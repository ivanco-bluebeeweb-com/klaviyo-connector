"""Tests for handlers_catalog.py -- Catalog Items/Categories, Coupons, Webhooks."""
from __future__ import annotations

import pytest

import handlers_catalog as hcat
from models import (
    ListCatalogItemsParams, CatalogItemIdParams, CreateCatalogItemParams,
    UpdateCatalogItemParams, ListCatalogCategoriesParams,
    ListCouponsParams, CreateCouponParams, CouponIdParams,
    ListCouponCodesParams, CreateCouponCodeParams,
    ListWebhooksParams, CreateWebhookParams, WebhookIdParams,
    ListWebhookTopicsParams,
)


@pytest.mark.asyncio
async def test_list_catalog_items_requires_connection(ctx):
    with pytest.raises(ValueError):
        await hcat.list_catalog_items(ctx, ListCatalogItemsParams())


# ── catalog items ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_catalog_items_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/catalog-items/",
        {"data": [{"id": "item_1", "attributes": {"title": "Shoes", "price": 49.99}}], "links": {}},
        status=200,
    )
    result = await hcat.list_catalog_items(ctx_connected, ListCatalogItemsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_get_catalog_item_not_found(ctx_connected):
    ctx_connected.http.mock_get("/catalog-items/missing/", {"data": {}}, status=200)
    result = await hcat.get_catalog_item(ctx_connected, CatalogItemIdParams(item_id="missing"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_create_catalog_item_success(ctx_connected):
    ctx_connected.http.mock_post(
        "/catalog-items/",
        {"data": {"id": "item_1", "attributes": {"title": "Shoes", "price": 49.99, "published": True}}},
        status=201,
    )
    result = await hcat.create_catalog_item(
        ctx_connected,
        CreateCatalogItemParams(external_id="sku-1", title="Shoes", price=49.99, published=True),
    )
    assert result.error is None
    assert result.data.title == "Shoes"


@pytest.mark.asyncio
async def test_update_catalog_item_requires_a_field(ctx_connected):
    result = await hcat.update_catalog_item(ctx_connected, UpdateCatalogItemParams(item_id="item_1"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_update_catalog_item_success(ctx_connected):
    ctx_connected.http.mock_patch(
        "/catalog-items/item_1/",
        {"data": {"id": "item_1", "attributes": {"title": "Shoes v2", "price": 59.99}}},
        status=200,
    )
    result = await hcat.update_catalog_item(ctx_connected, UpdateCatalogItemParams(item_id="item_1", title="Shoes v2"))
    assert result.error is None


@pytest.mark.asyncio
async def test_delete_catalog_item_success(ctx_connected):
    ctx_connected.http.mock_delete("/catalog-items/item_1/", {}, status=204)
    result = await hcat.delete_catalog_item(ctx_connected, CatalogItemIdParams(item_id="item_1"))
    assert result.error is None
    assert result.data.deleted is True


@pytest.mark.asyncio
async def test_list_catalog_categories_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/catalog-categories/",
        {"data": [{"id": "cat_1", "attributes": {"name": "Footwear"}}], "links": {}},
        status=200,
    )
    result = await hcat.list_catalog_categories(ctx_connected, ListCatalogCategoriesParams())
    assert result.error is None
    assert len(result.data.items) == 1


# ── coupons ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_coupons_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/coupons/",
        {"data": [{"id": "coup_1", "attributes": {"description": "10% off"}}], "links": {}},
        status=200,
    )
    result = await hcat.list_coupons(ctx_connected, ListCouponsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_create_coupon_success(ctx_connected):
    ctx_connected.http.mock_post(
        "/coupons/",
        {"data": {"id": "coup_1", "attributes": {"description": "10% off", "external_id": "SAVE10"}}},
        status=201,
    )
    result = await hcat.create_coupon(ctx_connected, CreateCouponParams(external_id="SAVE10", description="10% off"))
    assert result.error is None


@pytest.mark.asyncio
async def test_delete_coupon_success(ctx_connected):
    ctx_connected.http.mock_delete("/coupons/coup_1/", {}, status=204)
    result = await hcat.delete_coupon(ctx_connected, CouponIdParams(coupon_id="coup_1"))
    assert result.error is None
    assert result.data.deleted is True


@pytest.mark.asyncio
async def test_list_coupon_codes_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/coupon-codes/",
        {"data": [{"id": "code_1", "attributes": {"unique_code": "SAVE10-ABC", "status": "unused"}}], "links": {}},
        status=200,
    )
    result = await hcat.list_coupon_codes(ctx_connected, ListCouponCodesParams(coupon_id="coup_1"))
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_create_coupon_code_success(ctx_connected):
    ctx_connected.http.mock_post(
        "/coupon-codes/",
        {"data": {"id": "code_1", "attributes": {"unique_code": "SAVE10-ABC", "status": "unused"}}},
        status=201,
    )
    result = await hcat.create_coupon_code(
        ctx_connected, CreateCouponCodeParams(coupon_id="coup_1", unique_code="SAVE10-ABC"),
    )
    assert result.error is None
    assert result.data.unique_code == "SAVE10-ABC"


# ── webhooks ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_webhook_topics_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/webhook-topics/",
        {"data": [{"id": "campaign.sent", "attributes": {"name": "campaign.sent"}}]},
        status=200,
    )
    result = await hcat.list_webhook_topics(ctx_connected, ListWebhookTopicsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_list_webhooks_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/webhooks/",
        {"data": [{"id": "wh_1", "attributes": {"name": "My Hook", "endpoint_url": "https://x.com", "topics": ["campaign.sent"]}}]},
        status=200,
    )
    result = await hcat.list_webhooks(ctx_connected, ListWebhooksParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_create_webhook_success(ctx_connected):
    ctx_connected.http.mock_post(
        "/webhooks/",
        {"data": {"id": "wh_1", "attributes": {"name": "My Hook", "endpoint_url": "https://x.com", "topics": ["campaign.sent"]}}},
        status=201,
    )
    result = await hcat.create_webhook(
        ctx_connected,
        CreateWebhookParams(name="My Hook", endpoint_url="https://x.com", topics=["campaign.sent"]),
    )
    assert result.error is None
    assert result.data.endpoint_url == "https://x.com"


@pytest.mark.asyncio
async def test_delete_webhook_success(ctx_connected):
    ctx_connected.http.mock_delete("/webhooks/wh_1/", {}, status=204)
    result = await hcat.delete_webhook(ctx_connected, WebhookIdParams(webhook_id="wh_1"))
    assert result.error is None
    assert result.data.deleted is True
