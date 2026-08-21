# Klaviyo Connector

Email/SMS marketing automation over the [Klaviyo](https://www.klaviyo.com/)
API: profiles and consent, lists and segments, campaigns (email + SMS),
flows, behavioral events and metrics, catalogs, coupons, templates, tags,
and webhooks. Bring-your-own-account (BYOK): you connect your own Klaviyo
private API key, same pattern as DataForSEO Connector's login+password and
n8n Connector's API key -- every call runs against your own Klaviyo
account, your own contacts, your own sending quota.

## Connecting

1. Get a private API key from Klaviyo: **Account > Settings > API Keys >
   Create Private API Key**. Scope it for the resources you want this
   connector to manage (profiles, lists, campaigns, etc.) -- Klaviyo's own
   key-scoping screen lets you pick exactly which ones.
2. Paste it into the right-hand panel's "Connect Klaviyo" form, or call
   `connect_klaviyo` from chat. The key is **verified against Klaviyo
   before being saved** (a cheap `GET /accounts/` call) -- a bad paste is
   rejected immediately instead of failing silently on first real use.
3. `disconnect_klaviyo` deletes the stored key. Nothing in Klaviyo itself
   changes.

## Why `Authorization: Klaviyo-API-Key <key>`, not Bearer/OAuth

Klaviyo's own docs (`developers.klaviyo.com/en/docs/authenticate_requests`)
document this as a deliberately non-standard scheme for private API keys,
distinct from the separate OAuth flow meant for public partner apps
installed by *other* Klaviyo accounts. This connector targets the private
API key model -- the user operates their own account directly, same shape
as every other BYOK connector in this portfolio. OAuth would only make
sense if Imperal became a listed Klaviyo partner app, a different, later
product decision.

## Why the `revision` header is hardcoded, not user-facing

Every Klaviyo API call requires an HTTP `revision` header (an ISO date,
e.g. `2025-10-15`) pinning which API version's field/behavior contract is
in effect. Omitting it does not error -- it silently falls back to an old
implicit default, a worse failure mode than a pinned, deliberately-bumped
constant. `klaviyo_client.KLAVIYO_REVISION` is that pin; bumping it is a
deliberate developer action, same discipline as pinning `imperal-sdk` in
`requirements.txt`.

## Why `ctx.http`, not a hand-rolled HTTP client

`klaviyo_client.request()` calls through `ctx.http` -- the platform's own
egress client, swappable for `imperal_sdk.testing.MockContext`'s mock HTTP
surface in tests (no real network in the whole suite). Same reasoning
DataForSEO Connector's `dfs_client.py` documents for its own request path.

## Rate limits

Klaviyo enforces a fixed-window model with **two simultaneous windows**
(burst: 1s, steady: 60s) and per-endpoint weight tiers (XS/S/M/L/XL) -- see
`developers.klaviyo.com/en/docs/rate_limits_and_error_handling`. A 429
means either window tripped; the response carries a `Retry-After` header.
`klaviyo_client.request()` centralizes one retry-on-429 loop (single
retry, honors `Retry-After`, capped) so every handler gets correct
behavior for free instead of reinventing it inconsistently.

## Domain coverage (50 functions)

- **Accounts** -- `connect_klaviyo`, `disconnect_klaviyo`,
  `get_klaviyo_connection`, `get_klaviyo_account`.
- **Profiles** -- create/update/get/list/delete a contact record.
- **Lists** -- static opt-in groups: create/list/get/delete, add/remove
  profiles, list members.
- **Segments** -- Klaviyo-computed dynamic groups: list/get/list members
  (read-only from the API side -- membership is driven by conditions
  defined in Klaviyo's own UI, not by direct add/remove calls).
- **Events & Metrics** -- `create_event` tracks a behavioral event
  (auto-creates the profile and the metric if new); `list_events`,
  `list_metrics`.
- **Campaigns** -- one-off email/SMS sends: list/get/create/send.
- **Flows** -- automated multi-step sequences: list/get/set_flow_status
  (Klaviyo builds flow *logic* only in its own visual editor; this
  connector manages flow lifecycle, not flow authoring).
- **Templates** -- reusable HTML email bodies: list/get/create.
- **Tags** -- organizing labels: list/create/attach to a
  campaign/flow/list/segment (`tag_resource`).
- **Catalogs** -- product data Klaviyo renders into dynamic email/SMS
  blocks: list/get/create/update/delete items, list categories.
- **Coupons** -- discount codes issued through flows/campaigns:
  list/create/delete coupons, list/create coupon codes.
- **Webhooks** -- outbound HTTP notifications on Klaviyo-side events:
  list topics, list/create/delete webhooks.

## Panel

- **right (`klaviyo_overview`)** -- connect card (BYOK form, verified
  before saving) plus a quick account overview (profile/list/segment/
  campaign/flow counts) once connected, and shortcut buttons for the most
  common list actions. No per-project concept here (unlike DataForSEO
  Connector) -- one connected account, one flat API surface.

## Known limitation: icon is a placeholder, not the official Klaviyo logo

Klaviyo's official brand mark is gated behind their Partner/Press portal
(not freely redistributable), so `icon.svg` here is a simplified
geometric monogram placeholder -- the same portfolio precedent as UiPath,
Automation Anywhere, Blue Prism, and MuleSoft Connector's icons, all of
which face the same partner-portal gating on their real logos. **This
must be swapped for a properly licensed asset before public marketplace
listing if brand accuracy matters to the user.**

## Testing

`tests/` covers all 5 domains against `imperal_sdk.testing.MockContext`
(63 tests, 0 real network calls). `tests/conftest.py` extends the SDK's
`MockHTTP` with `mock_patch`/`mock_delete`/`mock_put` registrars (the SDK
ships only `mock_get`/`mock_post` today; its own dispatch already handles
the other verbs, there was just no public registrar for them) -- needed
because Klaviyo's API leans heavily on PATCH (`update_profile`,
`set_flow_status`, `update_catalog_item`) and DELETE (`delete_list`,
`delete_coupon`, `delete_webhook`, `remove_profiles_from_list`).
