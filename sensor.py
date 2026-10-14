"""Sensor entity for local_fleet with direct entity mapping and dynamic state tracking."""
import logging
import os
import re
from datetime import date, timedelta

import openpyxl

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    CONF_FILE_PATH,
    CONF_MILEAGE_CELL,
    CONF_MODEL,
    CONF_PLATE,
    CONF_SHEET_NAME,
    CONF_VIN,
    DOMAIN,
    CONF_SUMMER_DOTS,
    CONF_WINTER_DOTS,
    CONF_ALL_SEASON_DOTS,
)

SCAN_INTERVAL = timedelta(minutes=5)
_LOGGER = logging.getLogger(__name__)


class ExcelReadError(Exception):
    """Excepție de bază pentru erori de citire Excel."""


class FileMissingError(ExcelReadError):
    """Lansată când fișierul nu există la calea specificată."""


class SheetNotFoundError(ExcelReadError):
    """Lansată când foaia de calcul specificată nu există în workbook."""


class CellEmptyError(ExcelReadError):
    """Lansată când celula nu conține nicio valoare (None)."""


def read_excel_cell(file_path: str, sheet_name: str, cell: str):
    """Citește valoarea dintr-o celulă Excel izolând fiecare tip de eroare."""
    if not os.path.exists(file_path):
        raise FileMissingError(f"Fișierul nu există la calea: {file_path}")

    try:
        workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    except Exception as err:
        raise ExcelReadError(f"Fișierul există dar nu a putut fi deschis: {err}")

    try:
        if sheet_name not in workbook.sheetnames:
            raise SheetNotFoundError(f"Foaia '{sheet_name}' nu există în fișier")

        val = workbook[sheet_name][cell].value
        if val is None:
            raise CellEmptyError(f"Celula {cell} din foaia '{sheet_name}' este goală")

        return val
    finally:
        workbook.close()


