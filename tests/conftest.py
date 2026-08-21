"""Shared fixtures -- mirrors DataForSEO Connector's ctx fixture."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _patch_mock_http_verbs():
    """imperal_sdk.testing.MockHTTP only ships mock_get/mock_post -- its own
    _find() dispatch already handles PUT/PATCH/DELETE internally, there is
    just no public registrar for them yet. Klaviyo's API leans heavily on
    PATCH (update_profile, set_flow_status, update_catalog_item) and DELETE
    (delete_list, delete_coupon, delete_webhook, remove_profiles_from_list),
    so we extend the class once here rather than duplicate _find's tuple
    shape by reaching into ._mocks directly in every test.
    """
    from imperal_sdk.testing.mock_context import MockHTTP

    if hasattr(MockHTTP, "mock_patch"):
        return  # SDK added it upstream -- nothing to do.

    def _register(method):
        def _fn(self, url_pattern, response, status=200, headers=None):
            self._mocks.append((method, url_pattern, response, status, headers or {}))
        return _fn

    MockHTTP.mock_patch = _register("PATCH")
    MockHTTP.mock_delete = _register("DELETE")
    MockHTTP.mock_put = _register("PUT")


_patch_mock_http_verbs()


@pytest.fixture
def ctx():
    from imperal_sdk.testing import MockContext, MockSecretStore

    mock = MockContext()
    mock.secrets = MockSecretStore({})
    return mock


@pytest.fixture
def ctx_connected(ctx):
    """Same as `ctx` but with a Klaviyo API key already saved."""
    from imperal_sdk.testing import MockSecretStore
    ctx.secrets = MockSecretStore({
        "klaviyo_api_key": "pk_test_1234567890",
    })
    return ctx
