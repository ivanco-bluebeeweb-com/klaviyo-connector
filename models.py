"""Pydantic params models + SDL entity contracts for Klaviyo Connector.

All params models are module-scope (V17 federal invariant). Entities/
EntityLists follow the read-tool contract: a single record is an
sdl.Entity subclass, a list result is sdl.EntityList[T] -- never a bare
dict, same convention as every other connector in this portfolio.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection / account management.
# ──────────────────────────────────────────────────────────────────────────


class ConnectKlaviyoParams(BaseModel):
    api_key: str = Field(..., description="Klaviyo private API key (Settings > API Keys in your Klaviyo account). Verified against Klaviyo before being saved.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""


class KlaviyoAccount(sdl.Entity):
    id: str = ""
    title: str = ""
    contact_email: str = ""
    timezone: str = ""
    public_api_key: str = ""
    test_account: bool = False


# ──────────────────────────────────────────────────────────────────────────
# Profiles.
# ──────────────────────────────────────────────────────────────────────────


class CreateProfileParams(BaseModel):
    email: str = Field("", description="Profile email address (at least one of email/phone_number/external_id is required)")
    phone_number: str = Field("", description="Profile phone number in E.164 format, e.g. +15005550006")
    external_id: str = Field("", description="Your own external identifier for this person, if you have one")
    first_name: str = Field("", description="First name")
    last_name: str = Field("", description="Last name")
    organization: str = Field("", description="Company/organization name")
    title: str = Field("", description="Job title")
    location_city: str = Field("", description="City")
    location_country: str = Field("", description="Country")
    properties: dict = Field(default_factory=dict, description="Arbitrary custom profile properties as key/value pairs")


class UpdateProfileParams(BaseModel):
    profile_id: str = Field(..., description="Klaviyo profile id, from list_profiles/get_profile")
    email: str = Field("", description="New email, if changing")
    phone_number: str = Field("", description="New phone number, if changing")
    first_name: str = Field("", description="New first name, if changing")
    last_name: str = Field("", description="New last name, if changing")
    organization: str = Field("", description="New organization, if changing")
    title: str = Field("", description="New job title, if changing")
    properties: dict = Field(default_factory=dict, description="Custom properties to merge into the profile")


class GetProfileParams(BaseModel):
    profile_id: str = Field(..., description="Klaviyo profile id")


class ListProfilesParams(BaseModel):
    email: str = Field("", description="Filter to an exact email address")
    phone_number: str = Field("", description="Filter to an exact phone number")
    cursor: str = Field("", description="Pagination cursor from a previous call's next_cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100, description="Results per page, 1-100")


class DeleteProfileParams(BaseModel):
    profile_id: str = Field(..., description="Klaviyo profile id -- this creates a permanent data-privacy deletion request, cannot be undone")


class Profile(sdl.Entity):
    id: str = ""
    title: str = ""
    email: str = ""
    phone_number: str = ""
    external_id: str = ""
    first_name: str = ""
    last_name: str = ""
    organization: str = ""
    location_city: str = ""
    location_country: str = ""
    created: str = ""
    updated: str = ""
    properties: dict = Field(default_factory=dict)


class ProfileList(sdl.EntityList[Profile]):
    next_cursor: str = ""


class BulkProfileIdsParams(BaseModel):
    list_id: str = Field(..., description="Klaviyo list id")
    profile_ids: list[str] = Field(..., description="Klaviyo profile ids to add/remove, 1-100 per call")


# ──────────────────────────────────────────────────────────────────────────
# Lists.
# ──────────────────────────────────────────────────────────────────────────


class CreateListParams(BaseModel):
    name: str = Field(..., description="List display name")


class UpdateListParams(BaseModel):
    list_id: str = Field(..., description="Klaviyo list id")
    name: str = Field(..., description="New list name")


class ListIdParams(BaseModel):
    list_id: str = Field(..., description="Klaviyo list id")


class ListListsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")


class KlaviyoList(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    created: str = ""
    updated: str = ""
    profile_count: int = 0


class KlaviyoListList(sdl.EntityList[KlaviyoList]):
    next_cursor: str = ""


class ListMembersParams(BaseModel):
    list_id: str = Field(..., description="Klaviyo list id")
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class ListMembershipResult(sdl.Entity):
    id: str = ""
    title: str = ""
    profile_count: int = 0


# ──────────────────────────────────────────────────────────────────────────
# Segments.
# ──────────────────────────────────────────────────────────────────────────


class ListSegmentsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")


class SegmentIdParams(BaseModel):
    segment_id: str = Field(..., description="Klaviyo segment id")


class ListSegmentMembersParams(BaseModel):
    segment_id: str = Field(..., description="Klaviyo segment id")
    cursor: str = Field("", description="Pagination cursor, empty for first page")


class CreateSegmentParams(BaseModel):
    name: str = Field(..., description="Segment display name")
    condition_field: str = Field(..., description="Profile field the condition checks, e.g. 'email' or a custom property name")
    condition_operator: str = Field("equals", description="Condition operator: equals, not-equals, contains, greater-than, less-than")
    condition_value: str = Field(..., description="Value to compare against")


class Segment(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    created: str = ""
    updated: str = ""
    is_active: bool = True
    is_processing: bool = False
    profile_count: int = 0


class SegmentList(sdl.EntityList[Segment]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Subscriptions (bulk profile subscribe/unsubscribe -- consent management).
# ──────────────────────────────────────────────────────────────────────────


class SubscribeProfilesParams(BaseModel):
    list_id: str = Field(..., description="Klaviyo list id to subscribe these profiles to")
    emails: list[str] = Field(default_factory=list, description="Email addresses to subscribe to email marketing on this list")
    phone_numbers: list[str] = Field(default_factory=list, description="Phone numbers (E.164) to subscribe to SMS marketing on this list")


class UnsubscribeProfilesParams(BaseModel):
    list_id: str = Field("", description="Klaviyo list id to unsubscribe from (omit to unsubscribe globally)")
    emails: list[str] = Field(default_factory=list, description="Email addresses to unsubscribe")
    phone_numbers: list[str] = Field(default_factory=list, description="Phone numbers to unsubscribe")


class SubscriptionResult(sdl.Entity):
    id: str = ""
    title: str = ""
    accepted_count: int = 0


# ──────────────────────────────────────────────────────────────────────────
# Events / Metrics.
# ──────────────────────────────────────────────────────────────────────────


class CreateEventParams(BaseModel):
    metric_name: str = Field(..., description="Event/metric name, e.g. 'Viewed Product', 'Placed Order'")
    email: str = Field("", description="Profile email this event belongs to (email or phone_number or external_id required)")
    phone_number: str = Field("", description="Profile phone number this event belongs to")
    external_id: str = Field("", description="Your own external id for the profile this event belongs to")
    value: float = Field(0.0, description="Numeric value of the event, e.g. order total")
    properties: dict = Field(default_factory=dict, description="Arbitrary event properties as key/value pairs")
    unique_id: str = Field("", description="Your own idempotency key for this event, to avoid duplicates on retry")


class ListEventsParams(BaseModel):
    metric_id: str = Field("", description="Filter to events of one metric id, from list_metrics")
    profile_id: str = Field("", description="Filter to events belonging to one profile id")
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class KlaviyoEvent(sdl.Entity):
    id: str = ""
    title: str = ""
    metric_id: str = ""
    profile_id: str = ""
    value: float = 0.0
    datetime: str = ""


class KlaviyoEventList(sdl.EntityList[KlaviyoEvent]):
    next_cursor: str = ""


class ListMetricsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")


class Metric(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    integration_name: str = ""
    created: str = ""


class MetricList(sdl.EntityList[Metric]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Campaigns (Email + SMS).
# ──────────────────────────────────────────────────────────────────────────


class ListCampaignsParams(BaseModel):
    channel: str = Field("email", description="Campaign channel: email or sms")
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class CampaignIdParams(BaseModel):
    campaign_id: str = Field(..., description="Klaviyo campaign id")


class CreateCampaignParams(BaseModel):
    name: str = Field(..., description="Internal campaign name")
    channel: str = Field("email", description="Campaign channel: email or sms")
    list_ids: list[str] = Field(..., description="Klaviyo list ids to send to")
    segment_ids: list[str] = Field(default_factory=list, description="Klaviyo segment ids to also target")
    subject: str = Field("", description="Email subject line (email channel only)")
    from_email: str = Field("", description="Sending email address (email channel only, must be a verified sending domain)")
    from_label: str = Field("", description="Sender display name (email channel only)")


class SendCampaignParams(BaseModel):
    campaign_id: str = Field(..., description="Klaviyo campaign id to send immediately")


class Campaign(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    status: str = ""
    channel: str = ""
    created: str = ""
    updated: str = ""
    send_time: str = ""


class CampaignList(sdl.EntityList[Campaign]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Flows.
# ──────────────────────────────────────────────────────────────────────────


class ListFlowsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class FlowIdParams(BaseModel):
    flow_id: str = Field(..., description="Klaviyo flow id")


class SetFlowStatusParams(BaseModel):
    flow_id: str = Field(..., description="Klaviyo flow id")
    status: str = Field(..., description="New status: live, draft, or manual")


class Flow(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    status: str = ""
    trigger_type: str = ""
    created: str = ""
    updated: str = ""


class FlowList(sdl.EntityList[Flow]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Templates.
# ──────────────────────────────────────────────────────────────────────────


class ListTemplatesParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class TemplateIdParams(BaseModel):
    template_id: str = Field(..., description="Klaviyo template id")


class CreateTemplateParams(BaseModel):
    name: str = Field(..., description="Template name")
    html: str = Field(..., description="Full HTML content of the email template")


class Template(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    created: str = ""
    updated: str = ""


class TemplateList(sdl.EntityList[Template]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Tags.
# ──────────────────────────────────────────────────────────────────────────


class ListTagsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")


class CreateTagParams(BaseModel):
    name: str = Field(..., description="Tag name")


class TagResourceParams(BaseModel):
    tag_id: str = Field(..., description="Klaviyo tag id")
    resource_type: str = Field(..., description="Resource type to tag: campaign, flow, list, or segment")
    resource_id: str = Field(..., description="Id of the campaign/flow/list/segment to tag")


class Tag(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""


class TagList(sdl.EntityList[Tag]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Catalogs (ecommerce product feed).
# ──────────────────────────────────────────────────────────────────────────


class ListCatalogItemsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class CreateCatalogItemParams(BaseModel):
    external_id: str = Field(..., description="Your own product id in your source system (SKU or similar)")
    title: str = Field(..., description="Product title")
    description: str = Field("", description="Product description")
    url: str = Field("", description="Public product page URL")
    image_full_url: str = Field("", description="Full-size product image URL")
    price: float = Field(0.0, description="Product price")
    published: bool = Field(True, description="Whether the item is published/visible")
    catalog_type: str = Field("$default", description="Klaviyo catalog integration type, '$default' unless using a custom feed")


class UpdateCatalogItemParams(BaseModel):
    item_id: str = Field(..., description="Klaviyo catalog item id (composite id like '$custom:::<external_id>')")
    title: str = Field("", description="New product title, empty to leave unchanged")
    price: float | None = Field(None, description="New price, None to leave unchanged")
    url: str = Field("", description="New public product page URL, empty to leave unchanged")
    image_full_url: str = Field("", description="New full-size product image URL, empty to leave unchanged")
    published: bool | None = Field(None, description="New published state, None to leave unchanged")


class CatalogItemIdParams(BaseModel):
    item_id: str = Field(..., description="Klaviyo catalog item id (composite id like '$default:::<external_id>')")


class CatalogItem(sdl.Entity):
    id: str = ""
    title: str = ""
    external_id: str = ""
    integration_type: str = ""
    catalog_type: str = ""
    url: str = ""
    image_full_url: str = ""
    price: float = 0.0
    published: bool = True


class CatalogItemList(sdl.EntityList[CatalogItem]):
    next_cursor: str = ""


class ListCatalogCategoriesParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class CatalogCategory(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    external_id: str = ""


class CatalogCategoryList(sdl.EntityList[CatalogCategory]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Coupons.
# ──────────────────────────────────────────────────────────────────────────


class CreateCouponParams(BaseModel):
    external_id: str = Field(..., description="Your own coupon identifier")
    description: str = Field("", description="Internal description")


class CouponIdParams(BaseModel):
    coupon_id: str = Field(..., description="Klaviyo coupon id")


class CreateCouponCodeParams(BaseModel):
    coupon_id: str = Field(..., description="Klaviyo coupon id from create_coupon")
    unique_code: str = Field(..., description="The actual redeemable code, e.g. 'SAVE20-AB12CD'")
    expires_at: str = Field("", description="ISO 8601 expiry datetime, empty for no expiry")


class ListCouponsParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class ListCouponCodesParams(BaseModel):
    coupon_id: str = Field(..., description="Klaviyo coupon id to list issued codes for")
    cursor: str = Field("", description="Pagination cursor, empty for first page")
    page_size: int = Field(20, ge=1, le=100)


class Coupon(sdl.Entity):
    id: str = ""
    title: str = ""
    external_id: str = ""
    description: str = ""


class CouponList(sdl.EntityList[Coupon]):
    next_cursor: str = ""


class CouponCode(sdl.Entity):
    id: str = ""
    title: str = ""
    unique_code: str = ""
    status: str = ""
    expires_at: str = ""


class CouponCodeList(sdl.EntityList[CouponCode]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Images.
# ──────────────────────────────────────────────────────────────────────────


class ListImagesParams(BaseModel):
    cursor: str = Field("", description="Pagination cursor, empty for first page")


class UploadImageFromUrlParams(BaseModel):
    image_url: str = Field(..., description="Publicly reachable https:// URL of the image to import into Klaviyo's image library")
    name: str = Field("", description="Display name for the image, defaults to the filename")


class KlaviyoImage(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    image_url: str = ""
    format: str = ""


class KlaviyoImageList(sdl.EntityList[KlaviyoImage]):
    next_cursor: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Webhooks.
# ──────────────────────────────────────────────────────────────────────────


class ListWebhookTopicsParams(BaseModel):
    pass


class WebhookTopic(sdl.Entity):
    id: str = ""
    title: str = ""


class WebhookTopicList(sdl.EntityList[WebhookTopic]):
    pass


class ListWebhooksParams(BaseModel):
    pass


class CreateWebhookParams(BaseModel):
    name: str = Field(..., description="Webhook display name")
    endpoint_url: str = Field(..., description="Your https:// URL Klaviyo will POST events to")
    topics: list[str] = Field(..., description="Event topics to subscribe to, e.g. ['profile.created','order.placed']")


class WebhookIdParams(BaseModel):
    webhook_id: str = Field(..., description="Klaviyo webhook id")


class Webhook(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    endpoint_url: str = ""
    topics: list[str] = Field(default_factory=list)


class WebhookList(sdl.EntityList[Webhook]):
    pass


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    deleted: bool = True
