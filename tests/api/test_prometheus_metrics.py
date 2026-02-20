"""
CTS -- Prometheus Metrics Endpoint Depth Tests

Tests GET /metrics for Prometheus-compatible output format,
metric names, types, and values.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_metrics_returns_200(rest):
    """GET /metrics returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_metrics_content_type(rest):
    """Prometheus metrics have correct content-type."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct


async def test_metrics_has_info(rest):
    """Metrics include marge_info gauge."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_info" in text
    assert "version" in text


async def test_metrics_has_uptime(rest):
    """Metrics include marge_uptime_seconds counter."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_uptime_seconds" in text
    assert "# TYPE marge_uptime_seconds counter" in text


async def test_metrics_has_startup(rest):
    """Metrics include marge_startup_seconds gauge."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_startup_seconds" in text


async def test_metrics_has_entity_count(rest):
    """Metrics include marge_entity_count gauge."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_entity_count" in text
    assert "# TYPE marge_entity_count gauge" in text


async def test_metrics_has_state_changes(rest):
    """Metrics include marge_state_changes_total counter."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_state_changes_total" in text
    assert "# TYPE marge_state_changes_total counter" in text


async def test_metrics_has_events_fired(rest):
    """Metrics include marge_events_fired_total counter."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_events_fired_total" in text


async def test_metrics_has_latency(rest):
    """Metrics include latency gauges."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_latency_avg_microseconds" in text
    assert "marge_latency_max_microseconds" in text


async def test_metrics_has_memory(rest):
    """Metrics include marge_memory_rss_bytes gauge."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_memory_rss_bytes" in text
    assert "# TYPE marge_memory_rss_bytes gauge" in text


async def test_metrics_has_ws_connections(rest):
    """Metrics include marge_ws_connections gauge."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_ws_connections" in text


async def test_metrics_has_automation_triggers(rest):
    """Metrics include marge_automation_triggers_total counter."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    text = resp.text
    assert "marge_automation_triggers_total" in text


async def test_metrics_valid_prometheus_format(rest):
    """Metrics follow Prometheus exposition format."""
    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    lines = resp.text.strip().split("\n")
    for line in lines:
        if line.startswith("#"):
            # Comment line — HELP or TYPE
            assert line.startswith("# HELP") or line.startswith("# TYPE")
        else:
            # Metric line — should have metric_name value or metric_name{labels} value
            parts = line.split(" ")
            assert len(parts) >= 2, f"Invalid metric line: {line}"


async def test_metrics_entity_count_positive(rest):
    """Entity count in metrics is positive."""
    # Ensure at least one entity
    await rest.set_state("sensor.prom_test", "val")

    resp = await rest.client.get(f"{rest.base_url}/metrics", headers=rest._headers())
    for line in resp.text.split("\n"):
        if line.startswith("marge_entity_count "):
            count = int(line.split(" ")[1])
            assert count > 0
            break
    else:
        pytest.fail("marge_entity_count metric not found")
