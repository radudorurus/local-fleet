"""Config Flow and Options Flow for local_fleet."""
import os
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_VIN,
    CONF_PLATE,
    CONF_MODEL,
    CONF_FILE_PATH,
    CONF_SHEET_NAME,
    CONF_MILEAGE_CELL,
    CONF_SUMMER_DOTS,
    CONF_WINTER_DOTS,
    CONF_ALL_SEASON_DOTS,
)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_VIN): str,
    vol.Required(CONF_PLATE): str,
    vol.Required(CONF_MODEL): str,
    vol.Required(CONF_FILE_PATH, default="/config/downloads/jurnal_auto.xlsx"): str,
    vol.Required(CONF_SHEET_NAME, default="vehicle001"): str,
    vol.Required(CONF_MILEAGE_CELL, default="E2"): str,
})

def validate_dot_string(value: str) -> bool:
    """Validează formatul a 4 grupuri de câte 4 cifre separate prin virgulă."""
    if not value or not str(value).strip():
        return True
    pattern = r"^\s*\d{4}\s*,\s*\d{4}\s*,\s*\d{4}\s*,\s*\d{4}\s*$"
    return bool(re.match(pattern, value))


class LocalFleetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestionează fluxul de configurare inițială pentru Local Fleet."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Atașează fluxul de opțiuni la intrarea de configurare."""
        return LocalFleetOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Pasul de preluare a datelor de la utilizator la prima instalare."""
        errors = {}
        if user_input is not None:
            if not await self.hass.async_add_executor_job(
                os.path.exists, user_input[CONF_FILE_PATH]
            ):
                errors["base"] = "file_not_found"
            else:
                await self.async_set_unique_id(user_input[CONF_VIN])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_PLATE], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class LocalFleetOptionsFlowHandler(config_entries.OptionsFlow):
    """Gestionează modificarea parametrilor după configurarea inițială."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Afișează formularul de opțiuni și salvează modificările."""
        errors = {}
        if user_input is not None:
            for field in [CONF_SUMMER_DOTS, CONF_WINTER_DOTS, CONF_ALL_SEASON_DOTS]:
                val = user_input.get(field, "")
                if not validate_dot_string(val):
                    errors[field] = "invalid_dot_format"

            if not await self.hass.async_add_executor_job(
                os.path.exists, user_input[CONF_FILE_PATH]
            ):
                errors["base"] = "file_not_found"
            elif not errors:
                return self.async_create_entry(title="", data=user_input)

        current_file_path = self._config_entry.options.get(
            CONF_FILE_PATH, self._config_entry.data.get(CONF_FILE_PATH)
        )
        current_sheet_name = self._config_entry.options.get(
            CONF_SHEET_NAME, self._config_entry.data.get(CONF_SHEET_NAME)
        )
        current_mileage_cell = self._config_entry.options.get(
            CONF_MILEAGE_CELL, self._config_entry.data.get(CONF_MILEAGE_CELL)
        )
        current_summer_dots = self._config_entry.options.get(CONF_SUMMER_DOTS, "")
        current_winter_dots = self._config_entry.options.get(CONF_WINTER_DOTS, "")
        current_all_season_dots = self._config_entry.options.get(CONF_ALL_SEASON_DOTS, "")

        options_schema = vol.Schema({
            vol.Required(CONF_FILE_PATH, default=current_file_path): str,
            vol.Required(CONF_SHEET_NAME, default=current_sheet_name): str,
            vol.Required(CONF_MILEAGE_CELL, default=current_mileage_cell): str,
            vol.Optional(CONF_SUMMER_DOTS, default=current_summer_dots): str,
            vol.Optional(CONF_WINTER_DOTS, default=current_winter_dots): str,
            vol.Optional(CONF_ALL_SEASON_DOTS, default=current_all_season_dots): str,
        })

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )