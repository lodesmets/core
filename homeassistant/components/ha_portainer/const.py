"""Constants for Portainer."""
from datetime import timedelta
from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

NAME = "Portainer"
DOMAIN = "ha_portainer"
VERSION = "0.0.1"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

DEFAULT_USE_SSL = False
DEFAULT_PORT = 9000

EXCEPTION_MESSAGE = "message"
EXCEPTION_DETAILS = "details"
EXCEPTION_UNKNOWN = "unknown"

SERVERS: Final = "servers"
DISPATCHERS: Final = "dispatchers"


UPDATE_PORTAINER_INTERVAL = timedelta(minutes=5)
UPDATE_STATS_INTERVAL = timedelta(seconds=10)
UPDATE_SENSOR_INTERVAL = timedelta(seconds=10)

CONF_SERVER = "server"
CONF_INSTANCE_ID = "instance_id"

SERVER_CONFIG = "server_config"

PORTAINER_NEW_ENDPOINT_SIGNAL = "portainer_new_endpoint_signal_{instance_id}"
PORTAINER_NEW_CONTAINER_SIGNAL = (
    "portainer_new_container_signal_{instance_id}_{endpoint_id}"
)
PORTAINER_UPDATE_PORTAINER_SIGNAL = "portainer_update_portainer_signal_{instance_id}"
PORTAINER_UPDATE_ENDPOINT_SIGNAL = (
    "portainer_update_endpoint_signal_{instance_id}_{endpoint_id}"
)
PORTAINER_UPDATE_CONTAINER_SIGNAL = (
    "portainer_update_endpoint_signal_{instance_id}_{endpoint_id}"
)
PORTAINER_UPDATE_CONTAINER_STATS_SIGNAL = (
    "portainer_update_endpoint_signal_{instance_id}_{endpoint_id}_{container_id}"
)
