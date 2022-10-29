"""Tests for iAqualink integration utility functions."""

from iaqualink.exception import AqualinkServiceException
import pytest

from homeassistant.components.iaqualink.utils import await_or_reraise
from homeassistant.exceptions import HomeAssistantError

from .conftest import async_raises, async_returns


async def test_await_or_reraise(hass):
    """Test await_or_reraise for all values of awaitable."""
    async_noop = async_returns(None)
    await await_or_reraise(async_noop())

    with pytest.raises(Exception):
        async_ex = async_raises(Exception)
        await await_or_reraise(async_ex())

    with pytest.raises(HomeAssistantError):
        async_ex = async_raises(AqualinkServiceException)
        await await_or_reraise(async_ex())