def calculate_max_tire_age(dots_string: str) -> float | None:
    """Calculează vechimea maximă (în ani) pentru un set de 4 coduri DOT."""
    if not dots_string or not str(dots_string).strip():
        return None

    parts = [p.strip() for p in str(dots_string).split(",")]
    if len(parts) != 4:
        return None

    oldest_date = None
    today = date.today()

    for dot in parts:
        if not re.match(r"^\d{4}$", dot):
            continue
        try:
            week = int(dot[0:2])
            year = 2000 + int(dot[2:4])

            if not (1 <= week <= 53):
                continue
            if year > today.year + 1 or year < 1990:
                continue

            tire_date = date.fromisocalendar(year, week, 1)

            if oldest_date is None or tire_date < oldest_date:
                oldest_date = tire_date
        except (ValueError, OverflowError):
            continue

    if oldest_date is None:
        return None

    days_diff = (today - oldest_date).days
    if days_diff < 0:
        return 0.0

    return round(days_diff / 365.25, 1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setarea senzorilor din Config Entry sau Options."""
    data = entry.data
    options = entry.options

    file_path = options.get(CONF_FILE_PATH, data.get(CONF_FILE_PATH))
    sheet_name = options.get(CONF_SHEET_NAME, data.get(CONF_SHEET_NAME))
    mileage_cell = options.get(CONF_MILEAGE_CELL, data.get(CONF_MILEAGE_CELL))

    vin = data[CONF_VIN]
    plate = data[CONF_PLATE]
    model = data[CONF_MODEL]

    slug_plate = slugify(plate)

    async_add_entities(
        [
            FleetMileageSensor(
                hass, vin, plate, model, file_path, sheet_name, mileage_cell
            ),
            FleetVinSensor(vin, plate, model),
            FleetRemainingDaysSensor(
                vin=vin,
                plate=plate,
                model=model,
                name_suffix="ITP Remaining Days",
                unique_key="itp_remaining_days",
                source_entity_id=f"date.{slug_plate}_itp_valid_until",
            ),
            FleetRemainingDaysSensor(
                vin=vin,
                plate=plate,
                model=model,
                name_suffix="RCA Remaining Days",
                unique_key="rca_remaining_days",
                source_entity_id=f"date.{slug_plate}_rca_valid_until",
            ),
            FleetRemainingDaysSensor(
                vin=vin,
                plate=plate,
                model=model,
                name_suffix="Vignette Remaining Days",
                unique_key="vignette_remaining_days",
                source_entity_id=f"date.{slug_plate}_vignette_valid_until",
            ),
            FleetRemainingDaysSensor(
                vin=vin,
                plate=plate,
                model=model,
                name_suffix="Service Remaining Days",
                unique_key="service_remaining_days",
                source_entity_id=f"date.{slug_plate}_next_service",
            ),
            FleetRemainingKmSensor(
                vin=vin,
                plate=plate,
                model=model,
                name_suffix="Km Until Next Service",
                unique_key="km_until_next_service",
                current_km_entity_id=f"sensor.{slug_plate}_mileage",
                target_km_entity_id=f"number.{slug_plate}_km_next_service",
            ),
            FleetTireAgeSensor(vin, plate, model, CONF_SUMMER_DOTS, "Summer Tire Age", "summer_tire_age"),
            FleetTireAgeSensor(vin, plate, model, CONF_WINTER_DOTS, "Winter Tire Age", "winter_tire_age"),
            FleetTireAgeSensor(vin, plate, model, CONF_ALL_SEASON_DOTS, "All-Season Tire Age", "all_season_tire_age"),
        ],
        True,
    )


class FleetMileageSensor(RestoreEntity, SensorEntity):
    """Senzor pentru citirea și stocarea kilometrajului."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        vin: str,
        plate: str,
        model: str,
        file_path: str,
        sheet_name: str,
        cell: str,
    ) -> None:
        self.hass = hass
        self._vin = vin
        self._plate = plate
        self._model = model
        self._file_path = file_path
        self._sheet_name = sheet_name
        self._cell = cell

        self._attr_name = "Mileage"
        self._attr_unique_id = f"{vin}_mileage"
        self._attr_native_unit_of_measurement = "km"
        self._attr_icon = "mdi:speedometer"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_suggested_display_precision = 0
        self._state: int | None = None
        self._last_mtime: float = 0.0

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model,
        )

    @property
    def native_value(self) -> int | None:
        return self._state

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = int(float(last_state.state))
            except ValueError:
                self._state = None

    async def async_update(self) -> None:
        try:
            current_mtime = await self.hass.async_add_executor_job(
                os.path.getmtime, self._file_path
            )
        except OSError as err:
            _LOGGER.error("Vehicle %s - Metadata access error: %s", self._plate, err)
            return

        if current_mtime <= self._last_mtime:
            return

        try:
            new_val = await self.hass.async_add_executor_job(
                read_excel_cell, self._file_path, self._sheet_name, self._cell
            )

            val_float = float(new_val)

            if not val_float.is_integer():
                _LOGGER.error(
                    "Vehicle %s: Cell %s contains a decimal value (%s). An integer is required for the mileage.",
                    self._plate,
                    self._cell,
                    new_val,
                )
                return

            self._state = int(val_float)
            self._last_mtime = current_mtime

        except FileMissingError as err:
            _LOGGER.error("Vehicle %s - I/O Error: %s", self._plate, err)
        except SheetNotFoundError as err:
            _LOGGER.error("Vehicle %s - Sheet Configuration Error: %s", self._plate, err)
        except CellEmptyError as err:
            _LOGGER.error("Vehicle %s - Data Empty Error: %s", self._plate, err)
        except (ValueError, TypeError):
            _LOGGER.error(
                "Vehicle %s - Data type Error: Cell contents %s is not a valid number",
                self._plate,
                self._cell,
            )
        except ExcelReadError as err:
            _LOGGER.error("Vehicle %s - Excel Generic Error: %s", self._plate, err)


