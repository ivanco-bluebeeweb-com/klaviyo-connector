"""Catalogs (product data Klaviyo can render into dynamic email/SMS
blocks -- product images, prices, links), Coupons (discount codes issued
through flows/campaigns), and Webhooks (outbound HTTP notifications when
Klaviyo-side events happen, e.g. a campaign finishes sending). Rounds out
full API surface coverage per the Discovery pass (2026-08-20).
"""
from __future__ import annotations

import klaviyo_client as kc
from imperal_sdk import ActionResult, sdl

from app import ext, chat
from accounts import _get_key
from models import (
    ListCatalogItemsParams, CatalogItemIdParams, CreateCatalogItemParams,
    UpdateCatalogItemParams, CatalogItem, CatalogItemList,
    ListCatalogCategoriesParams, CatalogCategory, CatalogCategoryList,
    ListCouponsParams, CreateCouponParams, CouponIdParams,
    Coupon, CouponList,
    ListCouponCodesParams, CreateCouponCodeParams, CouponCode, CouponCodeList,
    ListWebhooksParams, CreateWebhookParams, WebhookIdParams,
    Webhook, WebhookList, ListWebhookTopicsParams, WebhookTopic, WebhookTopicList,
    DeleteResult,
)


async def _need_key(ctx):
    key = await _get_key(ctx)
    if not key:
        raise ValueError("Klaviyo is not connected yet. Call connect_klaviyo first.")
    return key


# ──────────────────────────────────────────────────────────────────────────
# Catalogs.
# ──────────────────────────────────────────────────────────────────────────


def _catalog_item_from_row(row: dict) -> CatalogItem:
    a = row.get("attributes") or {}
    return CatalogItem(
        id=row.get("id", ""),
        title=a.get("title", "") or row.get("id", ""),
        external_id=a.get("external_id", "") or "",
        integration_type=a.get("integration_type", "") or "$custom",
        catalog_type=a.get("catalog_type", "") or "$default",
        price=float(a.get("price") or 0),
        url=a.get("url", "") or "",
        image_full_url=a.get("image_full_url", "") or "",
        published=bool(a.get("published", False)),
    )


@chat.function(name="list_catalog_items", data_model=CatalogItemList, description="List items in Klaviyo's product catalog -- products that can be rendered into dynamic email/SMS blocks (recommendations, browse abandonment, etc).")
async def list_catalog_items(ctx, params: ListCatalogItemsParams) -> ActionResult:
    """List catalog items (products) with cursor pagination."""
    key = await _need_key(ctx)
    q: dict = {"page[size]": params.page_size}
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/catalog-items/", params=q)
    rows = payload.get("data") or []
    items = [_catalog_item_from_row(r) for r in rows]
    next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(
        CatalogItemList(items=items, next_cursor=next_cursor),
        summary=f"{len(items)} catalog item(s).",
    )


