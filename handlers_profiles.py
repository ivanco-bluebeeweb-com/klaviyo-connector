"""Profiles, Lists, Segments -- contact management, the core of any
marketing platform. Profiles are the person record; Lists are static
opt-in groups a person is explicitly added/removed from; Segments are
Klaviyo-computed dynamic groups (defined by conditions in Klaviyo's UI) --
read-only from the API side, you cannot add/remove a profile from a
segment directly, only from the lists/behavior that feed it.
"""
from __future__ import annotations

import klaviyo_client as kc
from imperal_sdk import ActionResult, sdl

from app import ext, chat
from accounts import _get_key
from models import (
    NoParams,
    CreateProfileParams, UpdateProfileParams, GetProfileParams,
    ListProfilesParams, DeleteProfileParams, Profile, ProfileList,
    CreateListParams, ListListsParams, ListIdParams,
    KlaviyoList, KlaviyoListList,
    BulkProfileIdsParams,
    ListMembersParams, ListMembershipResult,
    ListSegmentsParams, SegmentIdParams, Segment, SegmentList,
    ListSegmentMembersParams,
    DeleteResult,
)


async def _need_key(ctx):
    key = await _get_key(ctx)
    if not key:
        raise ValueError("Klaviyo is not connected yet. Call connect_klaviyo first.")
    return key


def _profile_from_row(row: dict) -> Profile:
    a = row.get("attributes") or {}
    loc = a.get("location") or {}
    return Profile(
        id=row.get("id", ""),
        title=a.get("email") or a.get("phone_number") or row.get("id", ""),
        email=a.get("email", ""),
        phone_number=a.get("phone_number", ""),
        first_name=a.get("first_name", "") or "",
        last_name=a.get("last_name", "") or "",
        organization=a.get("organization", "") or "",
        location_city=loc.get("city", "") or "",
        location_country=loc.get("country", "") or "",
        created=a.get("created", "") or "",
        updated=a.get("updated", "") or "",
        properties=a.get("properties", {}) or {},
    )


