"""Entitate numerică editabilă din UI pentru prag revizie."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_VIN, CONF_PLATE, CONF_MODEL

async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.data
    async_add_entities([
        FleetEditableNumber(data[CONF_VIN], data[CONF_PLATE], data[CONF_MODEL], "Km Next Service", "service_km")
    ])

class FleetEditableNumber(RestoreEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_suggested_display_precision = 0 # Elimină zecimalele din UI
    _attr_native_step = 1.0 # Limitează setările manuale la pași întregi

    def __init__(self, vin, plate, model, name_suffix, key):
        self._vin = vin
        self._plate = plate
        self._model = model
        self._attr_name = name_suffix
        self._attr_unique_id = f"{vin}_{key}"
        self._attr_native_unit_of_measurement = "km"
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1000000
        self._attr_native_step = 1
        self._attr_native_value = None
        self._attr_icon = "mdi:wrench-clock"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                self._attr_native_value = None

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()