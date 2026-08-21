"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), same reasoning as DataForSEO Connector /
n8n Connector. Klaviyo is a paid third-party marketing platform the USER
has their own account and quota/billing with -- not something Imperal can
broker centrally. The user pastes their own Klaviyo private API key once,
Vault-encrypted via `ctx.secrets`, and every call runs against their own
Klaviyo account, their own contacts, their own sending quota.

WHY A SINGLE SECRET (api_key), NOT client_id/client_secret.

Klaviyo offers two auth models (per developers.klaviyo.com/en/docs/
authenticate_requests, checked 2026-08-20): private API key (header
`Authorization: Klaviyo-API-Key <key>`) for server-to-server calls, and
OAuth (Authorization Code + PKCE) for public partner apps installed by
OTHER Klaviyo accounts. This connector targets the first model -- the
user operates their OWN Klaviyo account directly, same shape as every
other BYOK connector in this portfolio (DataForSEO, n8n, Make.com). OAuth
would only make sense if Imperal itself became a listed Klaviyo partner
app installed by third parties -- a different, later product decision,
not what "connect my own Klaviyo account" means today.

WHY THE `revision` HEADER IS HARDCODED IN THE CLIENT, NOT USER-FACING.

Every Klaviyo API call requires an HTTP `revision` header (an ISO date
string, e.g. "2025-10-15") pinning which API version's field/behavior
contract the request uses -- omitting it silently falls back to an
implicit old default per Klaviyo's own versioning policy. This connector
hardcodes one known-good revision in `klaviyo_client.py`
(`KLAVIYO_REVISION`) and bumps it deliberately on a future dev pass, the
same way this portfolio pins `imperal-sdk` versions in requirements.txt
rather than floating to "latest" implicitly.

WHY `write_mode="both"`, SAME REASONING AS DATAFORSEO CONNECTOR.

Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write this -- leaving a first-time user with no
in-app screen explaining what a Klaviyo private API key even is, where to
get one (Klaviyo Account > Settings > API Keys), or whether what they
pasted actually works. `write_mode="both"` keeps the platform Secrets
screen working AND lets this extension's own `connect_klaviyo` validate
the key against Klaviyo's API *before* writing it, so a bad paste is
rejected immediately instead of failing silently on first real use.
"""

from imperal_sdk import Extension, ChatExtension

ext = Extension(
    "klaviyo-connector",
    version="0.1.0",
    display_name="Klaviyo Connector",
    description=(
        "Email/SMS marketing automation via your own Klaviyo account -- "
        "profiles and consent, lists and segments, campaigns (email + SMS), "
        "flows, events and metrics, catalogs, coupons, reviews, templates, "
        "tags, and webhooks. Bring-your-own-account (BYOK): connect your own "
        "Klaviyo private API key, every call runs against your own account "
        "and your own sending quota."
    ),
    icon="icon.svg",
    actions_explicit=True,
    capabilities=["klaviyo:read", "klaviyo:write"],
)

chat = ChatExtension(
    ext,
    tool_name="klaviyo-connector",
    description="Profiles, lists, segments, campaigns, flows, events, catalogs, coupons and webhooks via your own Klaviyo account",
)

ext.secret(
    name="klaviyo_api_key",
    description=(
        "Your Klaviyo private API key, from Klaviyo Account > Settings > "
        "API Keys > Create Private API Key. Needs read/write scopes for the "
        "resources you want this connector to manage (profiles, lists, "
        "campaigns, etc.) -- Klaviyo's own key-scoping screen lets you pick "
        "exactly which ones."
    ),
    write_mode="both",
)


@ext.health_check
async def health_check(ctx) -> bool:
    """Basic liveness check -- confirms the secrets surface is reachable.

    Deliberately does NOT call out to Klaviyo itself: a health check should
    verify OUR OWN plumbing works, not spend the user's Klaviyo rate-limit
    budget on every kernel liveness probe. Whether the saved key is still
    valid is what connect_klaviyo / get_klaviyo_connection are for.
    """
    await ctx.secrets.get("klaviyo_api_key")


@ext.on_install
async def on_install(ctx):
    """Make the first step traceable -- and knowable.

    A Klaviyo private API key cannot be provisioned for the user, so a
    fresh install is inert by design until one is pasted via
    connect_klaviyo. Recording that at install time means "nothing works
    yet" shows up as an expected state in the audit log rather than
    looking like a broken deployment -- same reasoning as Trello
    Connector's on_install.
    """
    await ctx.log(
        "Klaviyo Connector installed -- awaiting a private API key; "
        "call connect_klaviyo to activate."
    )
