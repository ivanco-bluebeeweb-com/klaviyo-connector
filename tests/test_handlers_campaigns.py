"""Tests for handlers_campaigns.py -- Campaigns, Flows, Templates, Tags."""
from __future__ import annotations

import pytest

import handlers_campaigns as hc
from models import (
    ListCampaignsParams, CampaignIdParams, CreateCampaignParams, SendCampaignParams,
    ListFlowsParams, FlowIdParams, SetFlowStatusParams,
    ListTemplatesParams, TemplateIdParams, CreateTemplateParams,
    ListTagsParams, CreateTagParams, TagResourceParams,
)


@pytest.mark.asyncio
async def test_list_campaigns_requires_connection(ctx):
    with pytest.raises(ValueError):
        await hc.list_campaigns(ctx, ListCampaignsParams())


# ── campaigns ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_campaigns_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/campaigns/",
        {"data": [{"id": "camp_1", "attributes": {"name": "Sale", "status": "draft"}}], "links": {}},
        status=200,
    )
    result = await hc.list_campaigns(ctx_connected, ListCampaignsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_get_campaign_not_found(ctx_connected):
    ctx_connected.http.mock_get("/campaigns/missing/", {"data": {}}, status=200)
    result = await hc.get_campaign(ctx_connected, CampaignIdParams(campaign_id="missing"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_create_campaign_success(ctx_connected):
    ctx_connected.http.mock_post(
        "/campaigns/",
        {"data": {"id": "camp_1", "attributes": {"name": "Sale", "status": "draft"}}},
        status=201,
    )
    result = await hc.create_campaign(
        ctx_connected,
        CreateCampaignParams(name="Sale", list_ids=["list_1"], subject="Big Sale", from_email="a@x.com", from_label="X"),
    )
    assert result.error is None
    assert result.data.name == "Sale"


@pytest.mark.asyncio
async def test_send_campaign_success(ctx_connected):
    ctx_connected.http.mock_post("/campaign-send-jobs/", {}, status=202)
    result = await hc.send_campaign(ctx_connected, SendCampaignParams(campaign_id="camp_1"))
    assert result.error is None
    assert result.data.status == "sending"


# ── flows ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_flows_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/flows/",
        {"data": [{"id": "flow_1", "attributes": {"name": "Welcome", "status": "live"}}], "links": {}},
        status=200,
    )
    result = await hc.list_flows(ctx_connected, ListFlowsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_get_flow_not_found(ctx_connected):
    ctx_connected.http.mock_get("/flows/missing/", {"data": {}}, status=200)
    result = await hc.get_flow(ctx_connected, FlowIdParams(flow_id="missing"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_set_flow_status_rejects_bad_status(ctx_connected):
    result = await hc.set_flow_status(ctx_connected, SetFlowStatusParams(flow_id="flow_1", status="bogus"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_set_flow_status_success(ctx_connected):
    ctx_connected.http.mock_patch(
        "/flows/flow_1/",
        {"data": {"id": "flow_1", "attributes": {"name": "Welcome", "status": "live"}}},
        status=200,
    )
    result = await hc.set_flow_status(ctx_connected, SetFlowStatusParams(flow_id="flow_1", status="live"))
    assert result.error is None
    assert result.data.status == "live"


# ── templates ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_templates_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/templates/",
        {"data": [{"id": "tpl_1", "attributes": {"name": "Newsletter"}}], "links": {}},
        status=200,
    )
    result = await hc.list_templates(ctx_connected, ListTemplatesParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_get_template_not_found(ctx_connected):
    ctx_connected.http.mock_get("/templates/missing/", {"data": {}}, status=200)
    result = await hc.get_template(ctx_connected, TemplateIdParams(template_id="missing"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_create_template_success(ctx_connected):
    ctx_connected.http.mock_post(
        "/templates/",
        {"data": {"id": "tpl_1", "attributes": {"name": "Newsletter"}}},
        status=201,
    )
    result = await hc.create_template(ctx_connected, CreateTemplateParams(name="Newsletter", html="<p>Hi</p>"))
    assert result.error is None
    assert result.data.name == "Newsletter"


# ── tags ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tags_success(ctx_connected):
    ctx_connected.http.mock_get(
        "/tags/",
        {"data": [{"id": "tag_1", "attributes": {"name": "VIP"}}]},
        status=200,
    )
    result = await hc.list_tags(ctx_connected, ListTagsParams())
    assert result.error is None
    assert len(result.data.items) == 1


@pytest.mark.asyncio
async def test_create_tag_success(ctx_connected):
    ctx_connected.http.mock_post("/tags/", {"data": {"id": "tag_1", "attributes": {"name": "VIP"}}}, status=201)
    result = await hc.create_tag(ctx_connected, CreateTagParams(name="VIP"))
    assert result.error is None
    assert result.data.name == "VIP"


@pytest.mark.asyncio
async def test_tag_resource_rejects_bad_type(ctx_connected):
    result = await hc.tag_resource(ctx_connected, TagResourceParams(tag_id="tag_1", resource_type="bogus", resource_id="x"))
    assert result.error is not None


@pytest.mark.asyncio
async def test_tag_resource_success(ctx_connected):
    ctx_connected.http.mock_post("/tags/tag_1/relationships/campaigns/", {}, status=204)
    result = await hc.tag_resource(ctx_connected, TagResourceParams(tag_id="tag_1", resource_type="campaign", resource_id="camp_1"))
    assert result.error is None