@chat.function(name="get_catalog_item", data_model=CatalogItem, description="Read one Klaviyo catalog item in full.")
async def get_catalog_item(ctx, params: CatalogItemIdParams) -> ActionResult:
    """Read one catalog item's details by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/catalog-items/{params.item_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error("Catalog item not found.")
    return ActionResult.success(_catalog_item_from_row(row), summary="Catalog item loaded.")


@chat.function(name="create_catalog_item", data_model=CatalogItem, description="Create a product in Klaviyo's catalog so it can be used in dynamic email/SMS blocks and recommendations.")
async def create_catalog_item(ctx, params: CreateCatalogItemParams) -> ActionResult:
    """Create a new catalog item (product) for use in dynamic email/SMS blocks."""
    key = await _need_key(ctx)
    attrs: dict = {
        "external_id": params.external_id,
        "title": params.title,
        "integration_type": "$custom",
        "catalog_type": "$default",
        "price": params.price,
        "published": params.published,
    }
    if params.url:
        attrs["url"] = params.url
    if params.image_full_url:
        attrs["image_full_url"] = params.image_full_url
    if params.description:
        attrs["description"] = params.description
    body = {"data": {"type": "catalog-item", "attributes": attrs}}
    payload = await kc.request(ctx, key, "POST", "/catalog-items/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_catalog_item_from_row(row), summary=f"Catalog item '{params.title}' created.")


@chat.function(name="update_catalog_item", data_model=CatalogItem, description="Update selected fields of an existing Klaviyo catalog item (price, title, published state, etc).")
async def update_catalog_item(ctx, params: UpdateCatalogItemParams) -> ActionResult:
    """Update selected fields on an existing catalog item."""
    key = await _need_key(ctx)
    attrs: dict = {}
    if params.title:
        attrs["title"] = params.title
    if params.price is not None:
        attrs["price"] = params.price
    if params.url:
        attrs["url"] = params.url
    if params.image_full_url:
        attrs["image_full_url"] = params.image_full_url
    if params.published is not None:
        attrs["published"] = params.published
    if not attrs:
        return ActionResult.error("Provide at least one field to update.")
    body = {"data": {"type": "catalog-item", "id": params.item_id, "attributes": attrs}}
    payload = await kc.request(ctx, key, "PATCH", f"/catalog-items/{params.item_id}/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_catalog_item_from_row(row), summary="Catalog item updated.")


@chat.function(name="delete_catalog_item", data_model=DeleteResult, description="Permanently delete a product from Klaviyo's catalog.")
async def delete_catalog_item(ctx, params: CatalogItemIdParams) -> ActionResult:
    """Permanently delete a catalog item."""
    key = await _need_key(ctx)
    await kc.request(ctx, key, "DELETE", f"/catalog-items/{params.item_id}/")
    return ActionResult.success(DeleteResult(id=params.item_id, deleted=True), summary="Catalog item deleted.")


@chat.function(name="list_catalog_categories", data_model=CatalogCategoryList, description="List categories in Klaviyo's product catalog.")
async def list_catalog_categories(ctx, params: ListCatalogCategoriesParams) -> ActionResult:
    """List catalog categories with cursor pagination."""
    key = await _need_key(ctx)
    q: dict = {"page[size]": params.page_size}
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/catalog-categories/", params=q)
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(CatalogCategory(id=r.get("id", ""), title=a.get("name", "") or r.get("id", ""), external_id=a.get("external_id", "") or ""))
    return ActionResult.success(
        CatalogCategoryList(items=items, next_cursor=kc.next_cursor_from_links(payload)),
        summary=f"{len(items)} catalog categor{'y' if len(items) == 1 else 'ies'}.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Coupons.
# ──────────────────────────────────────────────────────────────────────────


@chat.function(name="list_coupons", data_model=CouponList, description="List discount coupons (the reusable discount definition, not individual codes) configured in Klaviyo.")
async def list_coupons(ctx, params: ListCouponsParams) -> ActionResult:
    """List coupons (discount code definitions) with cursor pagination."""
    key = await _need_key(ctx)
    q: dict = {"page[size]": params.page_size}
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/coupons/", params=q)
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(Coupon(id=r.get("id", ""), title=a.get("description", "") or r.get("id", ""), external_id=a.get("external_id", "") or "", description=a.get("description", "") or ""))
    return ActionResult.success(
        CouponList(items=items, next_cursor=kc.next_cursor_from_links(payload)),
        summary=f"{len(items)} coupon(s).",
    )


@chat.function(name="create_coupon", data_model=Coupon, description="Create a discount coupon definition in Klaviyo (the template a coupon code is issued under).")
async def create_coupon(ctx, params: CreateCouponParams) -> ActionResult:
    """Create a new coupon (discount definition)."""
    key = await _need_key(ctx)
    attrs = {"external_id": params.external_id, "description": params.description}
    body = {"data": {"type": "coupon", "attributes": attrs}}
    payload = await kc.request(ctx, key, "POST", "/coupons/", json_body=body)
    row = payload.get("data") or {}
    a = row.get("attributes") or {}
    return ActionResult.success(
        Coupon(id=row.get("id", ""), title=a.get("description", "") or row.get("id", ""), external_id=a.get("external_id", "") or "", description=a.get("description", "") or ""),
        summary=f"Coupon '{params.description}' created.",
    )


@chat.function(name="delete_coupon", data_model=DeleteResult, description="Permanently delete a coupon definition from Klaviyo.")
async def delete_coupon(ctx, params: CouponIdParams) -> ActionResult:
    """Permanently delete a coupon definition and its issued codes."""
    key = await _need_key(ctx)
    await kc.request(ctx, key, "DELETE", f"/coupons/{params.coupon_id}/")
    return ActionResult.success(DeleteResult(id=params.coupon_id, deleted=True), summary="Coupon deleted.")


@chat.function(name="list_coupon_codes", data_model=CouponCodeList, description="List individual redeemable codes issued under a Klaviyo coupon.")
async def list_coupon_codes(ctx, params: ListCouponCodesParams) -> ActionResult:
    """List individual redeemable codes issued under a coupon."""
    key = await _need_key(ctx)
    q: dict = {"filter": f'equals(coupon.id,"{params.coupon_id}")', "page[size]": params.page_size}
    if params.cursor:
        q["page[cursor]"] = params.cursor
    payload = await kc.request(ctx, key, "GET", "/coupon-codes/", params=q)
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(CouponCode(id=r.get("id", ""), title=a.get("unique_code", "") or r.get("id", ""), unique_code=a.get("unique_code", "") or "", status=a.get("status", "") or "", expires_at=a.get("expires_at", "") or ""))
    return ActionResult.success(
        CouponCodeList(items=items, next_cursor=kc.next_cursor_from_links(payload)),
        summary=f"{len(items)} coupon code(s).",
    )


@chat.function(name="create_coupon_code", data_model=CouponCode, description="Issue a new redeemable code under an existing Klaviyo coupon, optionally with an expiry date.")
async def create_coupon_code(ctx, params: CreateCouponCodeParams) -> ActionResult:
    """Create a new redeemable code under an existing coupon."""
    key = await _need_key(ctx)
    attrs: dict = {"unique_code": params.unique_code}
    if params.expires_at:
        attrs["expires_at"] = params.expires_at
    body = {
        "data": {
            "type": "coupon-code",
            "attributes": attrs,
            "relationships": {"coupon": {"data": {"type": "coupon", "id": params.coupon_id}}},
        }
    }
    payload = await kc.request(ctx, key, "POST", "/coupon-codes/", json_body=body)
    row = payload.get("data") or {}
    a = row.get("attributes") or {}
    return ActionResult.success(
        CouponCode(id=row.get("id", ""), title=a.get("unique_code", "") or row.get("id", ""), unique_code=a.get("unique_code", "") or "", status=a.get("status", "") or "", expires_at=a.get("expires_at", "") or ""),
        summary=f"Coupon code '{params.unique_code}' issued.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Webhooks.
# ──────────────────────────────────────────────────────────────────────────


@chat.function(name="list_webhook_topics", data_model=WebhookTopicList, description="List the event topics Klaviyo can notify a webhook about (e.g. campaign.sent, profile.created).")
async def list_webhook_topics(ctx, params: ListWebhookTopicsParams) -> ActionResult:
    """List the event topics available to subscribe a webhook to."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", "/webhook-topics/")
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(WebhookTopic(id=r.get("id", ""), title=a.get("name", "") or r.get("id", "")))
    return ActionResult.success(WebhookTopicList(items=items), summary=f"{len(items)} webhook topic(s).")


