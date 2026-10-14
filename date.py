"""Date/time entities editable from GUI."""
from datetime import date
from homeassistant.components.date import DateEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_VIN, CONF_PLATE, CONF_MODEL

async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.data
    vin = data[CONF_VIN]
    plate = data[CONF_PLATE]
    model = data[CONF_MODEL]

    async_add_entities([
        FleetEditableDate(vin, plate, model, "ITP valid until", "itp_date"),
        FleetEditableDate(vin, plate, model, "RCA valid until", "rca_date"),
        FleetEditableDate(vin, plate, model, "Vignette valid until", "vignette_date"),
        FleetEditableDate(vin, plate, model, "Next Service", "next_service"),
    ])

class FleetEditableDate(RestoreEntity, DateEntity):
    _attr_has_entity_name = True 

    def __init__(self, vin, plate, model, name_suffix, key):
        self._vin = vin
        self._plate = plate
        self._model = model
        
        self._attr_name = name_suffix 
        self._attr_unique_id = f"{vin}_{key}"
        self._attr_native_value = None
        if key == "itp_date":
            self._attr_icon = "mdi:car-cog"
        elif key == "rca_date":
            self._attr_icon = "mdi:shield-car"
        elif key == "vignette_date":
            self._attr_icon = "mdi:card-account-details-outline"
        elif key == "service_date":
            self._attr_icon = "mdi:calendar-clock"
        else:
            self._attr_icon = "mdi:calendar"
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
                self._attr_native_value = date.fromisoformat(last_state.state)
            except ValueError:
                self._attr_native_value = None

    async def async_set_value(self, value: date) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()