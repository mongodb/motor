.. currentmodule:: motor.motor_tornado

Examples With Callbacks And Coroutines
======================================

Programming with Motor is far easier with Tornado coroutines than with
raw callbacks. Here's an example that shows the difference.

This page describes using Motor with Tornado. Beginning in
version 0.5 Motor can also integrate with asyncio instead of Tornado.

.. contents::

With callbacks
--------------
An application that can create and display short messages:

.. code-block:: python

    import tornado.web, tornado.ioloop
    import motor

    class NewMessageHandler(tornado.web.RequestHandler):
        def get(self):
            """Show a 'compose message' form."""
            self.write('''
            <form method="post">
                <input type="text" name="msg">
                <input type="submit">
            </form>''')

        # Method exits before the HTTP request completes, thus "asynchronous"
        @tornado.web.asynchronous
        def post(self):
            """Insert a message."""
            msg = self.get_argument('msg')

            # Async insert; callback is executed when insert completes
            self.settings['db'].messages.insert_one(
                {'msg': msg},
                callback=self._on_response)

        def _on_response(self, result, error):
            if error:
                raise tornado.web.HTTPError(500, error)
            else:
                self.redirect('/')


    class MessagesHandler(tornado.web.RequestHandler):
        @tornado.web.asynchronous
        def get(self):
            """Display all messages."""
            self.write('<a href="/compose">Compose a message</a><br>')
            self.write('<ul>')
            db = self.settings['db']
            db.messages.find().sort([('_id', -1)]).each(self._got_message)

        def _got_message(self, message, error):
            if error:
                raise tornado.web.HTTPError(500, error)
            elif message:
                self.write('<li>%s</li>' % message['msg'])
            else:
                # Iteration complete
                self.write('</ul>')
                self.finish()

    db = motor.motor_tornado.MotorClient().test

    application = tornado.web.Application(
        [
            (r'/compose', NewMessageHandler),
            (r'/', MessagesHandler)
        ],
        db=db
    )

    print('Listening on http://localhost:8888')
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

The call to :meth:`~MotorCursor.each` could be
replaced with :meth:`~MotorCursor.to_list`, which is easier to use
with templates because the callback receives the entire result at once:

.. code-block:: python

    from tornado import template
    messages_template = template.Template('''<ul>
    {% for message in messages %}
        <li>{{ message['msg'] }}</li>
    {% end %}
    </ul>''')

    class MessagesHandler(tornado.web.RequestHandler):
        @tornado.web.asynchronous
        def get(self):
            """Display all messages
            """
            self.write('<a href="/compose">Compose a message</a><br>')
            self.write('<ul>')
            db = self.settings['db']
            (db.messages.find()
                .sort([('_id', -1)])
                .limit(10)
                .to_list(length=10, callback=self._got_messages))

        def _got_messages(self, messages, error):
            if error:
                raise tornado.web.HTTPError(500, error)
            elif messages:
                self.write(messages_template.generate(messages=messages))
            self.finish()

To protect you from buffering huge numbers of documents in memory, ``to_list``
requires a maximum ``length`` argument.

.. _coroutine-example:

With coroutines
---------------
Motor's asynchronous methods return `Futures <tornado.concurrent.Future>`.
Yield a Future to resolve it into a result or an exception:

.. code-block:: python

    from tornado import gen

    class NewMessageHandler(tornado.web.RequestHandler):
        @gen.coroutine
        def post(self):
            """Insert a message."""
            msg = self.get_argument('msg')
            db = self.settings['db']

            # insert_one() returns a Future. Yield the Future to get the result.
            result = yield db.messages.insert_one({'msg': msg})

            # Success
            self.redirect('/')


    class MessagesHandler(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            """Display all messages."""
            self.write('<a href="/compose">Compose a message</a><br>')
            self.write('<ul>')
            db = self.settings['db']
            cursor = db.messages.find().sort([('_id', -1)])
            while (yield cursor.fetch_next):
                message = cursor.next_object()
                self.write('<li>%s</li>' % message['msg'])

            # Iteration complete
            self.write('</ul>')
            self.finish()

One can parallelize operations and wait for all to complete. To query for
two messages at once and wait for both:

.. code-block:: python

    msg = yield db.messages.find_one({'_id': msg_id})

    # Start getting the previous. find_one returns a Future.
    prev_future = db.messages.find_one({'_id': {'$lt': msg_id}})

    # Start getting the next.
    next_future = db.messages.find_one({'_id': {'$gt': msg_id}})

    # Wait for both to complete by yielding the Futures.
    previous_msg, next_msg = yield [prev_future, next_future]

`async` and `await`
-------------------

Python 3.5 introduces `native coroutines`_ that use the `async` and `await`
keywords. Starting in Python 3.5, you can use `async def` instead of the
`gen.coroutine` decorator, and replace the while-loop with `async for`:

.. code-block:: python

    class MessagesHandler(tornado.web.RequestHandler):
        async def get(self):
            """Display all messages."""
            self.write('<a href="/compose">Compose a message</a><br>')
            self.write('<ul>')
            db = self.settings['db']

            # New in Python 3.5:
            async for message in db.messages.find().sort([('_id', -1)]):
                self.write('<li>%s</li>' % message['msg'])

            self.write('</ul>')
            self.finish()

This version of the code is dramatically faster.

.. _native coroutines: https://www.python.org/dev/peps/pep-0492/
