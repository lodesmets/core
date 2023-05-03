"""Helper methods for common Portainer integration operations."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from .const import DOMAIN, SERVERS

if TYPE_CHECKING:
    from . import PortainerApi


class PortainerData(TypedDict):
    """Typed description of Portainer data stored in `hass.data`."""

    servers: dict[str, PortainerApi]
    dispatchers: dict[str, list[CALLBACK_TYPE]]


def get_portainer_data(hass: HomeAssistant) -> PortainerData:
    """Get typed data from hass.data."""
    return hass.data[DOMAIN]


def get_portainer_server(hass: HomeAssistant, instance_id: str) -> PortainerApi:
    """Get portainer server from hass.data."""
    return get_portainer_data(hass)[SERVERS][instance_id]
