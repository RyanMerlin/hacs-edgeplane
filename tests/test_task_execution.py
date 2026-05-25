import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.edgeplane.const import DOMAIN
from custom_components.edgeplane.coordinator import EPCoordinator


@pytest.fixture
def coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "ep_url": "http://edgeplane:8008",
        "sa_token": "ep_session_test",
        "agent_name": "home-assistant",
        "capabilities": ["home_control.light", "notify"],
        "mission_id": "mission-123",
        "agent_id": "agent-456",
    })
    entry.add_to_hass(hass)
    return EPCoordinator(hass, entry)


def _session_with_post(status=200, json_data=None):
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.raise_for_status = MagicMock()
    post_ctx = MagicMock()
    post_ctx.__aenter__ = AsyncMock(return_value=resp)
    post_ctx.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=post_ctx)
    return session


def _session_with_get(status=200, json_data=None):
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.raise_for_status = MagicMock()
    get_ctx = MagicMock()
    get_ctx.__aenter__ = AsyncMock(return_value=resp)
    get_ctx.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=get_ctx)
    return session


async def test_task_claim_returns_lease_id(hass, coordinator):
    session = _session_with_post(200, {"claim_lease_id": "lease-abc"})
    with patch("aiohttp.ClientSession", return_value=session):
        lease_id = await coordinator._claim_task("task-123")
    assert lease_id == "lease-abc"


async def test_task_claim_409_returns_none(hass, coordinator):
    session = _session_with_post(409)
    with patch("aiohttp.ClientSession", return_value=session):
        lease_id = await coordinator._claim_task("task-123")
    assert lease_id is None


async def test_task_claim_423_returns_none(hass, coordinator):
    session = _session_with_post(423)
    with patch("aiohttp.ClientSession", return_value=session):
        lease_id = await coordinator._claim_task("task-123")
    assert lease_id is None


async def test_handle_task_full_lifecycle(hass, coordinator):
    """Fetch → claim → HA service call → complete."""
    task_payload = json.dumps({
        "domain": "light", "service": "turn_on",
        "target": {"entity_id": "light.office"}, "data": {"brightness": 200}
    })
    task_data = {
        "id": "task-123", "title": "Test task",
        "description": task_payload,
        "required_capabilities": ["home_control.light"],
    }

    fetch_session = _session_with_get(200, task_data)
    claim_session = _session_with_post(200, {"claim_lease_id": "lease-xyz"})
    progress_session = _session_with_post(200)
    complete_session = _session_with_post(200)
    sessions = iter([fetch_session, claim_session, progress_session, complete_session])

    with patch("aiohttp.ClientSession", side_effect=sessions):
        with patch.object(coordinator, "_schedule_task_heartbeat", return_value=lambda: None):
            with patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as mock_svc:
                await coordinator._handle_task("task-123")

    mock_svc.assert_awaited_once()
    args = mock_svc.call_args[0]
    assert args[0] == "light"
    assert args[1] == "turn_on"


async def test_handle_task_skips_on_capability_mismatch(hass, coordinator):
    task_data = {
        "id": "task-999", "title": "K8s task",
        "description": "{}",
        "required_capabilities": ["kubectl"],
    }
    fetch_session = _session_with_get(200, task_data)

    with patch("aiohttp.ClientSession", side_effect=[fetch_session]):
        with patch.object(coordinator, "_claim_task", new_callable=AsyncMock) as mock_claim:
            await coordinator._handle_task("task-999")
            mock_claim.assert_not_awaited()


async def test_handle_task_fails_on_invalid_payload(hass, coordinator):
    task_data = {
        "id": "task-bad", "title": "Bad payload",
        "description": "not-json",
        "required_capabilities": [],
    }
    fetch_session = _session_with_get(200, task_data)
    claim_session = _session_with_post(200, {"claim_lease_id": "lease-1"})
    progress_session = _session_with_post(200)
    fail_session = _session_with_post(200)
    sessions = iter([fetch_session, claim_session, progress_session, fail_session])

    with patch("aiohttp.ClientSession", side_effect=sessions):
        with patch.object(coordinator, "_schedule_task_heartbeat", return_value=lambda: None):
            await coordinator._handle_task("task-bad")

    assert coordinator.state.tasks_completed == 1