class FleetVinSensor(SensorEntity):
    """Senzor de tip text pentru afișarea numărului de identificare (VIN)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:barcode"

    def __init__(self, vin: str, plate: str, model: str) -> None:
        self._vin = vin
        self._plate = plate
        self._model = model

        self._attr_name = "VIN"
        self._attr_unique_id = f"{vin}_vin"
        self._attr_native_value = vin

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model,
        )


class FleetRemainingDaysSensor(SensorEntity):
    """Senzor care calculează zilele rămase până la o dată de expirare."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vin: str,
        plate: str,
        model: str,
        name_suffix: str,
        unique_key: str,
        source_entity_id: str,
    ) -> None:
        self._vin = vin
        self._plate = plate
        self._model = model
        self._source_entity_id = source_entity_id

        self._attr_name = name_suffix
        self._attr_unique_id = f"{vin}_{unique_key}"
        self._attr_native_unit_of_measurement = "d"
        self._attr_icon = "mdi:calendar-alert"
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _update_state(*_) -> None:
            state = self.hass.states.get(self._source_entity_id)

            if state and state.state not in (None, "unknown", "unavailable", ""):
                try:
                    target_date = date.fromisoformat(state.state)
                    self._attr_native_value = (target_date - date.today()).days
                except ValueError:
                    self._attr_native_value = None
            else:
                self._attr_native_value = None

            self.async_write_ha_state()

        _update_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity_id], _update_state
            )
        )

        self.async_on_remove(
            async_track_time_change(
                self.hass, _update_state, hour=0, minute=0, second=1
            )
        )


class FleetRemainingKmSensor(SensorEntity):
    """Senzor care calculează diferența dintre pragul setat și odometrul curent."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vin: str,
        plate: str,
        model: str,
        name_suffix: str,
        unique_key: str,
        current_km_entity_id: str,
        target_km_entity_id: str,
    ) -> None:
        self._vin = vin
        self._plate = plate
        self._model = model
        self._current_km_entity_id = current_km_entity_id
        self._target_km_entity_id = target_km_entity_id

        self._attr_name = name_suffix
        self._attr_unique_id = f"{vin}_{unique_key}"
        self._attr_native_unit_of_measurement = "km"
        self._attr_icon = "mdi:map-marker-distance"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_suggested_display_precision = 0
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _update_state(event=None) -> None:
            mileage_state = self.hass.states.get(self._current_km_entity_id)
            target_state = self.hass.states.get(self._target_km_entity_id)

            if (
                mileage_state
                and mileage_state.state not in (None, "unknown", "unavailable", "")
                and target_state
                and target_state.state not in (None, "unknown", "unavailable", "")
            ):
                try:
                    current_km = float(mileage_state.state)
                    target_km = float(target_state.state)
                    self._attr_native_value = int(target_km - current_km)
                except ValueError:
                    self._attr_native_value = None
            else:
                self._attr_native_value = None

            self.async_write_ha_state()

        _update_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._current_km_entity_id, self._target_km_entity_id],
                _update_state,
            )
        )


class FleetTireAgeSensor(RestoreEntity, SensorEntity):
    """Senzor pentru calculul vechimii maxime a setului de anvelope."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vin: str,
        plate: str,
        model: str,
        dot_conf_key: str,
        name_suffix: str,
        unique_key: str,
    ) -> None:
        self._vin = vin
        self._plate = plate
        self._model = model
        self._dot_conf_key = dot_conf_key

        self._attr_name = name_suffix
        self._attr_unique_id = f"{vin}_{unique_key}"
        self._attr_native_unit_of_measurement = "years"
        self._attr_icon = "mdi:tire"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._state: float | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model,
        )

    @property
    def native_value(self) -> float | None:
        return self._state

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = float(last_state.state)
            except ValueError:
                self._state = None
        self._update_age()

    async def async_update(self) -> None:
        self._update_age()

    @callback
    def _update_age(self) -> None:
        entry = self.hass.config_entries.async_get_entry(
            self.platform.config_entry.entry_id
        )
        if not entry:
            self._state = None
            return

        options = entry.options
        data = entry.data

        dots_string = options.get(
            self._dot_conf_key, data.get(self._dot_conf_key, "")
        )
        self._state = calculate_max_tire_age(dots_string)