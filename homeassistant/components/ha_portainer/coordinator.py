"""DataUpdateCoordinator for updating the values for Portainer."""
import logging

import async_timeout
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .api import PortainerApi
from .const import DOMAIN, UPDATE_STATS_INTERVAL, UPDATE_SENSOR_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PortainerCoordinator(DataUpdateCoordinator):
    """Portainer coordinator."""

    def __init__(self, hass, portainer_api: PortainerApi):
        """Initialize portainer coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="My sensor",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=UPDATE_SENSOR_INTERVAL,
        )
        self.portainer_api = portainer_api

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with async_timeout.timeout(10):
            # Grab active context variables to limit data required to be fetched from API
            # Note: using context is not required if there is no need or ability to limit
            # data retrieved from API.
            listening_idx = set(self.async_contexts())
            return await self.portainer_api.portainer.fetch_data(listening_idx)
