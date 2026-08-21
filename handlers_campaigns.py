"""Campaigns (one-off email/SMS sends), Flows (automated multi-step
sequences triggered by events/segments), Templates (reusable HTML email
bodies), and Tags (organizing labels attachable to campaigns/flows/lists/
segments). These are the "marketing send" layer sitting on top of
Profiles/Lists/Segments/Events.
"""
from __future__ import annotations

import klaviyo_client as kc
from imperal_sdk import ActionResult, sdl

from app import ext, chat
from accounts import _get_key
from models import (
    ListCampaignsParams, CampaignIdParams, CreateCampaignParams,
    SendCampaignParams, Campaign, CampaignList,
    ListFlowsParams, FlowIdParams, SetFlowStatusParams, Flow, FlowList,
    ListTemplatesParams, TemplateIdParams, CreateTemplateParams,
    Template, TemplateList,
    ListTagsParams, CreateTagParams, TagResourceParams, Tag, TagList,
    DeleteResult,
)


async def _need_key(ctx):
    key = await _get_key(ctx)
    if not key:
        raise ValueError("Klaviyo is not connected yet. Call connect_klaviyo first.")
    return key


# ──────────────────────────────────────────────────────────────────────────
# Campaigns.
# ──────────────────────────────────────────────────────────────────────────


def _campaign_from_row(row: dict) -> Campaign:
    a = row.get("attributes") or {}
    send_opts = a.get("send_strategy") or {}
    return Campaign(
        id=row.get("id", ""),
        title=a.get("name", "") or row.get("id", ""),
        name=a.get("name", "") or "",
        status=a.get("status", "") or "",
        channel=(a.get("channel") or "email"),
        created=a.get("created_at", "") or "",
        updated=a.get("updated_at", "") or "",
        send_time=send_opts.get("datetime", "") if isinstance(send_opts, dict) else "",
    )


@chat.function(
    name="list_campaigns", data_model=CampaignList,
    description="List Klaviyo campaigns (one-off email or SMS sends), filtered by channel, with cursor pagination.",
)
async def list_campaigns(ctx, params: ListCampaignsParams) -> ActionResult:
    """List campaigns (one-off email/SMS sends) filtered by channel."""
    key = await _need_key(ctx)
    channel = params.channel or "email"
    q: dict = {
        "filter": f"equals(messages.channel,'{channel}')",
        "page[size]": params.page_size,
    }
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/campaigns/", params=q)
    rows = payload.get("data") or []
    items = [_campaign_from_row(r) for r in rows]
    next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(
        CampaignList(items=items, next_cursor=next_cursor),
        summary=f"{len(items)} campaign(s).",
    )


@chat.function(name="get_campaign", data_model=Campaign, description="Read one Klaviyo campaign's details by id.")
async def get_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    """Read one campaign's details by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/campaigns/{params.campaign_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error("Campaign not found.")
    return ActionResult.success(_campaign_from_row(row), summary="Campaign loaded.")


@chat.function(
    name="create_campaign", data_model=Campaign,
    description=(
        "Create a new Klaviyo email or SMS campaign targeting one or more "
        "lists/segments. Created in draft -- use send_campaign to actually "
        "send it, or schedule it from the Klaviyo UI."
    ),
)
async def create_campaign(ctx, params: CreateCampaignParams) -> ActionResult:
    """Create a new draft campaign."""
    key = await _need_key(ctx)
    audiences = {"included": list(params.list_ids) + list(params.segment_ids)}
    attrs: dict = {
        "name": params.name,
        "audiences": audiences,
        "send_strategy": {"method": "immediate"},
        "campaign-messages": {
            "data": [
                {
                    "type": "campaign-message",
                    "attributes": {
                        "channel": params.channel or "email",
                        "label": params.name,
                        "content": {
                            "subject": params.subject,
                            "from_email": params.from_email,
                            "from_label": params.from_label,
                        } if (params.channel or "email") == "email" else {"body": params.subject},
                    },
                }
            ]
        },
    }
    body = {"data": {"type": "campaign", "attributes": attrs}}
    payload = await kc.request(ctx, key, "POST", "/campaigns/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_campaign_from_row(row), summary=f"Campaign '{params.name}' created as draft.")


@chat.function(
    name="send_campaign", data_model=Campaign,
    description="Send a Klaviyo campaign now. The campaign must already have content and an audience configured.",
)
async def send_campaign(ctx, params: SendCampaignParams) -> ActionResult:
    """Queue an existing draft campaign to send now."""
    key = await _need_key(ctx)
    body = {"data": {"type": "campaign-send-job", "id": params.campaign_id}}
    await kc.request(ctx, key, "POST", "/campaign-send-jobs/", json_body=body)
    return ActionResult.success(
        Campaign(id=params.campaign_id, title=params.campaign_id, status="sending"),
        summary=f"Campaign {params.campaign_id} queued to send.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Flows.
# ──────────────────────────────────────────────────────────────────────────


def _flow_from_row(row: dict) -> Flow:
    a = row.get("attributes") or {}
    trigger = a.get("trigger_type", "") or ""
    return Flow(
        id=row.get("id", ""),
        title=a.get("name", "") or row.get("id", ""),
        name=a.get("name", "") or "",
        status=a.get("status", "") or "",
        trigger_type=trigger,
        created=a.get("created", "") or "",
        updated=a.get("updated", "") or "",
    )


@chat.function(name="list_flows", data_model=FlowList, description="List Klaviyo flows (automated multi-step sequences triggered by events, segment membership, or dates).")
async def list_flows(ctx, params: ListFlowsParams) -> ActionResult:
    """List flows (automated multi-step sequences) with cursor pagination."""
    key = await _need_key(ctx)
    q: dict = {"page[size]": params.page_size}
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/flows/", params=q)
    rows = payload.get("data") or []
    items = [_flow_from_row(r) for r in rows]
    next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(FlowList(items=items, next_cursor=next_cursor), summary=f"{len(items)} flow(s).")


@chat.function(name="get_flow", data_model=Flow, description="Read one Klaviyo flow's details by id.")
async def get_flow(ctx, params: FlowIdParams) -> ActionResult:
    """Read one flow's details by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/flows/{params.flow_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error("Flow not found.")
    return ActionResult.success(_flow_from_row(row), summary="Flow loaded.")


