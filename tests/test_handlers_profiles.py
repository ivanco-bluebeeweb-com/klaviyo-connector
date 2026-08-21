"""Tests for handlers_profiles.py -- Profiles, Lists, Segments."""
from __future__ import annotations

import pytest

import handlers_profiles as hp
from models import (
    CreateProfileParams, UpdateProfileParams, GetProfileParams,
    ListProfilesParams, DeleteProfileParams,
    CreateListParams, ListListsParams, ListIdParams,
    BulkProfileIdsParams, ListMembersParams,
    ListSegmentsParams, SegmentIdParams, ListSegmentMembersParams,
)


def _profile_row(pid="prof_1", email="a@example.com"):
    return {"id": pid, "attributes": {"email": email, "first_name": "Ann"}}


# ── requires connection ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_profile_requires_connection(ctx):
    """_need_key raises ValueError when disconnected -- same convention as
    Sales Strategy Hub's validation raises, caught by the platform's own
    dispatch layer in production and surfaced to the user as an error."""
    with pytest.raises(ValueError):
        await hp.create_profile(ctx, CreateProfileParams(email="a@example.com"))


# ── profiles ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_profile_requires_identifier(ctx_connected):
    result = await hp.create_profile(ctx_connected, CreateProfileParams())
    assert result.error is not None


@pytest.mark.asyncio
async def test_create_profile_success(ctx_connected):
    ctx_connected.http.mock_post("/profiles/", {"data": _profile_row()}, status=201)
    result = await hp.create_profile(ctx_connected, CreateProfileParams(email="a@example.com"))
    assert result.error is None
    assert result.data.email == "a@example.com"


@pytest.mark.asyncio
async def test_update_profile_success(ctx_connected):
    ctx_connected.http.mock_patch("/profiles/prof_1/", {"data": _profile_row()}, status=200)
    result = await hp.update_profile(ctx_connected, UpdateProfileParams(profile_id="prof_1", first_name="Ann"))
    assert result.error is None


@pytest.mark.asyncio
async def test_get_profile_success(ctx_connected):
    ctx_connected.http.mock_get("/profiles/prof_1/", {"data": _profile_row()}, status=200)
    result = await hp.get_profile(ctx_connected, GetProfileParams(profile_id="prof_1"))
    assert result.error is None
    assert result.data.id == "prof_1"


@pytest.mark.asyncio
async def test_list_profiles_success(ctx_connected):
    ctx_connected.http.mock_get("/profiles/", {"data": [_profile_row()], "links": {}}, status=200)
    result = await hp.list_profiles(ctx_connected, ListProfilesParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_delete_profile_success(ctx_connected):
    ctx_connected.http.mock_post("/data-privacy-deletion-jobs/", {}, status=202)
    result = await hp.delete_profile(ctx_connected, DeleteProfileParams(profile_id="prof_1"))
    assert result.error is None
    assert result.data.deleted is True


# ── lists ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_list_success(ctx_connected):
    ctx_connected.http.mock_post("/lists/", {"data": {"id": "list_1", "attributes": {"name": "VIP"}}}, status=201)
    result = await hp.create_list(ctx_connected, CreateListParams(name="VIP"))
    assert result.error is None
    assert result.data.name == "VIP"


@pytest.mark.asyncio
async def test_list_lists_success(ctx_connected):
    ctx_connected.http.mock_get("/lists/", {"data": [{"id": "list_1", "attributes": {"name": "VIP"}}], "links": {}}, status=200)
    result = await hp.list_lists(ctx_connected, ListListsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_get_list_success(ctx_connected):
    ctx_connected.http.mock_get("/lists/list_1/", {"data": {"id": "list_1", "attributes": {"name": "VIP"}}}, status=200)
    result = await hp.get_list(ctx_connected, ListIdParams(list_id="list_1"))
    assert result.error is None


@pytest.mark.asyncio
async def test_delete_list_success(ctx_connected):
    ctx_connected.http.mock_delete("/lists/list_1/", {}, status=204)
    result = await hp.delete_list(ctx_connected, ListIdParams(list_id="list_1"))
    assert result.error is None
    assert result.data.deleted is True


@pytest.mark.asyncio
async def test_add_profiles_to_list_success(ctx_connected):
    ctx_connected.http.mock_post("/lists/list_1/relationships/profiles/", {}, status=204)
    result = await hp.add_profiles_to_list(ctx_connected, BulkProfileIdsParams(list_id="list_1", profile_ids=["p1", "p2"]))
    assert result.error is None


@pytest.mark.asyncio
async def test_remove_profiles_from_list_success(ctx_connected):
    ctx_connected.http.mock_delete("/lists/list_1/relationships/profiles/", {}, status=204)
    result = await hp.remove_profiles_from_list(ctx_connected, BulkProfileIdsParams(list_id="list_1", profile_ids=["p1"]))
    assert result.error is None


@pytest.mark.asyncio
async def test_list_list_members_success(ctx_connected):
    ctx_connected.http.mock_get("/lists/list_1/profiles/", {"data": [_profile_row()], "links": {}}, status=200)
    result = await hp.list_list_members(ctx_connected, ListMembersParams(list_id="list_1"))
    assert result.error is None
    assert len(result.data.items) == 1


# ── segments ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_segments_success(ctx_connected):
    ctx_connected.http.mock_get("/segments/", {"data": [{"id": "seg_1", "attributes": {"name": "Active"}}], "links": {}}, status=200)
    result = await hp.list_segments(ctx_connected, ListSegmentsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_get_segment_success(ctx_connected):
    ctx_connected.http.mock_get("/segments/seg_1/", {"data": {"id": "seg_1", "attributes": {"name": "Active"}}}, status=200)
    result = await hp.get_segment(ctx_connected, SegmentIdParams(segment_id="seg_1"))
    assert result.error is None


@pytest.mark.asyncio
async def test_list_segment_members_success(ctx_connected):
    ctx_connected.http.mock_get("/segments/seg_1/profiles/", {"data": [_profile_row()], "links": {}}, status=200)
    result = await hp.list_segment_members(ctx_connected, ListSegmentMembersParams(segment_id="seg_1"))
    assert result.error is None
    assert len(result.data.items) == 1
