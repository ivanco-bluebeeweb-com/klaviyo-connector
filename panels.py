"""Panel UI -- connect form + campaigns/flows dashboard.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as MuleSoft
Connector's / Shopify Connector's / Stripe Connector's panels.py).

Every section is a plain ui.Stack, content stacked vertically and
left-aligned, sections separated by ui.Divider() -- no Card
border/background/shadow anywhere in this slot.

CENTER SLOT -- a real post-connect dashboard (campaigns + flows), not the
canonical "Nothing to show here" placeholder, per
POST_CONNECT_EXPERIENCE.md for this app.
"""
from __future__ import annotations

from imperal_sdk import ui

import klaviyo_client as kc
from app import ext
from accounts import _get_key
import handlers_campaigns as h


def _connect_section(connected: bool, detail: str) -> ui.UINode:
    if connected:
        return ui.Stack(direction="v", gap=2, align="start", children=[
            ui.Text("Klaviyo", variant="subtitle"),
            ui.Text(f"Connected{f' — {detail}' if detail else ''}", variant="caption"),
            ui.Button("Disconnect", variant="danger", size="sm",
                      on_click=ui.Call("disconnect_klaviyo")),
        ])
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Text("Connect Klaviyo", variant="subtitle"),
        ui.Text(
            "Get a private API key from Klaviyo: Settings > API Keys > "
            "Create Private API Key. Verified before saving.",
            variant="caption",
        ),
        ui.Link(label="Open klaviyo.com", href="https://www.klaviyo.com/"),
        ui.Form(
            action="connect_klaviyo",
            submit_label="Verify and connect",
            full_width=True,
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Private API key", variant="caption"),
                    ui.Password(param_name="api_key", placeholder="pk_...", full_width=True),
                ]),
            ],
        ),
    ])


async def _quick_counts(ctx) -> list[dict]:
    key = await _get_key(ctx)
    if not key:
        return []
    counts = []
    for label, path in [
        ("Profiles", "/profiles/"),
        ("Lists", "/lists/"),
        ("Segments", "/segments/"),
        ("Campaigns", "/campaigns/?filter=" + kc.build_filter([kc.equals("messages.channel", "email")])),
        ("Flows", "/flows/"),
    ]:
        try:
            payload = await kc.request(ctx, key, "GET", path, params={"page[size]": 1})
            rows = payload.get("data") or []
            counts.append({"key": label, "value": f"{len(rows)}+" if rows else "0"})
        except Exception:
            counts.append({"key": label, "value": "—"})
    return counts


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__klaviyo_settings"),
    )


@ext.panel("klaviyo_overview", slot="left", title="Klaviyo", icon="✉️")
async def klaviyo_overview_panel(ctx, **kwargs) -> object:
    key = await _get_key(ctx)
    connected = bool(key)
    detail = ""
    if connected:
        try:
            payload = await kc.request(ctx, key, "GET", "/accounts/")
            rows = payload.get("data") or []
            if rows:
                attrs = rows[0].get("attributes") or {}
                detail = attrs.get("contact_information", {}).get("organization_name", "") or ""
        except Exception:
            connected = False

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            _connect_section(connected, detail),
            ui.Divider(),
            _settings_button(),
        ])

    counts = await _quick_counts(ctx)
    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        _connect_section(connected, detail),
        ui.Divider(),
        ui.Text("Account overview", variant="subtitle"),
        ui.KeyValue(columns=2, items=counts) if counts else ui.Text("Unable to load counts.", variant="caption"),
        ui.Divider(),
        ui.Button("View campaigns & flows", variant="primary", size="sm", full_width=True,
                  icon="Mail", on_click=ui.Call("__panel__klaviyo_center")),
        ui.Divider(),
        _settings_button(),
    ])


def _campaign_row(c) -> dict:
    return {
        "name": c.name or c.title or c.id, "channel": c.channel or "—",
        "status": c.status or "—", "send_time": (c.send_time or "")[:16] or "—",
        "campaign_id": c.id,
    }


def _flow_row(f) -> dict:
    return {
        "name": f.name or f.title or f.id, "trigger": f.trigger_type or "—",
        "status": f.status or "—", "flow_id": f.id,
    }