@chat.function(name="create_profile", data_model=Profile, description="Create a new Klaviyo profile (contact) with email/phone/external_id plus optional name, organization, location, and custom properties.")
async def create_profile(ctx, params: CreateProfileParams) -> ActionResult:
    """Create or update-by-identifier a Klaviyo profile (person record)."""
    key = await _need_key(ctx)
    if not (params.email or params.phone_number or params.external_id):
        return ActionResult.error("At least one of email, phone_number, or external_id is required.")
    attrs: dict = {}
    if params.email:
        attrs["email"] = params.email
    if params.phone_number:
        attrs["phone_number"] = params.phone_number
    if params.external_id:
        attrs["external_id"] = params.external_id
    if params.first_name:
        attrs["first_name"] = params.first_name
    if params.last_name:
        attrs["last_name"] = params.last_name
    if params.organization:
        attrs["organization"] = params.organization
    if params.title:
        attrs["title"] = params.title
    if params.location_city or params.location_country:
        attrs["location"] = {k: v for k, v in {"city": params.location_city, "country": params.location_country}.items() if v}
    if params.properties:
        attrs["properties"] = params.properties

    body = {"data": {"type": "profile", "attributes": attrs}}
    payload = await kc.request(ctx, key, "POST", "/profiles/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_profile_from_row(row), summary=f"Created profile {attrs.get('email') or attrs.get('phone_number') or row.get('id','')}.")


@chat.function(name="update_profile", data_model=Profile, description="Update an existing Klaviyo profile's email/phone/name/organization/title or merge custom properties. Only given fields change.")
async def update_profile(ctx, params: UpdateProfileParams) -> ActionResult:
    """Update selected fields on an existing profile by id."""
    key = await _need_key(ctx)
    attrs: dict = {}
    if params.email:
        attrs["email"] = params.email
    if params.phone_number:
        attrs["phone_number"] = params.phone_number
    if params.first_name:
        attrs["first_name"] = params.first_name
    if params.last_name:
        attrs["last_name"] = params.last_name
    if params.organization:
        attrs["organization"] = params.organization
    if params.title:
        attrs["title"] = params.title
    if params.properties:
        attrs["properties"] = params.properties
    if not attrs:
        return ActionResult.error("Provide at least one field to update.")
    body = {"data": {"type": "profile", "id": params.profile_id, "attributes": attrs}}
    payload = await kc.request(ctx, key, "PATCH", f"/profiles/{params.profile_id}/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_profile_from_row(row), summary=f"Updated profile {params.profile_id}.")


@chat.function(name="get_profile", data_model=Profile, description="Read one Klaviyo profile in full by its id.")
async def get_profile(ctx, params: GetProfileParams) -> ActionResult:
    """Read one profile in full by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/profiles/{params.profile_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error(f"Profile {params.profile_id} not found.")
    return ActionResult.success(_profile_from_row(row), summary=f"Read profile {params.profile_id}.")


@chat.function(name="list_profiles", data_model=ProfileList, description="List Klaviyo profiles, optionally filtered by exact email or phone number, with cursor pagination.")
async def list_profiles(ctx, params: ListProfilesParams) -> ActionResult:
    """List profiles, optionally filtered by email/phone, with cursor pagination."""
    key = await _need_key(ctx)
    filters = []
    if params.email:
        filters.append(kc.equals("email", params.email))
    if params.phone_number:
        filters.append(kc.equals("phone_number", params.phone_number))
    query = kc.page_params(params.cursor, params.page_size)
    if filters:
        query["filter"] = kc.build_filter(filters)
    payload = await kc.request(ctx, key, "GET", "/profiles/", params=query)
    rows = payload.get("data") or []
    result = ProfileList(items=[_profile_from_row(r) for r in rows])
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"Found {len(rows)} profile(s).")


@chat.function(name="delete_profile", data_model=DeleteResult, description="Request deletion of a Klaviyo profile (data-privacy erasure request). This is queued by Klaviyo and cannot be undone once processed.")
async def delete_profile(ctx, params: DeleteProfileParams) -> ActionResult:
    """Permanently delete a profile and all its data from Klaviyo."""
    key = await _need_key(ctx)
    body = {"data": {"type": "data-privacy-deletion-job", "attributes": {"profile": {"data": {"type": "profile", "id": params.profile_id}}}}}
    await kc.request(ctx, key, "POST", "/data-privacy-deletion-jobs/", json_body=body)
    return ActionResult.success(DeleteResult(id=params.profile_id, title=params.profile_id, deleted=True), summary=f"Queued deletion for profile {params.profile_id}.")


# ──────────────────────────────────────────────────────────────────────────
# Lists.
# ──────────────────────────────────────────────────────────────────────────


def _list_from_row(row: dict) -> KlaviyoList:
    a = row.get("attributes") or {}
    return KlaviyoList(id=row.get("id", ""), title=a.get("name", ""), name=a.get("name", ""), created=a.get("created", "") or "", updated=a.get("updated", "") or "")


@chat.function(name="create_list", data_model=KlaviyoList, description="Create a new Klaviyo list (a static, explicit opt-in group you add/remove profiles from directly).")
async def create_list(ctx, params: CreateListParams) -> ActionResult:
    """Create a new static Klaviyo list (an opt-in group)."""
    key = await _need_key(ctx)
    body = {"data": {"type": "list", "attributes": {"name": params.name}}}
    payload = await kc.request(ctx, key, "POST", "/lists/", json_body=body)
    row = payload.get("data") or {}
    return ActionResult.success(_list_from_row(row), summary=f"Created list '{params.name}'.")


@chat.function(name="list_lists", data_model=KlaviyoListList, description="List all Klaviyo lists with cursor pagination.")
async def list_lists(ctx, params: ListListsParams) -> ActionResult:
    """List all Klaviyo lists with cursor pagination."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", "/lists/", params=kc.page_params(params.cursor, 20))
    rows = payload.get("data") or []
    result = KlaviyoListList(items=[_list_from_row(r) for r in rows])
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"Found {len(rows)} list(s).")


