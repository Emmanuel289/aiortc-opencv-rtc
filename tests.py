
import os
import pytest
from aiohttp import web
from server import index

ROOT = os.path.dirname(__file__)


@pytest.mark.asyncio
async def test_index(aiohttp_client):
    app = web.Application()
    app.router.add_get("/", index)
    client = await aiohttp_client(app)

    response = await client.get('/')
    assert response.status == 200

    content = await response.text()
    expected_content = open(os.path.join(ROOT, "index.html"), "r").read()
    assert content == expected_content
