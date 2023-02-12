"""Tests for Synology DSM Media Source."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from synology_dsm.api.photos import SynoPhotosAlbum, SynoPhotosItem

from homeassistant.components.media_source.error import Unresolvable
from homeassistant.components.media_source.models import MediaSourceItem
from homeassistant.components.synology_dsm.const import DOMAIN
from homeassistant.components.synology_dsm.media_source import (
    SynologyPhotosMediaSource,
    async_get_media_source,
)
from homeassistant.components.synology_dsm.models import SynologyDSMData
from homeassistant.core import HomeAssistant


@pytest.fixture
def dsm_with_photos():
    """Set up SynologyDSM API fixture."""
    with patch("homeassistant.components.synology_dsm.common.SynologyDSM") as dsm:
        dsm.login = AsyncMock(return_value=True)
        dsm.update = AsyncMock(return_value=True)
        dsm.photos = Mock(
            get_albums=AsyncMock(return_value=[SynoPhotosAlbum(1, "Album 1", 10)]),
            get_items_from_album=AsyncMock(
                return_value=[
                    SynoPhotosItem(10, "", "filename.jpg", 12345, "10_1298753", "sm")
                ]
            ),
            get_item_thumbnail_url=AsyncMock(),
        )

    return dsm


@pytest.mark.usefixtures("setup_media_source")
async def test_get_media_source(hass: HomeAssistant) -> None:
    """Test the async_get_media_source function and SynologyPhotosMediaSource constructor."""

    source = await async_get_media_source(hass)
    assert isinstance(source, SynologyPhotosMediaSource)
    assert source.domain == DOMAIN


@pytest.mark.usefixtures("setup_media_source")
@pytest.mark.parametrize(
    "identifier,exception_msg",
    [
        ("unique_id", "No album id"),
        ("unique_id/1", "No file name"),
        ("unique_id/1/cache_key", "No file name"),
        ("unique_id/1/cache_key/filename", "No file extension"),
    ],
)
async def test_resolve_media_bad_identifier(
    hass: HomeAssistant, identifier: str, exception_msg: str
) -> None:
    """Test resolve_media with bad identifiers."""
    source = await async_get_media_source(hass)
    item = MediaSourceItem(hass, DOMAIN, identifier, None)
    with pytest.raises(Unresolvable, match=exception_msg):
        await source.async_resolve_media(item)


@pytest.mark.usefixtures("setup_media_source")
@pytest.mark.parametrize(
    "identifier,url,mime_type",
    [
        (
            "ABC012345/10/27643_876876/filename.jpg",
            "/synology_dsm/ABC012345/27643_876876/filename.jpg",
            "image/jpeg",
        ),
        (
            "ABC012345/12/12631_47189/filename.png",
            "/synology_dsm/ABC012345/12631_47189/filename.png",
            "image/png",
        ),
    ],
)
async def test_resolve_media_success(
    hass: HomeAssistant, identifier: str, url: str, mime_type: str
) -> None:
    """Test successful resolving an item."""
    source = await async_get_media_source(hass)
    item = MediaSourceItem(hass, DOMAIN, identifier, None)
    result = await source.async_resolve_media(item)

    assert result.url == url
    assert result.mime_type == mime_type


@pytest.mark.usefixtures("setup_media_source")
async def test_browse_media_unconfigured(hass: HomeAssistant) -> None:
    """Test browse_media without any devices being configured."""
    source = await async_get_media_source(hass)
    item = MediaSourceItem(
        hass, DOMAIN, "unique_id/album_id/cache_key/filename.jpg", None
    )
    with pytest.raises(Unresolvable, match="Diskstation not initialized"):
        await source.async_browse_media(item)


@pytest.mark.usefixtures("mock_setup_entry")
@pytest.mark.usefixtures("setup_media_source")
async def test_browse_media_unknown_album(hass: HomeAssistant, dsm_with_photos) -> None:
    """Test browse_media with unknown album."""

    dsm = SynologyDSMData
    dsm.api = dsm_with_photos
    dsm.api.photos.get_items_from_album = AsyncMock(return_value=[])
    hass.data[DOMAIN] = {"unique_id": dsm}

    source = await async_get_media_source(hass)
    item = MediaSourceItem(hass, DOMAIN, "unique_id/1", None)
    result = await source.async_browse_media(item)

    assert result
    assert result.identifier is None
    assert len(result.children) == 0