@chat.function(name="get_list", data_model=KlaviyoList, description="Read one Klaviyo list's details by id.")
async def get_list(ctx, params: ListIdParams) -> ActionResult:
    """Read one list's details by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/lists/{params.list_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error(f"List {params.list_id} not found.")
    return ActionResult.success(_list_from_row(row), summary=f"Read list {params.list_id}.")


@chat.function(name="delete_list", data_model=DeleteResult, description="Permanently delete a Klaviyo list. Profiles themselves are not deleted, only removed from this list.")
async def delete_list(ctx, params: ListIdParams) -> ActionResult:
    """Permanently delete a list; profiles themselves are not deleted."""
    key = await _need_key(ctx)
    await kc.request(ctx, key, "DELETE", f"/lists/{params.list_id}/")
    return ActionResult.success(DeleteResult(id=params.list_id, title=params.list_id, deleted=True), summary=f"Deleted list {params.list_id}.")


@chat.function(name="add_profiles_to_list", data_model=ListMembershipResult, description="Add one or more existing profiles (by id) to a Klaviyo list.")
async def add_profiles_to_list(ctx, params: BulkProfileIdsParams) -> ActionResult:
    """Add existing profiles (by id) to a list."""
    key = await _need_key(ctx)
    body = {"data": [{"type": "profile", "id": pid} for pid in params.profile_ids]}
    await kc.request(ctx, key, "POST", f"/lists/{params.list_id}/relationships/profiles/", json_body=body)
    return ActionResult.success(ListMembershipResult(id=params.list_id, title=params.list_id, profile_count=len(params.profile_ids)), summary=f"Added {len(params.profile_ids)} profile(s) to list {params.list_id}.")


@chat.function(name="remove_profiles_from_list", data_model=ListMembershipResult, description="Remove one or more profiles (by id) from a Klaviyo list.")
async def remove_profiles_from_list(ctx, params: BulkProfileIdsParams) -> ActionResult:
    """Remove profiles (by id) from a list."""
    key = await _need_key(ctx)
    body = {"data": [{"type": "profile", "id": pid} for pid in params.profile_ids]}
    await kc.request(ctx, key, "DELETE", f"/lists/{params.list_id}/relationships/profiles/", json_body=body)
    return ActionResult.success(ListMembershipResult(id=params.list_id, title=params.list_id, profile_count=len(params.profile_ids)), summary=f"Removed {len(params.profile_ids)} profile(s) from list {params.list_id}.")


@chat.function(name="list_list_members", data_model=ProfileList, description="List the profiles that belong to one Klaviyo list, with cursor pagination.")
async def list_list_members(ctx, params: ListMembersParams) -> ActionResult:
    """List the profiles currently on a list, with cursor pagination."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/lists/{params.list_id}/profiles/", params=kc.page_params(params.cursor, params.page_size))
    rows = payload.get("data") or []
    result = ProfileList(items=[_profile_from_row(r) for r in rows])
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"List {params.list_id} has {len(rows)} member(s) on this page.")


# ──────────────────────────────────────────────────────────────────────────
# Segments (read-only from the API -- membership is computed by Klaviyo).
# ──────────────────────────────────────────────────────────────────────────


def _segment_from_row(row: dict) -> Segment:
    a = row.get("attributes") or {}
    return Segment(id=row.get("id", ""), title=a.get("name", ""), name=a.get("name", ""), is_active=bool(a.get("is_active", True)), created=a.get("created", "") or "")


@chat.function(name="list_segments", data_model=SegmentList, description="List Klaviyo segments (dynamic, condition-based groups computed by Klaviyo itself) with cursor pagination.")
async def list_segments(ctx, params: ListSegmentsParams) -> ActionResult:
    """List Klaviyo segments (dynamic, condition-computed groups)."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", "/segments/", params=kc.page_params(params.cursor, 20))
    rows = payload.get("data") or []
    result = SegmentList(items=[_segment_from_row(r) for r in rows])
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"Found {len(rows)} segment(s).")


@chat.function(name="get_segment", data_model=Segment, description="Read one Klaviyo segment's details by id.")
async def get_segment(ctx, params: SegmentIdParams) -> ActionResult:
    """Read one segment's definition and details by id."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/segments/{params.segment_id}/")
    row = payload.get("data") or {}
    if not row:
        return ActionResult.error(f"Segment {params.segment_id} not found.")
    return ActionResult.success(_segment_from_row(row), summary=f"Read segment {params.segment_id}.")


@chat.function(name="list_segment_members", data_model=ProfileList, description="List the profiles currently matching one Klaviyo segment's conditions, with cursor pagination. Read-only -- you cannot add/remove members directly, only the underlying behavior/list membership that feeds the segment's own conditions.")
async def list_segment_members(ctx, params: ListSegmentMembersParams) -> ActionResult:
    """List the profiles currently matching a segment's conditions."""
    key = await _need_key(ctx)
    payload = await kc.request(ctx, key, "GET", f"/segments/{params.segment_id}/profiles/", params=kc.page_params(params.cursor, 20))
    rows = payload.get("data") or []
    result = ProfileList(items=[_profile_from_row(r) for r in rows])
    result.next_cursor = kc.next_cursor_from_links(payload)
    return ActionResult.success(result, summary=f"Segment {params.segment_id} has {len(rows)} member(s) on this page.")
