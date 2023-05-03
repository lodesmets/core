"""Sensor platform for integration_blueprint."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from portainer.docker_container import PortainerDockerContainer
from portainer.endpoint import PortainerEndpoint

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PortainerApi
from .const import (
    CONF_INSTANCE_ID,
    CONF_SERVER,
    DISPATCHERS,
    DOMAIN,
    PORTAINER_NEW_CONTAINER_SIGNAL,
    PORTAINER_NEW_ENDPOINT_SIGNAL,
)
from .helpers import get_portainer_data, get_portainer_server
from .coordinator import PortainerCoordinator


@dataclass
class PortainerEntityDescription:
    """Describes Endpoint sensor entity."""

    icon: str
    name: str
    key: str
    value_fn: Callable[[PortainerEndpoint], StateType]
    exists_fn: Callable[[PortainerEndpoint], bool] = lambda _: True


PORTAINER_SENSORS: tuple[PortainerEntityDescription, ...] = (
    PortainerEntityDescription(
        icon="mdi:state-machine",
        name="Status",
        key="status",
        value_fn=lambda endpoint: endpoint.status,
        exists_fn=lambda endpoint: bool(endpoint.status),
    ),
)

ENDPOINT_SENSORS: tuple[PortainerEntityDescription, ...] = (
    PortainerEntityDescription(
        icon="mdi:state-machine",
        name="Status",
        key="status",
        value_fn=lambda endpoint: endpoint.status,
        exists_fn=lambda endpoint: bool(endpoint.status),
    ),
)

CONTAINER_SENSORS: tuple[PortainerEntityDescription, ...] = (
    PortainerEntityDescription(
        icon="mdi:state-machine",
        name="State",
        key="state",
        value_fn=lambda endpoint: endpoint.state,
        exists_fn=lambda endpoint: bool(endpoint.state),
    ),
    PortainerEntityDescription(
        icon="mdi:clock-outline",
        name="Status",
        key="status",
        value_fn=lambda endpoint: endpoint.status,
        exists_fn=lambda endpoint: bool(endpoint.status),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    instance_id = config_entry.data[CONF_INSTANCE_ID]
    friendly_name = config_entry.data[CONF_SERVER]
    portainer_server = get_portainer_server(hass, instance_id)
    sensors: list[SensorEntity] = [PortainerSensor(portainer_server, friendly_name)]
    async_add_entities(sensors)

    @callback
    def async_new_container(
        endpoint_id, containers: dict[str, PortainerDockerContainer]
    ):
        sensors: list[SensorEntity] = []
        for container in containers.values():
            for sensor in CONTAINER_SENSORS:
                sensors.append(
                    PortainerContainerSensor(
                        sensor, instance_id, endpoint_id, container
                    )
                )
        async_add_entities(sensors, True)

    @callback
    def async_new_endpoint(new_endpoints: dict[str, PortainerEndpoint]):
        sensors: list[SensorEntity] = []
        for endpoint in new_endpoints.values():
            for sensor in ENDPOINT_SENSORS:
                sensors.append(PortainerEndpointSensor(sensor, instance_id, endpoint))
            unsub = async_dispatcher_connect(
                hass,
                PORTAINER_NEW_CONTAINER_SIGNAL.format(
                    instance_id=instance_id, endpoint_id=endpoint.endpoint_id
                ),
                async_new_container,
            )
            get_portainer_data(hass)[DISPATCHERS][instance_id].append(unsub)
        async_add_entities(sensors, True)

    unsub = async_dispatcher_connect(
        hass,
        PORTAINER_NEW_ENDPOINT_SIGNAL.format(instance_id=instance_id),
        async_new_endpoint,
    )
    get_portainer_data(hass)[DISPATCHERS][instance_id].append(unsub)


class PortainerSensor(SensorEntity):
    """integration_blueprint Sensor class."""

    def __init__(
        self,
        portainer_server: PortainerApi,
        friendly_name: str,
    ) -> None:
        """Initialize the sensor class."""
        self._server = portainer_server
        self._friendly_name = friendly_name

        self._attr_available = True
        self._attr_entity_registry_enabled_default = True
        self._attr_extra_state_attributes = {}
        self._attr_icon = "mdi:update"
        self._attr_name = "Latest version"
        self._attr_should_poll = False
        self._attr_unique_id = (
            f"{portainer_server.portainer.instance_id}_sensor_latest_version"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._server.portainer.instance_id)},
            name=self._friendly_name,
            manufacturer="Portainer",
            sw_version=self._server.portainer.version,
        )

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._server.portainer.latest_version


class PortainerEndpointSensor(SensorEntity):
    """integration_blueprint Sensor class."""

    def __init__(
        self,
        sensor: PortainerEntityDescription,
        portainer_instance_id: str,
        endpoint: PortainerEndpoint,
    ) -> None:
        """Initialize the sensor class."""
        self._sensor = sensor
        self._portainer_instance_id = portainer_instance_id
        self._endpoint = endpoint

        self._attr_available = True
        self._attr_entity_registry_enabled_default = True
        self._attr_extra_state_attributes = {}
        self._attr_icon = self._sensor.icon
        self._attr_name = self._sensor.name
        self._attr_should_poll = False
        self._attr_unique_id = f"{self._portainer_instance_id}_{self._endpoint.endpoint_id}_sensor_{self._sensor.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self._portainer_instance_id}_{self._endpoint.endpoint_id}",
                )
            },
            name=self._endpoint.name,
            via_device=(DOMAIN, self._portainer_instance_id),
        )

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._sensor.value_fn(self._endpoint)


class PortainerContainerSensor(CoordinatorEntity, SensorEntity):
    """integration_blueprint Sensor class."""

    def __init__(
        self,
        sensor: PortainerEntityDescription,
        portainer_instance_id: str,
        endpoint_id: str,
        container: PortainerDockerContainer,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, context=idx)
        self._sensor = sensor
        self._portainer_instance_id = portainer_instance_id
        self._endpoint_id = endpoint_id
        self._container = container

        self._attr_available = True
        self._attr_entity_registry_enabled_default = True
        self._attr_extra_state_attributes = {}
        self._attr_icon = self._sensor.icon
        self._attr_name = self._sensor.name
        self._attr_should_poll = False
        self._attr_unique_id = f"{self._portainer_instance_id}_{self._endpoint_id}_{self._container.name}_sensor_{self._sensor.key}"

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

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._sensor.value_fn(self._container)
