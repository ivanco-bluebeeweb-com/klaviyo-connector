"""The single 'App settings' screen (center slot) -- key management for
Klaviyo Connector. Split out of panels.py per the same convention as
MuleSoft Connector's / Shopify Connector's / Stripe Connector's
panels_settings.py.

Per ~/UI_INTERFACE_STANDARD.md: the left sidebar never wraps the connect
form in a Card, and disconnect (never exposed in the sidebar itself)
lives here. The one secondary "App settings" button sits LAST at the
bottom of the sidebar. Klaviyo has exactly one connected account (a
single private API key), unlike MuleSoft's per-organization list, so
this screen has one row, not a list.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from accounts import _get_key


@ext.panel("klaviyo_settings", slot="center", title="Klaviyo settings", center_overlay=True)
async def klaviyo_settings_panel(ctx, **kwargs) -> object:
    key = await _get_key(ctx)
    if not key:
        return ui.Stack(direction="v", gap=2, align="start", children=[
            ui.Text("Connections", variant="heading"),
            ui.Text("No Klaviyo account connected yet.", variant="caption"),
        ])
    return ui.Stack(direction="v", gap=3, align="start", children=[
        ui.Text("Connections", variant="heading"),
        ui.Stack(direction="v", gap=1, align="start", children=[
            ui.Text("Klaviyo account", variant="body"),
            ui.Text("Private API key saved and verified.", variant="caption"),
            ui.Button(
                "Disconnect", variant="danger", size="sm",
                on_click=ui.Call("disconnect_klaviyo"),
            ),
        ]),
    ])
