"""Events and Metrics -- the behavioral data layer. An Event is one
timestamped occurrence tied to a profile (e.g. "Placed Order", "Viewed
Product") with a numeric value and arbitrary properties; a Metric is the
named event TYPE itself (Klaviyo auto-creates a metric the first time an
event with a new name is recorded). Events feed flows, segments, and
analytics -- this is the data most ecommerce/product integrations send.
"""
from __future__ import annotations

import klaviyo_client as kc
from imperal_sdk import ActionResult, sdl

from app import ext, chat
from accounts import _get_key
from models import (
    CreateEventParams, ListEventsParams, KlaviyoEvent, KlaviyoEventList,
    ListMetricsParams, Metric, MetricList,
)


async def _need_key(ctx):
    key = await _get_key(ctx)
    if not key:
        raise ValueError("Klaviyo is not connected yet. Call connect_klaviyo first.")
    return key


@chat.function(
    name="create_event", data_model=KlaviyoEvent,
    description=(
        "Track a custom event for a profile (e.g. 'Placed Order', 'Viewed "
        "Product') with a numeric value and arbitrary properties. Creates "
        "the profile automatically if it doesn't exist yet, and creates "
        "the metric automatically the first time this event name is used."
    ),
)
async def create_event(ctx, params: CreateEventParams) -> ActionResult:
    """Track a custom behavioral event for a profile."""
    key = await _need_key(ctx)
    if not (params.email or params.phone_number or params.external_id):
        return ActionResult.error("At least one of email, phone_number, or external_id is required to identify the profile.")

    profile_attrs: dict = {}
    if params.email:
        profile_attrs["email"] = params.email
    if params.phone_number:
        profile_attrs["phone_number"] = params.phone_number
    if params.external_id:
        profile_attrs["external_id"] = params.external_id

    event_attrs: dict = {
        "properties": params.properties or {},
        "metric": {"data": {"type": "metric", "attributes": {"name": params.metric_name}}},
        "profile": {"data": {"type": "profile", "attributes": profile_attrs}},
    }
    if params.value:
        event_attrs["value"] = params.value
    if params.unique_id:
        event_attrs["unique_id"] = params.unique_id

    body = {"data": {"type": "event", "attributes": event_attrs}}
    await kc.request(ctx, key, "POST", "/events/", json_body=body)
    return ActionResult.success(
        KlaviyoEvent(id="", title=params.metric_name, metric_id="", profile_id="", value=params.value),
        summary=f"Tracked event '{params.metric_name}'.",
    )


def _event_from_row(row: dict) -> KlaviyoEvent:
    a = row.get("attributes") or {}
    rel = row.get("relationships") or {}
    metric_id = ((rel.get("metric") or {}).get("data") or {}).get("id", "")
    profile_id = ((rel.get("profile") or {}).get("data") or {}).get("id", "")
    return KlaviyoEvent(
        id=row.get("id", ""),
        title=a.get("datetime", "") or row.get("id", ""),
        metric_id=metric_id,
        profile_id=profile_id,
        value=float(a.get("value") or 0.0),
        datetime=a.get("datetime", "") or "",
    )


@chat.function(name="list_events", data_model=KlaviyoEventList, description="List recorded Klaviyo events, optionally filtered by metric id or profile id, with cursor pagination.")
async def list_events(ctx, params: ListEventsParams) -> ActionResult:
    """List recorded events, optionally filtered by profile/metric, with cursor pagination."""
    key = await _need_key(ctx)
    filters = []
    if params.metric_id:
        filters.append(kc.equals("metric_id", params.metric_id))
    if params.profile_id:
        filters.append(kc.equals("profile_id", params.profile_id))
    query = kc.page_params(params.cursor, params.page_size)
    if filters:
        query["filter"] = kc.build_filter(filters)
    payload = await kc.request(ctx, key, "GET", "/events/", params=query)
    rows = payload.get("data") or []
    result = KlaviyoEventList(items=[_event_from_row(r) for r in rows])
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"Found {len(rows)} event(s).")


@chat.function(name="list_metrics", data_model=MetricList, description="List all event-type metrics Klaviyo has recorded for this account (e.g. 'Placed Order', 'Opened Email'), with cursor pagination.")
async def list_metrics(ctx, params: ListMetricsParams) -> ActionResult:
    """List metrics (event types) known to this Klaviyo account."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", "/metrics/", params=kc.page_params(params.cursor, 20))
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(Metric(id=r.get("id", ""), title=a.get("name", ""), name=a.get("name", ""), integration_name=(a.get("integration") or {}).get("name", "") if isinstance(a.get("integration"), dict) else "", created=a.get("created", "") or ""))
    result = MetricList(items=items)
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"Found {len(rows)} metric(s).")
