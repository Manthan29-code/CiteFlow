import pytest

from citegen.runner import process_single_title

pytestmark = [pytest.mark.part1, pytest.mark.live]


@pytest.mark.asyncio
async def test_live_lookup_kunz2014():
    """Live integration check with network access (skipped by default)."""
    title = "Firehose and mirror instabilities in a collisionless plasma"
    result = await process_single_title(title)

    assert result.get("status") == "accepted"
    meta = result.get("selected_metadata")
    assert meta is not None
    assert "Firehose" in meta.get("title", "")
    assert meta.get("year") == 2014
    assert meta.get("volume") == "112"
    assert "10.1103" in (meta.get("doi_url") or "")
