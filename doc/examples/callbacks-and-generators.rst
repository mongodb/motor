Examples With Callbacks And Generators
======================================

Programming with Motor is far easier using Tornado's ``gen`` module than when
using raw callbacks. Here's an example that shows the difference.

With callbacks
--------------

Here's an example of an application that can create and display short messages:

.. code-block:: python

    import tornado.web, tornado.ioloop
    import motor

    class NewMessageHandler(tornado.web.RequestHandler):
        def get(self):
            """Show a 'compose message' form"""
            self.write('''
            <form method="post">
                <input type="text" name="msg">
                <input type="submit">
            </form>''')

        # Method exits before the HTTP request completes, thus "asynchronous"
        @tornado.web.asynchronous
        def post(self):
            """Insert a message
            """
            msg = self.get_argument('msg')

            # Async insert; callback is executed when insert completes
            self.settings['db'].messages.insert(
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
            """Display all messages
            """
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

    db = motor.MotorClient().open_sync().test

    application = tornado.web.Application(
        [
            (r'/compose', NewMessageHandler),
            (r'/', MessagesHandler)
        ],
        db=db
    )

    print 'Listening on http://localhost:8888'
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

The call to :meth:`~motor.MotorCursor.each` could be
replaced with :meth:`~motor.MotorCursor.to_list`, which is easier to use
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
                .to_list(self._got_messages))

        def _got_messages(self, messages, error):
            if error:
                raise tornado.web.HTTPError(500, error)
            elif messages:
                self.write(messages_template.generate(messages=messages))
            self.finish()

It is extremely important to use :meth:`~motor.MotorCursor.limit` with
:meth:`~motor.MotorCursor.to_list` to avoid buffering an unbounded number of
documents in memory.

.. _generator-interface-example:

Using Tornado's generator interface
-----------------------------------

Motor provides :class:`~motor.Op`, :class:`~motor.WaitOp`, and
:class:`~motor.WaitAllOps` for convenient use with the
`tornado.gen module <http://www.tornadoweb.org/documentation/gen.html>`_. To
use async methods without explicit callbacks:

.. code-block:: python

    from tornado import gen

    class NewMessageHandler(tornado.web.RequestHandler):
        @tornado.web.asynchronous
        @gen.engine
        def post(self):
            """Insert a message
            """
            msg = self.get_argument('msg')
            db = self.settings['db']

            # motor.Op raises an exception on error, otherwise returns result
            result = yield motor.Op(db.messages.insert, {'msg': msg})

            # Success
            self.redirect('/')


    class MessagesHandler(tornado.web.RequestHandler):
        @tornado.web.asynchronous
        @gen.engine
        def get(self):
            """Display all messages
            """
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

Or using `to_list` instead of `next_object`:

.. code-block:: python

    cursor = db.messages.find().sort([('_id', -1)]).limit(100)
    messages = yield motor.Op(cursor.to_list)
    for message in messages:
        self.write('<li>%s</li>' % message['msg'])

One can also parallelize operations and wait for all to complete. To query for
two messages at once and wait for both:

.. code-block:: python

    msg = yield motor.Op(db.messages.find_one, {'_id': msg_id})

    # Get previous
    db.messages.find_one(
        {'_id': {'$lt': msg_id}},
        callback=(yield gen.Callback('prev')))

    # Get next
    db.messages.find_one(
        {'_id': {'$gt': msg_id}},
        callback=(yield gen.Callback('next')))

    previous_msg, next_msg = yield motor.WaitAllOps(['prev', 'next'])
