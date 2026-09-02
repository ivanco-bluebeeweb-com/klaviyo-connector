"""Klaviyo API client -- auth, revision pinning, JSON:API filter/pagination
helpers, and a thin request wrapper shared by every handler module.

WHY ONE HARDCODED REVISION CONSTANT.

Per developers.klaviyo.com/en/docs/api_versioning_and_deprecation_policy
(checked 2026-08-20), every request must carry a `revision` header (an ISO
date, e.g. "2025-10-15") pinning the field/behavior contract in effect.
Omitting it does not error -- it silently falls back to an old implicit
default, which is worse (a silent behavior change on Klaviyo's schedule,
not ours). Pinning one known revision here means this connector's behavior
only changes when a developer deliberately bumps KLAVIYO_REVISION, same
discipline as pinning `imperal-sdk` in requirements.txt.

WHY `Authorization: Klaviyo-API-Key <key>`, NOT Bearer.

Klaviyo's own docs are explicit this is a non-standard scheme (most SaaS
in this portfolio use Bearer or Basic) -- built here rather than assumed,
same reasoning n8n Connector documents for its `X-N8N-API-KEY` header.

WHY RATE-LIMIT HANDLING LIVES HERE, NOT IN EACH HANDLER.

Klaviyo uses a fixed-window model with TWO simultaneous windows (burst:
1s, steady: 60s) and per-endpoint weight tiers (XS/S/M/L/XL) -- see
developers.klaviyo.com/en/docs/rate_limits_and_error_handling. A 429 means
either window tripped; the response carries a `Retry-After` header telling
us exactly how long to back off. Centralizing one retry-on-429 loop here
(single retry, honoring Retry-After, capped) means every handler gets
correct behavior for free instead of each one reinventing it inconsistently.

WHY JSON:API FILTER-STRING BUILDING IS A HELPER, NOT STRING CONCATENATION
IN EACH HANDLER.

Klaviyo's filter syntax is `?filter=equals(field,"value")`,
`greater-or-equal(field,value)`, comma-chained as an implicit `and(...)`
(per developers.klaviyo.com/en/docs/filtering). Building this by hand in
every handler invites quoting bugs (unescaped user-supplied strings
breaking the filter grammar). `build_filter()` centralizes correct
quoting/escaping once.
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable

BASE_URL = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2025-10-15"  # bump deliberately; see module docstring.

_MAX_RETRIES_ON_429 = 1
_DEFAULT_RETRY_AFTER = 2.0


class KlaviyoError(Exception):
    """Raised for any non-2xx Klaviyo response, with parsed detail."""

    def __init__(self, status_code: int, detail: str, raw: Any = None):
        self.status_code = status_code
        self.detail = detail
        self.raw = raw
        super().__init__(f"Klaviyo API error {status_code}: {detail}")


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": KLAVIYO_REVISION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _extract_error_detail(payload: Any) -> str:
    """Klaviyo error bodies are JSON:API shape: {"errors": [{"detail": ...}]}."""
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            parts = []
            for err in errors:
                if isinstance(err, dict):
                    parts.append(str(err.get("detail") or err.get("title") or err))
                else:
                    parts.append(str(err))
            return "; ".join(parts)
    return str(payload)


async def request(
    ctx,
    api_key: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    """Single Klaviyo API call with revision header, auth, and one
    respectful retry on 429 honoring Retry-After. Raises KlaviyoError on
    any non-2xx after that retry. Returns parsed JSON body (or {} for 204).

    WHY `ctx.http`, NOT A DIRECT `httpx.AsyncClient` HERE.

    Same reasoning DataForSEO Connector's dfs_client.py documents: `ctx.http`
    is the platform's own egress client (single shared connection pool in
    production, swappable for imperal_sdk.testing.MockContext's MockHTTP in
    tests -- mock_get/mock_post register fixed responses per URL substring,
    no real network in the whole test suite). A hand-rolled httpx client
    would bypass both of those, and would need its own from-scratch test
    double just to unit test a single handler.
    """
    url = f"{BASE_URL}{path}"
    headers = _headers(api_key)
    method_fn = getattr(ctx.http, method.lower())
    kwargs: dict[str, Any] = {"headers": headers}
    if params:
        kwargs["params"] = params
    if json_body is not None:
        kwargs["json"] = json_body
    attempts = 0
    while True:
        try:
            resp = await method_fn(url, **kwargs)
        except Exception as exc:  # pragma: no cover -- network/transport failure
            raise KlaviyoError(0, f"Network error calling Klaviyo: {exc}") from exc

        if resp.status_code == 429 and attempts < _MAX_RETRIES_ON_429:
            retry_after = (resp.headers or {}).get("Retry-After")
            try:
                wait_s = float(retry_after) if retry_after else _DEFAULT_RETRY_AFTER
            except ValueError:
                wait_s = _DEFAULT_RETRY_AFTER
            await asyncio.sleep(min(wait_s, 10.0))
            attempts += 1
            continue

        if resp.status_code == 204:
            return {}

        try:
            payload = resp.json() if resp.body else {}
        except ValueError:
            payload = {"raw_text": resp.text() if hasattr(resp, "text") else ""}

        if resp.status_code >= 400:
            raise KlaviyoError(resp.status_code, _extract_error_detail(payload), payload)

        return payload


def build_filter(clauses: Iterable[str]) -> str:
    """Join pre-built JSON:API filter clauses with the comma-as-`and` alias.
    Callers build individual clauses with equals()/greater_or_equal()/etc
    below, so quoting is always correct.
    """
    clauses = [c for c in clauses if c]
    return ",".join(clauses)


def equals(field: str, value: str) -> str:
    return f'equals({field},"{_escape(value)}")'


def any_of(field: str, values: Iterable[str]) -> str:
    quoted = ",".join(f'"{_escape(v)}"' for v in values)
    return f"any({field},[{quoted}])"


def greater_than(field: str, value: str) -> str:
    return f"greater-than({field},{value})"


def greater_or_equal(field: str, value: str) -> str:
    return f"greater-or-equal({field},{value})"


def less_than(field: str, value: str) -> str:
    return f"less-than({field},{value})"


def contains(field: str, value: str) -> str:
    return f'contains({field},"{_escape(value)}")'


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def page_params(cursor: str = "", page_size: int = 20) -> dict:
    """Klaviyo cursor pagination: page[cursor] + page[size]. Leaving cursor
    empty omits it (first page) -- Klaviyo rejects an empty-string cursor
    value on some endpoints rather than treating it as "no cursor".
    """
    out: dict = {"page[size]": max(1, min(page_size, 100))}
    if cursor:
        out["page[cursor]"] = cursor
    return out


def next_cursor_from_links(payload: dict) -> str:
    """Pull the opaque cursor out of a list response's links.next URL, if
    present, so callers don't need to know Klaviyo's URL shape.
    """
    next_url = (payload.get("links") or {}).get("next")
    if not next_url:
        return ""
    if "page%5Bcursor%5D=" in next_url:
        return next_url.split("page%5Bcursor%5D=", 1)[1].split("&", 1)[0]
    if "page[cursor]=" in next_url:
        return next_url.split("page[cursor]=", 1)[1].split("&", 1)[0]
    return ""