@ext.panel("klaviyo_center", slot="center", title="Klaviyo", icon="✉️", center_overlay=True)
async def klaviyo_center_panel(ctx, campaign_id: str = "", flow_id: str = "", **kwargs) -> object:
    """Post-connect main screen: campaigns + flows dashboard, or a detail
    view when campaign_id/flow_id is passed (master-detail via the same
    panel_id, per UI_COMPONENT_VOCABULARY.md §3)."""
    key = await _get_key(ctx)
    if not key:
        return ui.Empty(
            message="Connect your Klaviyo account from the sidebar to see campaigns here.",
            icon="✉️",
        )
    if campaign_id:
        return await _campaign_detail(ctx, campaign_id)
    if flow_id:
        return await _flow_detail(ctx, flow_id)
    return await _campaigns_dashboard(ctx)


async def _campaigns_dashboard(ctx) -> ui.UINode:
    from models import ListCampaignsParams, ListFlowsParams
    campaigns_result = await h.list_campaigns(ctx, ListCampaignsParams())
    flows_result = await h.list_flows(ctx, ListFlowsParams())

    body: list[ui.UINode] = [ui.Text("Campaigns", variant="subtitle")]
    if campaigns_result.success and campaigns_result.data and campaigns_result.data.items:
        rows = [_campaign_row(c) for c in campaigns_result.data.items[:50]]
        body.append(ui.DataTable(
            columns=[
                ui.DataColumn("name", "Campaign", sortable=True),
                ui.DataColumn("channel", "Channel", sortable=True),
                ui.DataColumn("status", "Status", sortable=True),
                ui.DataColumn("send_time", "Send time", sortable=True),
            ],
            rows=rows,
            on_row_click=ui.Call("__panel__klaviyo_center", campaign_id=""),
        ))
    else:
        body.append(ui.Text("No campaigns yet.", variant="caption"))

    body.append(ui.Divider())
    body.append(ui.Text("Flows", variant="subtitle"))
    if flows_result.success and flows_result.data and flows_result.data.items:
        rows = [_flow_row(f) for f in flows_result.data.items[:50]]
        body.append(ui.DataTable(
            columns=[
                ui.DataColumn("name", "Flow", sortable=True),
                ui.DataColumn("trigger", "Trigger", sortable=True),
                ui.DataColumn("status", "Status", sortable=True),
            ],
            rows=rows,
            on_row_click=ui.Call("__panel__klaviyo_center", flow_id=""),
        ))
    else:
        body.append(ui.Text("No flows yet.", variant="caption"))

    return ui.Stack(direction="v", gap=3, align="stretch", children=body)


async def _campaign_detail(ctx, campaign_id: str) -> ui.UINode:
    from models import CampaignIdParams
    result = await h.get_campaign(ctx, CampaignIdParams(campaign_id=campaign_id))
    if not result.success or not result.data:
        return ui.Error(message="Could not load this campaign.", retry=ui.Call("__panel__klaviyo_center"))
    c = result.data
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("Back to dashboard", variant="secondary", size="sm",
                  on_click=ui.Call("__panel__klaviyo_center")),
        ui.KeyValue(columns=2, items=[
            {"key": "Name", "value": c.name or c.title},
            {"key": "Channel", "value": c.channel or "—"},
            {"key": "Status", "value": c.status or "—"},
            {"key": "Send time", "value": c.send_time or "—"},
            {"key": "Created", "value": c.created or "—"},
        ]),
        ui.Row(children=[
            ui.Button("Send now", variant="primary", size="sm",
                      on_click=ui.Call("send_campaign", campaign_id=c.id)),
        ]),
    ])


async def _flow_detail(ctx, flow_id: str) -> ui.UINode:
    from models import FlowIdParams
    result = await h.get_flow(ctx, FlowIdParams(flow_id=flow_id))
    if not result.success or not result.data:
        return ui.Error(message="Could not load this flow.", retry=ui.Call("__panel__klaviyo_center"))
    f = result.data
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("Back to dashboard", variant="secondary", size="sm",
                  on_click=ui.Call("__panel__klaviyo_center")),
        ui.KeyValue(columns=2, items=[
            {"key": "Name", "value": f.name or f.title},
            {"key": "Trigger", "value": f.trigger_type or "—"},
            {"key": "Status", "value": f.status or "—"},
            {"key": "Created", "value": f.created or "—"},
        ]),
        ui.Row(children=[
            ui.Button("Set live", variant="primary", size="sm",
                      on_click=ui.Call("set_flow_status", flow_id=f.id, status="live")),
            ui.Button("Pause", variant="secondary", size="sm",
                      on_click=ui.Call("set_flow_status", flow_id=f.id, status="paused")),
        ]),
    ])
