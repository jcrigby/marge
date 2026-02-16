"""
CTS -- Counter Reset Service Test

Tests counter.reset to initial value.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_counter_reset_to_initial(rest):
    """counter reset returns to initial value attribute."""
    await rest.set_state("counter.depth_crst", "5", {"initial": 0})
    await rest.call_service("counter", "reset", {"entity_id": "counter.depth_crst"})
    state = await rest.get_state("counter.depth_crst")
    assert state["state"] == "0"
