import logging
import os
import sys
from base64 import urlsafe_b64encode
from pprint import pformat

from motor.motor_tornado import MotorClient
from bson import json_util  # Installed with PyMongo.

import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="reload on source changes")
define("mongo", default="mongodb://localhost", help="MongoDB URI")
define("ns", default="test.test", help="database and collection name")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/socket", ChangesHandler)]

        templates = os.path.join(os.path.dirname(__file__),
                                 "tornado_change_stream_templates")

        super().__init__(handlers,
                         template_path=templates,
                         template_whitespace="all",
                         debug=options.debug)


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
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_change(cls, change):
        change_json = json_util.dumps(change)
        for waiter in cls.waiters:
            try:
                waiter.write_message(change_json)
            except Exception:
                logging.error("Error sending message", exc_info=True)

    @classmethod
    def on_change(cls, change):
        logging.info("got change of type '%s'", change.get('operationType'))

        # Each change notification has a binary _id. Use it to make an HTML
        # element id, then remove it.
        html_id = urlsafe_b64encode(change['_id']['_data']).decode().rstrip('=')
        change.pop('_id')
        change['html'] = '<div id="change-%s"><pre>%s</pre></div>' % (
            html_id,
            tornado.escape.xhtml_escape(pformat(change)))

        change['html_id'] = html_id
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
    if '.' not in options.ns:
        sys.stderr.write('Invalid ns "%s", must contain a "."' % (options.ns,))
        sys.exit(1)

    db_name, collection_name = options.ns.split('.', 1)
    client = MotorClient(options.mongo)
    collection = client[db_name][collection_name]

    app = Application()
    app.listen(options.port)
    loop = tornado.ioloop.IOLoop.current()
    # Start watching collection for changes.
    loop.add_callback(watch, collection)
    try:
        loop.start()
    except KeyboardInterrupt:
        pass
    finally:
        if change_stream is not None:
            change_stream.close()


if __name__ == "__main__":
    main()