@chat.function(
    name="set_flow_status", data_model=Flow,
    description="Turn a Klaviyo flow live, or pause/draft it. status must be one of: live, draft, manual.",
)
async def set_flow_status(ctx, params: SetFlowStatusParams) -> ActionResult:
    """Activate, pause, or archive an existing flow."""
    key = await _need_key(ctx)
    if params.status not in ("live", "draft", "manual"):
        return ActionResult.error("status must be one of: live, draft, manual.")
    body = {"data": {"type": "flow", "id": params.flow_id, "attributes": {"status": params.status}}}
    payload = await kc.request(ctx, key, "PATCH", f"/flows/{params.flow_id}/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_flow_from_row(row), summary=f"Flow {params.flow_id} set to '{params.status}'.")


# ──────────────────────────────────────────────────────────────────────────
# Templates.
# ──────────────────────────────────────────────────────────────────────────


def _template_from_row(row: dict) -> Template:
    a = row.get("attributes") or {}
    return Template(
        id=row.get("id", ""),
        title=a.get("name", "") or row.get("id", ""),
        name=a.get("name", "") or "",
        created=a.get("created", "") or "",
        updated=a.get("updated", "") or "",
    )


@chat.function(name="list_templates", data_model=TemplateList, description="List reusable Klaviyo email templates.")
async def list_templates(ctx, params: ListTemplatesParams) -> ActionResult:
    """List reusable email templates with cursor pagination."""
    key = await _need_key(ctx)
    q: dict = {"page[size]": params.page_size}
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/templates/", params=q)
    rows = payload.get("data") or []
    items = [_template_from_row(r) for r in rows]
    next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(TemplateList(items=items, next_cursor=next_cursor), summary=f"{len(items)} template(s).")


@chat.function(name="get_template", data_model=Template, description="Read one Klaviyo email template's HTML by id.")
async def get_template(ctx, params: TemplateIdParams) -> ActionResult:
    """Read one template's full HTML content by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/templates/{params.template_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error("Template not found.")
    return ActionResult.success(_template_from_row(row), summary="Template loaded.")


@chat.function(name="create_template", data_model=Template, description="Create a new reusable Klaviyo email template from raw HTML.")
async def create_template(ctx, params: CreateTemplateParams) -> ActionResult:
    """Create a new reusable HTML email template."""
    key = await _need_key(ctx)
    body = {"data": {"type": "template", "attributes": {"name": params.name, "editor_type": "CODE", "html": params.html}}}
    payload = await kc.request(ctx, key, "POST", "/templates/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_template_from_row(row), summary=f"Template '{params.name}' created.")


# ──────────────────────────────────────────────────────────────────────────
# Tags.
# ──────────────────────────────────────────────────────────────────────────


@chat.function(name="list_tags", data_model=TagList, description="List tags defined on this Klaviyo account -- organizing labels attachable to campaigns/flows/lists/segments.")
async def list_tags(ctx, params: ListTagsParams) -> ActionResult:
    """List tags defined in this Klaviyo account."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", "/tags/")
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(Tag(id=r.get("id", ""), title=a.get("name", "") or r.get("id", ""), name=a.get("name", "") or ""))
    return ActionResult.success(TagList(items=items), summary=f"{len(items)} tag(s).")


@chat.function(name="create_tag", data_model=Tag, description="Create a new Klaviyo tag.")
async def create_tag(ctx, params: CreateTagParams) -> ActionResult:
    """Create a new tag."""
    key = await _need_key(ctx)
    body = {"data": {"type": "tag", "attributes": {"name": params.name}}}
    payload = await kc.request(ctx, key, "POST", "/tags/", json_body=body)
    row = payload.get("data") or {}
    a = row.get("attributes") or {}
    return ActionResult.success(Tag(id=row.get("id", ""), title=a.get("name", ""), name=a.get("name", "")), summary=f"Created tag '{params.name}'.")


@chat.function(name="tag_resource", data_model=Tag, description="Attach an existing tag to a campaign, flow, list, or segment by id.")
async def tag_resource(ctx, params: TagResourceParams) -> ActionResult:
    """Attach an existing tag to a campaign, flow, list, or segment."""
    key = await _need_key(ctx)
    plural = {"campaign": "campaigns", "flow": "flows", "list": "lists", "segment": "segments"}.get(params.resource_type)
    if not plural:
        return ActionResult.error("resource_type must be one of: campaign, flow, list, segment.")
    body = {"data": [{"type": params.resource_type, "id": params.resource_id}]}
    await kc.request(ctx, key, "POST", f"/tags/{params.tag_id}/relationships/{plural}/", json_body=body)
    return ActionResult.success(Tag(id=params.tag_id, title=params.tag_id), summary=f"Tagged {params.resource_type} {params.resource_id} with tag {params.tag_id}.")
