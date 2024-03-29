import logging
import os
import sys
from base64 import urlsafe_b64encode
from pprint import pformat

import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from bson import json_util  # Installed with PyMongo.
from tornado.options import define, options

from motor.motor_tornado import MotorClient

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="reload on source changes")
define("mongo", default="mongodb://localhost", help="MongoDB URI")
define("ns", default="test.test", help="database and collection name")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/", MainHandler), (r"/socket", ChangesHandler)]

        templates = os.path.join(os.path.dirname(__file__), "tornado_change_stream_templates")

        super().__init__(
            handlers, template_path=templates, template_whitespace="all", debug=options.debug
        )


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", changes=ChangesHandler.cache)


class ChangesHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 5

    def open(self):
        ChangesHandler.waiters.add(self)

    def on_close(self):
        ChangesHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, change):
        cls.cache.append(change)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size :]

    @classmethod
    def send_change(cls, change):
        change_json = json_util.dumps(change)
        for waiter in cls.waiters:
            try:
                waiter.write_message(change_json)
            except Exception as exc:
                logging.exception(exc)

    @classmethod
    def on_change(cls, change):
        logging.info("got change of type '%s'", change.get("operationType"))

        # Each change notification has a binary _id. Use it to make an HTML
        # element id, then remove it.
        data = change["_id"]["_data"]
        if not isinstance(data, bytes):
            data = data.encode("utf-8")
        html_id = urlsafe_b64encode(data).decode().rstrip("=")
        change.pop("_id")
        change_pre = tornado.escape.xhtml_escape(pformat(change))
        change["html"] = f'<div id="change-{html_id}"><pre>{change_pre}</pre></div>'
        change["html_id"] = html_id
        ChangesHandler.send_change(change)
        ChangesHandler.update_cache(change)


change_stream = None


async def watch(collection):
    global change_stream

    async with collection.watch() as change_stream:
        async for change in change_stream:
            ChangesHandler.on_change(change)


def main():
    tornado.options.parse_command_line()
    if "." not in options.ns:
        sys.stderr.write(f'Invalid ns "{options.ns}", must contain a "."')
        sys.exit(1)

    db_name, collection_name = options.ns.split(".", 1)
    client = MotorClient(options.mongo)
    collection = client[db_name][collection_name]

    app = Application()
    app.listen(options.port)
    loop = tornado.ioloop.IOLoop.current()

    # Start watching collection for changes.
    try:
        loop.run_sync(lambda: watch(collection))
    except KeyboardInterrupt:
        if change_stream:
            loop.run_sync(change_stream.close)


if __name__ == "__main__":
    main()
