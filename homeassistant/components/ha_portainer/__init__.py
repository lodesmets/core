"""Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""
from __future__ import annotations

import logging

from portainer.exceptions import (
    PortainerException,
    PortainerInvalidCredentialsException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .api import PortainerApi
from .const import (
    CONF_INSTANCE_ID,
    CONF_SERVER,
    DISPATCHERS,
    DOMAIN,
    EXCEPTION_DETAILS,
    EXCEPTION_UNKNOWN,
    PORTAINER_UPDATE_PORTAINER_SIGNAL,
    SERVERS,
    UPDATE_PORTAINER_INTERVAL,
)
from .helpers import PortainerData, get_portainer_data

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]

LOGGER = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Portainer component."""
    hass_data = PortainerData(servers={}, dispatchers={})
    hass.data.setdefault(DOMAIN, hass_data)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=entry.data[CONF_INSTANCE_ID]
        )

    # Continue setup
    api = PortainerApi(hass, entry)
    try:
        await api.async_setup()
    except PortainerInvalidCredentialsException as err:
        raise ConfigEntryAuthFailed() from err
    except PortainerException as err:
        if err.args[0] and isinstance(err.args[0], dict):
            details = err.args[0].get(EXCEPTION_DETAILS, EXCEPTION_UNKNOWN)
        else:
            details = EXCEPTION_UNKNOWN
        raise ConfigEntryNotReady(details) from err

    instance_id = entry.data[CONF_INSTANCE_ID]
    friendly_name = entry.data[CONF_SERVER]
    hass_data = get_portainer_data(hass)
    hass_data[SERVERS][instance_id] = api

    unsub = async_dispatcher_connect(
        hass,
        PORTAINER_UPDATE_PORTAINER_SIGNAL.format(instance_id=instance_id),
        api.async_update_platforms,
    )

    hass_data[DISPATCHERS].setdefault(instance_id, [])
    hass_data[DISPATCHERS][instance_id].append(unsub)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await api.async_update_platforms()

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async_cleanup_portainer_devices(hass, entry)

    @callback
    def scheduled_endpoint_scan(_):
        LOGGER.debug("Scheduled scan for new endpoints on %s", friendly_name)
        async_dispatcher_send(
            hass, PORTAINER_UPDATE_PORTAINER_SIGNAL.format(instance_id=instance_id)
        )

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            scheduled_endpoint_scan,
            UPDATE_PORTAINER_INTERVAL,
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


@callback
def async_cleanup_portainer_devices(hass, entry):
    """Clean up old and invalid devices from the registry."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device_entries = dr.async_entries_for_config_entry(device_registry, entry.entry_id)

    for device_entry in device_entries:
        if (
            len(
                er.async_entries_for_device(
                    entity_registry, device_entry.id, include_disabled_entities=True
                )
            )
            == 0
        ):
            LOGGER.debug(
                "Removing orphaned device: %s / %s",
                device_entry.name,
                device_entry.identifiers,
            )
            device_registry.async_remove_device(device_entry.id)
