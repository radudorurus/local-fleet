"""Entitate de tip select pentru tipul anvelopelor vehiculului."""
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_VIN, CONF_PLATE, CONF_MODEL, CONF_TIRE_TYPE, TIRE_TYPES

async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.data
    async_add_entities([
        FleetTireSelect(
            data[CONF_VIN],
            data[CONF_PLATE],
            data[CONF_MODEL],
            "Tire Type",
            CONF_TIRE_TYPE
        )
    ])

class FleetTireSelect(RestoreEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:tire"

    def __init__(self, vin, plate, model, name_suffix, key):
        self._vin = vin
        self._plate = plate
        self._model = model
        self._attr_name = name_suffix
        self._attr_unique_id = f"{vin}_{key}"
        self._attr_options = TIRE_TYPES
        self._attr_current_option = "Summer"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
            manufacturer="Local Fleet",
            model=self._model
        )

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state in self._attr_options:
            self._attr_current_option = last_state.state

    async def async_select_option(self, option: str) -> None:
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()