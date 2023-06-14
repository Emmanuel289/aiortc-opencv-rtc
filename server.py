import os
from aiohttp import web

ROOT = os.path.dirname(__file__)


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type='text/html', text=content)


if __name__ == '__main__':
    app = web.Application()
    app.router.add_get("/", index)
    web.run_app(app)
