"""
Unit tests for the detail-fetch timeout (no network access).
"""
import asyncio

import pytest

from kleinanzeigen_mcp.client import KleinanzeigenClient
from kleinanzeigen_mcp.types import DetailFetchError


class HangingPage:
    def __init__(self):
        self.closed = False

    async def goto(self, *args, **kwargs):
        await asyncio.sleep(3600)

    async def close(self):
        self.closed = True


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def new_page(self):
        return self.page

    async def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, context):
        self.context = context

    async def new_context(self, **kwargs):
        return self.context


@pytest.mark.timeout(10)
async def test_hanging_detail_fetch_raises_and_cleans_up():
    page = HangingPage()
    context = FakeContext(page)
    client = KleinanzeigenClient()
    client.browser = FakeBrowser(context)
    client.DETAIL_TIMEOUT_S = 0.5

    with pytest.raises(DetailFetchError, match="timeout in step 'goto'"):
        await client.get_listing_details("123456789")

    assert page.closed
    assert context.closed
