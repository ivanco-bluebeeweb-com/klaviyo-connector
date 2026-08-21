"""Connect/disconnect Klaviyo, account info -- same validate-before-save
pattern as DataForSEO Connector's connect_dataforseo: a bad key is rejected
immediately (one cheap GET against Klaviyo's own accounts endpoint) instead
of failing silently on first real use later.
"""
from __future__ import annotations

from imperal_sdk import ActionResult, sdl

import klaviyo_client as kc
from app import ext, chat
from models import (
    NoParams,
    ConnectKlaviyoParams, ProviderConnection,
    KlaviyoAccount,
)

_SECRET_NAME = "klaviyo_api_key"


async def _get_key(ctx) -> str:
    """Async because ctx.secrets.get() is a coroutine on the real SDK --
    a sync wrapper here would always return a truthy coroutine object
    instead of the actual stored value (or its absence), silently
    breaking every connection check in this connector."""
    return (await ctx.secrets.get(_SECRET_NAME)) or ""


@chat.function(
    name="connect_klaviyo", data_model=ProviderConnection,
    description=(
        "Connect Klaviyo by saving your own private API key, after checking "
        "it actually works. Get it from Klaviyo: Settings > API Keys > "
        "Create Private API Key."
    ),
)
async def connect_klaviyo(ctx, params: ConnectKlaviyoParams) -> ActionResult:
    """Validate the key against Klaviyo before saving it."""
    key = (params.api_key or "").strip()
    if not key:
        return ActionResult.error("API key is required.")
    try:
        payload = await kc.request(ctx, key, "GET", "/accounts/")
    except kc.KlaviyoError as exc:
        return ActionResult.error(f"Klaviyo rejected this API key: {exc.detail}")
    except Exception as exc:  # network/timeout etc.
        return ActionResult.error(f"Could not reach Klaviyo to verify the key: {exc}")

    rows = payload.get("data") or []
    detail = ""
    if rows:
        attrs = rows[0].get("attributes") or {}
        detail = attrs.get("contact_information", {}).get("organization_name", "") or attrs.get("public_api_key", "")

    await ctx.secrets.set(_SECRET_NAME, key)
    return ActionResult.success(
        ProviderConnection(id="klaviyo", title="Klaviyo", connected=True, detail=detail),
        summary=f"Klaviyo connected{f' ({detail})' if detail else ''}.",
    )


@chat.function(
    name="disconnect_klaviyo", data_model=ProviderConnection,
    description=(
        "Disconnect Klaviyo: deletes the saved API key. Nothing in your "
        "Klaviyo account is changed -- lists, flows, campaigns, and "
        "profiles all stay exactly as they are; only this connector's "
        "access to them stops."
    ),
)
async def disconnect_klaviyo(ctx, params: NoParams) -> ActionResult:
    """Delete the saved key; existing Klaviyo data is untouched."""
    await ctx.secrets.delete(_SECRET_NAME)
    return ActionResult.success(
        ProviderConnection(id="klaviyo", title="Klaviyo", connected=False),
        summary="Klaviyo disconnected.",
    )


@chat.function(
    name="get_klaviyo_connection", data_model=ProviderConnection,
    description="Check whether Klaviyo is currently connected (does not reveal the saved API key).",
)
async def get_klaviyo_connection(ctx, params: NoParams) -> ActionResult:
    """Report whether a key is saved (never echoes it)."""
    key = await _get_key(ctx)
    return ActionResult.success(
        ProviderConnection(id="klaviyo", title="Klaviyo", connected=bool(key)),
        summary="Klaviyo is connected." if key else "Klaviyo is not connected yet.",
    )


@chat.function(
    name="get_klaviyo_account", data_model=KlaviyoAccount,
    description="Read the connected Klaviyo account's own profile: contact email, timezone, public API key, and whether it's a test account.",
)
async def get_klaviyo_account(ctx, params: NoParams) -> ActionResult:
    """Read the connected Klaviyo account's own profile."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Klaviyo is not connected yet. Call connect_klaviyo first.")
    payload = await kc.request(ctx, key, "GET", "/accounts/")
    rows = payload.get("data") or []
    if not rows:
        return ActionResult.error("Klaviyo returned no account data.")
    row = rows[0]
    attrs = row.get("attributes") or {}
    contact = attrs.get("contact_information") or {}
    return ActionResult.success(
        KlaviyoAccount(
            id=row.get("id", ""),
            title=contact.get("organization_name", "") or "Klaviyo account",
            contact_email=contact.get("default_sender_email", ""),
            timezone=attrs.get("timezone", ""),
            public_api_key=attrs.get("public_api_key", ""),
            test_account=bool(attrs.get("test_account", False)),
        ),
        summary="Read Klaviyo account details.",
    )
