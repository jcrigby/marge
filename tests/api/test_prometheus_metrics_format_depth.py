"""
CTS -- Prometheus Metrics Format Depth Tests

Tests the /metrics endpoint for proper Prometheus exposition format:
metric names, HELP/TYPE annotations, numeric values, and all expected
metric families.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _get_metrics(rest):
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    return resp.text


# ── Content Type ─────────────────────────────────────────

async def test_metrics_content_type(rest):
    """Metrics endpoint returns text/plain Prometheus content type."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct


# ── Required Metric Families ─────────────────────────────

async def test_metrics_has_uptime(rest):
    """Metrics include marge_uptime_seconds."""
    text = await _get_metrics(rest)
    assert "marge_uptime_seconds" in text


async def test_metrics_has_startup(rest):
    """Metrics include marge_startup_seconds."""
    text = await _get_metrics(rest)
    assert "marge_startup_seconds" in text


async def test_metrics_has_entity_count(rest):
    """Metrics include marge_entity_count."""
    text = await _get_metrics(rest)
    assert "marge_entity_count" in text


async def test_metrics_has_state_changes(rest):
    """Metrics include marge_state_changes_total."""
    text = await _get_metrics(rest)
    assert "marge_state_changes_total" in text


async def test_metrics_has_events_fired(rest):
    """Metrics include marge_events_fired_total."""
    text = await _get_metrics(rest)
    assert "marge_events_fired_total" in text


async def test_metrics_has_latency_avg(rest):
    """Metrics include marge_latency_avg_microseconds."""
    text = await _get_metrics(rest)
    assert "marge_latency_avg_microseconds" in text


async def test_metrics_has_latency_max(rest):
    """Metrics include marge_latency_max_microseconds."""
    text = await _get_metrics(rest)
    assert "marge_latency_max_microseconds" in text


async def test_metrics_has_memory_rss(rest):
    """Metrics include marge_memory_rss_bytes."""
    text = await _get_metrics(rest)
    assert "marge_memory_rss_bytes" in text


async def test_metrics_has_ws_connections(rest):
    """Metrics include marge_ws_connections."""
    text = await _get_metrics(rest)
    assert "marge_ws_connections" in text


async def test_metrics_has_info(rest):
    """Metrics include marge_info with version label."""
    text = await _get_metrics(rest)
    assert "marge_info" in text
    assert 'version="' in text


# ── HELP/TYPE Annotations ────────────────────────────────

async def test_metrics_has_help_lines(rest):
    """Metrics include # HELP annotations."""
    text = await _get_metrics(rest)
    help_lines = [l for l in text.splitlines() if l.startswith("# HELP")]
    assert len(help_lines) >= 5


async def test_metrics_has_type_lines(rest):
    """Metrics include # TYPE annotations."""
    text = await _get_metrics(rest)
    type_lines = [l for l in text.splitlines() if l.startswith("# TYPE")]
    assert len(type_lines) >= 5


# ── Numeric Values ───────────────────────────────────────

async def test_metrics_entity_count_numeric(rest):
    """marge_entity_count value is a parseable number."""
    text = await _get_metrics(rest)
    for line in text.splitlines():
        if line.startswith("marge_entity_count "):
            val = line.split()[-1]
            float(val)  # should not raise
            assert float(val) >= 0
            return
    pytest.fail("marge_entity_count metric line not found")


async def test_metrics_uptime_positive(rest):
    """marge_uptime_seconds is positive."""
    text = await _get_metrics(rest)
    for line in text.splitlines():
        if line.startswith("marge_uptime_seconds "):
            val = float(line.split()[-1])
            assert val > 0
            return
    pytest.fail("marge_uptime_seconds metric line not found")


async def test_metrics_memory_positive(rest):
    """marge_memory_rss_bytes is positive."""
    text = await _get_metrics(rest)
    for line in text.splitlines():
        if line.startswith("marge_memory_rss_bytes "):
            val = float(line.split()[-1])
            assert val > 0
            return
    pytest.fail("marge_memory_rss_bytes metric line not found")


# ── State Change Effect on Counters ──────────────────────

async def test_metrics_state_changes_increase(rest):
    """State change increments marge_state_changes_total."""
    text1 = await _get_metrics(rest)
    count1 = None
    for line in text1.splitlines():
        if line.startswith("marge_state_changes_total "):
            count1 = int(line.split()[-1])
            break
    assert count1 is not None

    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.prom_sc_{tag}", "42")

    text2 = await _get_metrics(rest)
    for line in text2.splitlines():
        if line.startswith("marge_state_changes_total "):
            count2 = int(line.split()[-1])
            assert count2 > count1
            return
    pytest.fail("marge_state_changes_total not found after state change")


# ── Automation Triggers ──────────────────────────────────

async def test_metrics_has_automation_triggers(rest):
    """Metrics include automation trigger counter with labels."""
    text = await _get_metrics(rest)
    assert "marge_automation_triggers_total" in text
    # Should have id and alias labels
    assert 'id="' in text
    assert 'alias="' in text


# ── No Auth Required ─────────────────────────────────────

async def test_metrics_no_auth_required(rest):
    """Metrics endpoint does not require auth header."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    assert len(resp.text) > 0
