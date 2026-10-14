from homeassistant.components.text import TextEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Ajustați importurile în funcție de structura fișierului const.py
from .const import DOMAIN, CONF_VIN, CONF_PLATE, CONF_MODEL

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Inițializarea platformei text."""
    data = entry.data
    
    async_add_entities(
        [
            FleetModelText(
                data[CONF_VIN],
                data[CONF_PLATE],
                data.get(CONF_MODEL, "Necunoscut"),
            )
        ],
        True,
    )

class FleetModelText(TextEntity, RestoreEntity):
    """Entitate editabilă pentru modelul vehiculului."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:car-info"

    def __init__(self, vin: str, plate: str, initial_model: str) -> None:
        """Inițializarea entității."""
        self._vin = vin
        self._plate = plate
        self._attr_name = "Model"
        self._attr_unique_id = f"{vin}_model_text"
        
        # Setează valoarea inițială doar dacă nu există o stare salvată anterior
        self._attr_native_value = initial_model

    @property
    def device_info(self) -> DeviceInfo:
        """Asocierea entității cu dispozitivul părinte."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=self._plate,
        )

    async def async_added_to_hass(self) -> None:
        """Metodă apelată la adăugarea entității. Restaurează starea anterioară."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        # Dacă există un istoric valid, suprascrie valoarea inițială
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state

    async def async_set_value(self, value: str) -> None:
        """Metodă apelată când utilizatorul introduce o valoare nouă în interfață."""
        # 1. Actualizează starea entității
        self._attr_native_value = value
        self.async_write_ha_state()

        # 2. Actualizează proprietatea "model" în Registrul Dispozitivelor (Device Registry)
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, self._vin)})
        
        if device:
            device_registry.async_update_device(
                device.id,
                model=value
            )