"""Support for setting the Transmission BitTorrent client Turtle Mode."""
import logging
from typing import Any

from portainer.docker_container import PortainerDockerContainer
from portainer.endpoint import PortainerEndpoint

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_INSTANCE_ID,
    DISPATCHERS,
    DOMAIN,
    PORTAINER_NEW_CONTAINER_SIGNAL,
    PORTAINER_NEW_ENDPOINT_SIGNAL,
)
from .helpers import get_portainer_data

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Transmission switch."""
    instance_id = config_entry.data[CONF_INSTANCE_ID]

    @callback
    def async_new_container(
        endpoint_id, containers: dict[str, PortainerDockerContainer]
    ):
        switches: list[SwitchEntity] = []
        for container in containers.values():
            switches.append(
                PortainerContainerStateSwitch(instance_id, endpoint_id, container)
            )
        async_add_entities(switches, True)

    @callback
    def async_new_endpoint(new_endpoints: dict[str, PortainerEndpoint]):
        for endpoint in new_endpoints.values():
            unsub = async_dispatcher_connect(
                hass,
                PORTAINER_NEW_CONTAINER_SIGNAL.format(
                    instance_id=instance_id, endpoint_id=endpoint.endpoint_id
                ),
                async_new_container,
            )
            get_portainer_data(hass)[DISPATCHERS][instance_id].append(unsub)

    unsub = async_dispatcher_connect(
        hass,
        PORTAINER_NEW_ENDPOINT_SIGNAL.format(instance_id=instance_id),
        async_new_endpoint,
    )
    get_portainer_data(hass)[DISPATCHERS][instance_id].append(unsub)


class PortainerContainerStateSwitch(SwitchEntity):
    """Representation of container status switch."""

    def __init__(
        self,
        portainer_instance_id: str,
        endpoint_id: str,
        container: PortainerDockerContainer,
    ) -> None:
        """Initialize the switch class."""
        self._portainer_instance_id = portainer_instance_id
        self._endpoint_id = endpoint_id
        self._container = container
        self._attr_name = "Running"
        self._attr_unique_id = f"{self._portainer_instance_id}_{self._endpoint_id}_{self._container.name}_switch_running"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the service."""
        await self._container.start()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the service."""
        await self._container.stop()

    @property
    def is_on(self) -> bool:
        """Return if the service is on."""
        return self._container.state == "running"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self._portainer_instance_id}_{self._endpoint_id}_{self._container.name}",
                )
            },
            name=self._container.name,
            manufacturer=self._container.image,
            via_device=(
                DOMAIN,
                f"{self._portainer_instance_id}_{self._endpoint_id}",
            ),
        )
