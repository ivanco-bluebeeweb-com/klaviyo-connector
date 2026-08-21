"""Panel UI: a single right-slot panel -- connect card plus a quick
account overview (list/segment/campaign counts) so a first-time user sees
their Klaviyo account is actually wired up without needing chat. Simpler
shape than DataForSEO Connector's project-scoped panels because Klaviyo
has no per-project concept here -- one connected account, one flat API
surface across profiles/lists/segments/campaigns/flows/etc.
"""
from __future__ import annotations

from imperal_sdk import ui

import klaviyo_client as kc
from app import ext
from accounts import _get_key


def _connect_card(connected: bool, detail: str) -> ui.UINode:
    if connected:
        return ui.Card(
            title="Klaviyo",
            subtitle=f"Connected{f' — {detail}' if detail else ''}",
            content=ui.Stack(direction="v", gap=2, children=[
                ui.Text("Your private API key is saved and verified.", variant="caption"),
                ui.Button("Disconnect", variant="danger", size="sm",
                          on_click=ui.Call("disconnect_klaviyo")),
            ]),
        )
    return ui.Card(
        title="Connect Klaviyo",
        subtitle="Bring your own Klaviyo account",
        content=ui.Stack(direction="v", gap=2, children=[
            ui.Text(
                "Get a private API key from Klaviyo: Settings > API Keys > "
                "Create Private API Key. Verified before saving.",
                variant="caption",
            ),
            ui.Link(label="Open klaviyo.com", href="https://www.klaviyo.com/"),
            ui.Form(
                action="connect_klaviyo",
                submit_label="Verify and connect",
                children=[
                    ui.Password(param_name="api_key", placeholder="Private API key (pk_...)"),
                ],
            ),
        ]),
    )


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


@ext.panel("klaviyo_overview", slot="right", title="Klaviyo", icon="✉️",
           default_width=300, min_width=240, max_width=420)
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

    children: list[ui.UINode] = [_connect_card(connected, detail)]

    if connected:
        counts = await _quick_counts(ctx)
        if counts:
            children.append(ui.Card(title="Account overview", content=ui.KeyValue(columns=2, items=counts)))
        children.append(ui.Card(
            title="Quick actions",
            content=ui.Stack(direction="v", gap=2, children=[
                ui.Button("List profiles", variant="secondary", size="sm",
                          on_click=ui.Call("list_profiles")),
                ui.Button("List campaigns", variant="secondary", size="sm",
                          on_click=ui.Call("list_campaigns")),
                ui.Button("List flows", variant="secondary", size="sm",
                          on_click=ui.Call("list_flows")),
            ]),
        ))

    return ui.Stack(direction="v", gap=3, children=children)
