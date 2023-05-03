"""Adds config flow for Portainer."""
from __future__ import annotations

from portainer import Portainer
from portainer.exceptions import (
    PortainerException,
    PortainerInvalidCredentialsException,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_INSTANCE_ID,
    CONF_SERVER,
    DEFAULT_PORT,
    DEFAULT_USE_SSL,
    DOMAIN,
    LOGGER,
    SERVER_CONFIG,
)


class PortainerFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Portainer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the synology_dsm config flow."""

    async def async_step_user(
        self, user_input: dict | None = None, errors: dict | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None and errors is None:
            return await self.async_step_verify_config(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL, default=(user_input or {}).get(CONF_URL)
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL),
                    ),
                    vol.Required(
                        CONF_PORT,
                        default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.NUMBER
                        ),
                    ),
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_PASSWORD,
                        default=(user_input or {}).get(CONF_PASSWORD),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                    vol.Optional(
                        CONF_SSL,
                        default=(user_input or {}).get(CONF_SSL, DEFAULT_USE_SSL),
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_verify_config(self, user_input: dict) -> FlowResult:
        """Validate config."""
        errors = {}
        url = user_input[CONF_URL]
        port = user_input.get(CONF_PORT)
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]
        use_ssl = user_input.get(CONF_SSL, DEFAULT_USE_SSL)
        session = async_get_clientsession(self.hass, use_ssl)
        portainer = Portainer(session, url, port, username, password, 30, use_ssl)
        try:
            await portainer.login()
            await portainer.request_version()
        except PortainerInvalidCredentialsException as exception:
            LOGGER.warning(exception)
            errors["base"] = "auth"
        except PortainerException as exception:
            LOGGER.exception(exception)
            errors["base"] = "unknown"

        if errors:
            return await self.async_step_user(user_input, errors=errors)

        friendly_name = f"{url}:{port}"
        data = {
            CONF_INSTANCE_ID: portainer.instance_id,
            CONF_SERVER: friendly_name,
            SERVER_CONFIG: user_input,
        }
        LOGGER.debug("Valid config created for %s", friendly_name)
        return self.async_create_entry(
            title=friendly_name,
            data=data,
        )
