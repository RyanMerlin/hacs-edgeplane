from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.edgeplane.const import DOMAIN
from custom_components.edgeplane.coordinator import EPCoordinator
from custom_components.edgeplane.models import EPAgentState
from custom_components.edgeplane.binary_sensor import EPAgentOnlineSensor
from custom_components.edgeplane.sensor import (
    EPActiveTasksSensor, EPTasksCompletedSensor, EPLastTaskSensor,
)


@pytest.fixture
def mock_coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "ep_url": "http://edgeplane:8008", "sa_token": "t",
        "agent_name": "ha", "capabilities": [], "mission_id": "m", "agent_id": "a",
    })
    entry.add_to_hass(hass)
    coord = MagicMock(spec=EPCoordinator)
    coord.state = EPAgentState(online=True, ws_connected=True, active_tasks=2, tasks_completed=5, last_task="dim lights")
    coord.data = coord.state
    coord.entry = entry
    return coord


def test_online_sensor_is_on(mock_coordinator):
    sensor = EPAgentOnlineSensor(mock_coordinator)
    assert sensor.is_on is True


def test_online_sensor_is_off_when_not_connected(mock_coordinator):
    mock_coordinator.state.ws_connected = False
    sensor = EPAgentOnlineSensor(mock_coordinator)
    assert sensor.is_on is False


def test_active_tasks_sensor_value(mock_coordinator):
    sensor = EPActiveTasksSensor(mock_coordinator)
    assert sensor.native_value == 2


def test_tasks_completed_sensor_value(mock_coordinator):
    sensor = EPTasksCompletedSensor(mock_coordinator)
    assert sensor.native_value == 5


def test_last_task_sensor_value(mock_coordinator):
    sensor = EPLastTaskSensor(mock_coordinator)
    assert sensor.native_value == "dim lights"


def test_last_task_sensor_none_when_no_tasks(mock_coordinator):
    mock_coordinator.state.last_task = None
    sensor = EPLastTaskSensor(mock_coordinator)
    assert sensor.native_value is None
