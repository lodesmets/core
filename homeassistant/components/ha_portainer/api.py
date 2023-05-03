"""Sample API Client."""
from __future__ import annotations

import logging

from portainer import Portainer
from portainer.endpoint import PortainerEndpoint
from portainer.docker_container import PortainerDockerContainer

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    PORTAINER_NEW_CONTAINER_SIGNAL,
    PORTAINER_NEW_ENDPOINT_SIGNAL,
    PORTAINER_UPDATE_ENDPOINT_SIGNAL,
    SERVER_CONFIG,
)

LOGGER = logging.getLogger(__name__)


class PortainerApi:
    """Sample API Client."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Sample API Client."""
        self._hass = hass
        self._entry = entry

        self._known_endpoints: dict[str, PortainerEndpoint] = {}
        self._known_docker_containers: dict[
            str, dict[str, PortainerDockerContainer]
        ] = {}

        self._portainer: Portainer = None
        self.async_update_platforms = Debouncer(
            hass,
            LOGGER,
            cooldown=10,
            immediate=True,
            function=self._async_update_platforms,
        ).async_call

    async def async_setup(self) -> None:
        """Start interacting with the NAS."""
        session = async_get_clientsession(
            self._hass, False
        )  # self._entry.data[CONF_VERIFY_SSL])
        self._portainer = Portainer(
            session,
            self._entry.data[SERVER_CONFIG][CONF_URL],
            self._entry.data[SERVER_CONFIG][CONF_PORT],
            self._entry.data[SERVER_CONFIG][CONF_USERNAME],
            self._entry.data[SERVER_CONFIG][CONF_PASSWORD],
            60,  # self._entry.options.get(CONF_TIMEOUT),
            self._entry.data[SERVER_CONFIG][CONF_SSL],
        )
        await self._portainer.login()
        await self._portainer.request_version()

    @callback
    def async_refresh_endpoint(self, endpoint: PortainerEndpoint):
        """Forward refresh dispatch to media_player."""
        unique_id = f"{self._portainer.instance_id}_{endpoint.endpoint_id}"
        LOGGER.debug("Refreshing %s", unique_id)
        async_dispatcher_send(
            self._hass,
            PORTAINER_UPDATE_ENDPOINT_SIGNAL.format(
                instance_id=self._portainer.instance_id,
                endpoint_id=endpoint.endpoint_id,
            ),
            endpoint,
        )

    async def _async_update_platforms(self):  # noqa: C901
        """Update the platform entities."""
        LOGGER.debug("Updating devices")
        all_endpoints = await self._portainer.get_endpoints()
        available_endpoints: dict[str, PortainerEndpoint] = {}

        new_endpoints: dict[str, PortainerEndpoint] = {}

        def process_containers(
            endpoint_id: str,
            containers: dict[str, PortainerDockerContainer],
            send_new_container_signal: bool,
        ):
            new_containers: dict[str, PortainerDockerContainer] = {}
            for container_name, container in containers.items():
                if container_name not in self._known_docker_containers[endpoint_id]:
                    self._known_docker_containers[endpoint_id][
                        container_name
                    ] = container
                    new_containers[container_name] = container
            if new_containers and send_new_container_signal:
                async_dispatcher_send(
                    self._hass,
                    PORTAINER_NEW_CONTAINER_SIGNAL.format(
                        instance_id=self._portainer.instance_id,
                        endpoint_id=endpoint_id,
                    ),
                    endpoint_id,
                    new_containers,
                )

        for portainer_endpoint in all_endpoints:
            endpoint_id = portainer_endpoint.endpoint_id
            available_endpoints[endpoint_id] = portainer_endpoint
            containers = portainer_endpoint.docker_container
            if endpoint_id not in self._known_endpoints:
                # Endpoint does not exist
                new_endpoints[endpoint_id] = portainer_endpoint
                self._known_docker_containers[endpoint_id] = {}
                process_containers(endpoint_id, containers, False)
            else:
                process_containers(endpoint_id, containers, True)

        self._known_endpoints = available_endpoints

        if new_endpoints:
            async_dispatcher_send(
                self._hass,
                PORTAINER_NEW_ENDPOINT_SIGNAL.format(
                    instance_id=self._portainer.instance_id
                ),
                new_endpoints,
            )
            for endpoint_id in new_endpoints:
                containers = available_endpoints[endpoint_id].docker_container
                async_dispatcher_send(
                    self._hass,
                    PORTAINER_NEW_CONTAINER_SIGNAL.format(
                        instance_id=self._portainer.instance_id,
                        endpoint_id=endpoint_id,
                    ),
                    endpoint_id,
                    containers,
                )

    @property
    def endpoints(self):
        """Return endpoints."""
        return self._known_endpoints

    @property
    def portainer(self):
        """Return portainer server."""
        return self._portainer
