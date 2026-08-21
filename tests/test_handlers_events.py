"""Tests for handlers_events.py -- Events, Metrics."""
from __future__ import annotations

import pytest

import handlers_events as he
from models import CreateEventParams, ListEventsParams, ListMetricsParams


@pytest.mark.asyncio
async def test_create_event_requires_connection(ctx):
    with pytest.raises(ValueError):
        await he.create_event(ctx, CreateEventParams(email="a@example.com", metric_name="Placed Order"))


@pytest.mark.asyncio
async def test_create_event_requires_identifier(ctx_connected):
    result = await he.create_event(ctx_connected, CreateEventParams(metric_name="Placed Order"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_create_event_success(ctx_connected):
    ctx_connected.http.mock_post("/events/", {"data": {"id": "evt_1", "attributes": {}}}, status=202)
    result = await he.create_event(
        ctx_connected,
        CreateEventParams(email="a@example.com", metric_name="Placed Order", value=42.5),
    )
    assert result.error is None


@pytest.mark.asyncio
async def test_list_events_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/events/",
        {"data": [{"id": "evt_1", "attributes": {"timestamp": "2026-01-01T00:00:00Z"}}], "links": {}},
        status=200,
    )
    result = await he.list_events(ctx_connected, ListEventsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_list_metrics_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/metrics/",
        {"data": [{"id": "met_1", "attributes": {"name": "Placed Order"}}], "links": {}},
        status=200,
    )
    result = await he.list_metrics(ctx_connected, ListMetricsParams())
    assert result.error is None
    assert len(result.data.items) == 1
