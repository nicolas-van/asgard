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

import unittest

import asgard.application as application
import asgard.users as users
import sqlalchemy as sa

app = application.Asgard(__name__)
app_users = users.UsersPlugin(app)

class DbTest(unittest.TestCase):
    """Class to extend to easily test code using the database."""
    def setUp(self):
        self.tmp_engine = app.engine
        app.engine = sa.create_engine('sqlite:///:memory:')
        app.metadata.create_all(app.engine)
        app.__enter__()
        self.trans = app.transaction()
        self.trans.__enter__()

    def tearDown(self):
        self.trans.__exit__(None, None, None)
        app.engine.dispose()
        app.engine = self.tmp_engine
        app.__exit__(None, None, None)


class UsersTest(DbTest):

    def test_base(self):
        app_users.UsersManager.i.create_user("test@test.com", "abc")
        self.assertTrue(app_users.UsersManager.i.test_user("test@test.com", "abc"))
        self.assertFalse(app_users.UsersManager.i.test_user("test@test.com", "xyz"))

    def test_change_password(self):
        id = app_users.UsersManager.i.create_user("test@test.com", "abc")
        self.assertTrue(app_users.UsersManager.i.test_user("test@test.com", "abc"))
        app_users.UsersManager.i.set_password(id, "xyz")
        self.assertTrue(app_users.UsersManager.i.test_user("test@test.com", "xyz"))
        self.assertFalse(app_users.UsersManager.i.test_user("test@test.com", "abc"))