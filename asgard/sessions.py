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

import werkzeug
import werkzeug.local
import werkzeug.contrib.sessions
import sjoh
import contextlib
import sqlalchemy as sa
import sqlalchemy.sql as sql
import datetime

def create_sessions_table(metadata):
    t = sa.Table('sessions', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('session_id', sa.String(50), unique=True, nullable=False),
        sa.Column('data', sa.Text()),
        sa.Column('creation_date', sa.DateTime(), nullable=False, default=datetime.datetime.now),
        sa.Column('last_modification_date', sa.DateTime(), nullable=False, default=datetime.datetime.now),
    )
    return t

class DbSessionStore(werkzeug.contrib.sessions.SessionStore):
    def __init__(self, app):
        super(DbSessionStore, self).__init__()
        self.app = app
        self.serializer = sjoh.JsonSerializer()

    def delete(self, session):
        pass

    def get(self, sid):
        with self.app.transaction():
            if not self.is_valid_key(sid):
                return self.new()
            res = self.app.conn.execute(sql.select([self.app.sessions_table]).where(self.app.sessions_table.c.session_id == sid)).fetchall()
            if len(res) == 0:
                return self.session_class({}, sid, True)
            data = self.serializer.parse(res[0]["data"])
            return self.session_class(data, sid, False)

    def save(self, session):
        """Save a session."""
        with self.app.transaction():
            data = dict(session)
            data = self.serializer.stringify(data)
            res = self.app.conn.execute(self.app.sessions_table.update().where(self.app.sessions_table.c.session_id == session.sid)
                .values(data=data, last_modification_date=datetime.datetime.now()))
            if res.rowcount == 0:
                self.app.conn.execute(self.app.sessions_table.insert().values(session_id=session.sid, data=data))

class SessionHandler(object):
    def __init__(self, app):
        self.app = app
        self.session_store = DbSessionStore(app)
        self._stack = werkzeug.local.LocalStack()
        self.current = self._stack()

    @contextlib.contextmanager
    def declare_session(self, sid=None):
        if sid is None:
            session = self.session_store.new()
        else:
            session = self.session_store.get(sid)
        self._stack.push(session)
        try:
            yield session
        finally:
            if session.should_save:
                self.session_store.save(session)
            self._stack.pop()
