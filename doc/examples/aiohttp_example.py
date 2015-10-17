# These comments let tutorial-asyncio.rst include this code in sections.
# -- setup-start --
import asyncio

from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient


@asyncio.coroutine
def setup_db():
    db = AsyncIOMotorClient().test
    yield from db.pages.drop()
    html = '<html><body>{}</body></html>'
    yield from db.pages.insert({'_id': 'page-one',
                                'body': html.format('Hello!')})

    yield from db.pages.insert({'_id': 'page-two',
                                'body': html.format('Goodbye.')})

    return db
# -- setup-end --


# -- handler-start --
@asyncio.coroutine
def page_handler(request):
    # If the visitor gets "/pages/page-one", then page_name is "page-one".
    page_name = request.match_info.get('page_name')

    # Retrieve the long-lived database handle.
    db = request.app['db']

    # Find the page by its unique id.
    document = yield from db.pages.find_one(page_name)

    if not document:
        return web.HTTPNotFound(text='No page named {!r}'.format(page_name))

    return web.Response(body=document['body'].encode())
# -- handler-end --


# -- create-server-start --
@asyncio.coroutine
def create_example_server(loop):
    db = yield from setup_db()

    app = web.Application(loop=loop)
    app['db'] = db
    app.router.add_route('GET', '/pages/{page_name}', page_handler)
    handler = app.make_handler()
    server = yield from loop.create_server(handler, '127.0.0.1', 8080)
    return server, app, handler
# -- create-server-end --


# -- shutdown-start --
@asyncio.coroutine
def shutdown(server, app, handler):
    sock = server.sockets[0]
    app.loop.remove_reader(sock.fileno())
    sock.close()

    yield from handler.finish_connections(1.0)
    server.close()
    yield from server.wait_closed()
    yield from app.finish()
# -- shutdown-end --


# -- main-start --
def main():
    loop = asyncio.get_event_loop()
    server, app, handler = loop.run_until_complete(create_example_server(loop))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(shutdown(server, app, handler))
    loop.close()
# -- main-end --

if __name__ == '__main__':
    main()
