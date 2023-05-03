"""Support for WLED button."""
from __future__ import annotations

from portainer.docker_container import PortainerDockerContainer
from portainer.endpoint import PortainerEndpoint

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
        buttons: list[ButtonEntity] = []
        for container in containers.values():
            buttons.append(
                PortainerContainerRestartButton(instance_id, endpoint_id, container)
            )
            buttons.append(
                PortainerContainerRecreateButton(instance_id, endpoint_id, container)
            )
        async_add_entities(buttons, True)

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


class PortainerContainerRestartButton(ButtonEntity):
    """Defines a Portainer docker container restart button."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Restart"

    def __init__(
        self,
        portainer_instance_id: str,
        endpoint_id: str,
        container: PortainerDockerContainer,
    ) -> None:
        """Initialize the button entity."""
        self._portainer_instance_id = portainer_instance_id
        self._endpoint_id = endpoint_id
        self._container = container
        self._attr_unique_id = f"{self._portainer_instance_id}_{self._endpoint_id}_{self._container.name}_button_restart"

    async def async_press(self) -> None:
        """Send out a restart command."""
        await self._container.restart()

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


class PortainerContainerRecreateButton(ButtonEntity):
    """Defines a Portainer docker container restart button."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Recreate"

    def __init__(
        self,
        portainer_instance_id: str,
        endpoint_id: str,
        container: PortainerDockerContainer,
    ) -> None:
        """Initialize the button entity."""
        self._portainer_instance_id = portainer_instance_id
        self._endpoint_id = endpoint_id
        self._container = container
        self._attr_unique_id = f"{self._portainer_instance_id}_{self._endpoint_id}_{self._container.name}_button_recreate"

    async def async_press(self) -> None:
        """Send out a recreate command."""
        await self._container.recreate()

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