@chat.function(name="list_webhooks", data_model=WebhookList, description="List webhook subscriptions configured on this Klaviyo account.")
async def list_webhooks(ctx, params: ListWebhooksParams) -> ActionResult:
    """List configured outbound webhooks with cursor pagination."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", "/webhooks/")
    rows = payload.get("data") or []
    items = []
    for r in rows:
        a = r.get("attributes") or {}
        items.append(Webhook(id=r.get("id", ""), title=a.get("name", "") or r.get("id", ""), endpoint_url=a.get("endpoint_url", "") or "", topics=a.get("topics", []) or []))
    return ActionResult.success(WebhookList(items=items), summary=f"{len(items)} webhook(s).")


@chat.function(name="create_webhook", data_model=Webhook, description="Create a webhook subscription: Klaviyo will POST to your endpoint_url when any of the given topics occur.")
async def create_webhook(ctx, params: CreateWebhookParams) -> ActionResult:
    """Create a new outbound webhook subscription."""
    key = await _need_key(ctx)
    attrs = {"name": params.name, "endpoint_url": params.endpoint_url, "topics": params.topics}
    body = {"data": {"type": "webhook", "attributes": attrs}}
    payload = await kc.request(ctx, key, "POST", "/webhooks/", json_body=body)
    row = payload.get("data") or {}
    a = row.get("attributes") or {}
    return ActionResult.success(
        Webhook(id=row.get("id", ""), title=a.get("name", "") or row.get("id", ""), endpoint_url=a.get("endpoint_url", "") or "", topics=a.get("topics", []) or []),
        summary=f"Webhook '{params.name}' created.",
    )


@chat.function(name="delete_webhook", data_model=DeleteResult, description="Permanently remove a Klaviyo webhook subscription.")
async def delete_webhook(ctx, params: WebhookIdParams) -> ActionResult:
    """Permanently delete a webhook subscription."""
    key = await _need_key(ctx)
    await kc.request(ctx, key, "DELETE", f"/webhooks/{params.webhook_id}/")
    return ActionResult.success(DeleteResult(id=params.webhook_id, deleted=True), summary="Webhook deleted.")
