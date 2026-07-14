# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from aiohttp.test_utils import make_mocked_request
import pytest

from impress_remote_relay.relay import RelayState, health


@pytest.mark.asyncio
async def test_health_reports_empty_state() -> None:
    state = RelayState()
    request = make_mocked_request("GET", "/health", app={"relay_state": state})
    response = await health(request)
    assert response.status == 200
