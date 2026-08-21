"""Tests for accounts.py -- connect/disconnect/connection-status/account info."""
from __future__ import annotations

import pytest

import accounts as acc
from models import ConnectKlaviyoParams, NoParams


@pytest.mark.asyncio
async def test_connect_klaviyo_rejects_empty_key(ctx):
    result = await acc.connect_klaviyo(ctx, ConnectKlaviyoParams(api_key=""))
    assert result.error is not None


@pytest.mark.asyncio
async def test_connect_klaviyo_rejects_bad_key(ctx):
    ctx.http.mock_get("/accounts/", {"errors": [{"detail": "Invalid API key."}]}, status=401)
    result = await acc.connect_klaviyo(ctx, ConnectKlaviyoParams(api_key="bad-key"))
    assert result.error is not None
    saved = await ctx.secrets.get("klaviyo_api_key")
    assert saved is None


@pytest.mark.asyncio
async def test_connect_klaviyo_saves_on_success(ctx):
    ctx.http.mock_get(
        "/accounts/",
        {"data": [{"id": "acc_1", "attributes": {
            "contact_information": {"organization_name": "Acme Co"},
            "public_api_key": "pk_123",
        }}]},
        status=200,
    )
    result = await acc.connect_klaviyo(ctx, ConnectKlaviyoParams(api_key="good-key"))
    assert result.error is None
    saved = await ctx.secrets.get("klaviyo_api_key")
    assert saved == "good-key"


@pytest.mark.asyncio
async def test_get_klaviyo_connection_reports_disconnected(ctx):
    result = await acc.get_klaviyo_connection(ctx, NoParams())
    assert result.error is None
    assert result.data.connected is False


@pytest.mark.asyncio
async def test_get_klaviyo_connection_reports_connected(ctx_connected):
    result = await acc.get_klaviyo_connection(ctx_connected, NoParams())
    assert result.data.connected is True


@pytest.mark.asyncio
async def test_disconnect_klaviyo_clears_key(ctx_connected):
    result = await acc.disconnect_klaviyo(ctx_connected, NoParams())
    assert result.error is None
    saved = await ctx_connected.secrets.get("klaviyo_api_key")
    assert not saved


@pytest.mark.asyncio
async def test_get_klaviyo_account_requires_connection(ctx):
    result = await acc.get_klaviyo_account(ctx, NoParams())
    assert result.error is not None


@pytest.mark.asyncio
async def test_get_klaviyo_account_returns_profile(ctx_connected):
    ctx_connected.http.mock_get(
        "/accounts/",
        {"data": [{"id": "acc_1", "attributes": {
            "contact_information": {"organization_name": "Acme Co"},
            "public_api_key": "pk_123",
            "timezone": "America/New_York",
            "test_account": False,
        }}]},
        status=200,
    )
    result = await acc.get_klaviyo_account(ctx_connected, NoParams())
    assert result.error is None
    assert result.data.public_api_key == "pk_123"
