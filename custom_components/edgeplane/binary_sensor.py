"""Binary sensor: EdgePlane agent online/offline."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_AGENT_ONLINE
from .coordinator import EPCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: EPCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EPAgentOnlineSensor(coordinator)])


class EPAgentOnlineSensor(CoordinatorEntity[EPCoordinator], BinarySensorEntity):
    """True when the WS connection to EdgePlane is active."""

    _attr_name = "EdgePlane Agent Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: EPCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{ENTITY_AGENT_ONLINE}"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.ws_connected
