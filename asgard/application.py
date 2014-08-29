# Copyright (c) 2014, Nicolas Vanhoren
# 
# Released under the MIT license
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals, print_function, absolute_import

import werkzeug.local
import sqlalchemy as sa
import contextlib
from . import sessions
from . import web

class Asgard(object):

    def __init__(self, import_name, flask_parameters=None):
        """
        Creates an Asgard application.
        """

        self.configuration = {}
        self.import_name = import_name

        """
        The engine used to connect to the database.
        """
        self.engine = None

        self._conn_stack = werkzeug.local.LocalStack()
        """
        A proxy to a connection object currently used to perform calls to the database.
        """
        self.connection = self._conn_stack()
        """
        The metadata object containing all the information about the db schema.
        """
        self.metadata = sa.MetaData()

        self.sessions_table = sessions.create_sessions_table(self.metadata)
        self.session_handler = sessions.SessionHandler(self)
        self.session = werkzeug.local.LocalProxy(lambda: self.session_handler.current)

        flask_parameters = flask_parameters or {}
        self.web_app = web.WebApp(self, self.import_name, **flask_parameters)

    @property
    def conn(self):
        return self.connection

    def configure(self, configuration):
        self.configuration = configuration
        self.engine = sa.engine_from_config(self.configuration.setdefault("database", {}))
        self.web_app.config.update(**self.configuration.setdefault("web", {}))

    @contextlib.contextmanager
    def transaction(self):
        """
        A context manager that initializes a connection and store it in the ``conn`` proxy. When the operations
        terminate normally, the transaction is commited. If there is an exception, the transaction is rollbacked.
        """
        assert self._conn_stack.top is None, "Only one connection can be opened at the same time"
        self._conn_stack.push(self.engine.connect())
        try:
            self.conn.current_transaction = self.conn.begin()
            try:
                yield
                self.conn.current_transaction.commit()
            except:
                self.conn.current_transaction.rollback()
                raise
        finally:
            try:
                self.conn.close()
            except:
                pass
            self._conn_stack.pop()

    def transactional(self, func):
        """
        A decorator that will call ``transaction`` before the invocation of the function.
        """
        def alt(*args, **kwargs):
            with self.transaction():
                return func(*args, **kwargs)
        alt.__name__ = func.__name__
        alt.__module__ = func.__module__
        return alt

    def manager(self, claz):
        """
        A decorator to mark a class as a manager. Thus, a single instance of that class will be instanciated and
        stored in the ``i`` attribute of the class and its methods will be accessible by RPC calls.

        It should be noted that all methods declared in a manager should take in arguments and return only types
        succeptible to be correctly serialized/deserialized by whatever RPC protocol will be used in front of
        the managers.
        """
        instance = claz()
        claz.i = instance
        return claz

    def __enter__(self):
        _app_stack.push(self)
        return self

    def __exit__(self, *args, **kwargs):
        _app_stack.pop()

    def declare_session(self, sid):
        return self.session_handler.declare_session(sid)

_app_stack = werkzeug.local.LocalStack()
"""
A proxy to the current Asgard application.
"""
app = _app_stack()

engine = werkzeug.local.LocalProxy(lambda: app.engine)
conn = werkzeug.local.LocalProxy(lambda: app.connection)
connection = werkzeug.local.LocalProxy(lambda: app.connection)
session = werkzeug.local.LocalProxy(lambda: app.session)
