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

import asgard.tables as table_manager
import sqlalchemy as sa
import asgard.application as application

app = application.Asgard()

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


test_table = sa.Table('test_table', app.metadata,
   sa.Column('id', sa.Integer, primary_key=True),
   sa.Column('key', sa.String(50), unique=True),
   sa.Column('value', sa.String(50)),
)

class TestTableManager(table_manager.table_manager(test_table)):
    pass

TestTableManager.i = TestTableManager()

class TableManagerTest(DbTest):

    def test_create(self):
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        record = TestTableManager.i.read_by_id(id)
        self.assertEqual(record["id"], id)
        self.assertEqual(record["key"], "a")
        self.assertEqual(record["value"], "b")

    def test_read(self):
        TestTableManager.i.create({"key": "a", "value": "b"})
        records = TestTableManager.i.read("key == 'a'")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["key"], "a")
        self.assertEqual(records[0]["value"], "b")

    def test_read_order(self):
        TestTableManager.i.create_many([
            {"key": "a", "value": "b"},
            {"key": "c", "value": "b"},
            {"key": "d", "value": "g"},
        ])
        records = TestTableManager.i.read("value == 'b'", None, "key asc")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["key"], "a")
        self.assertEqual(records[1]["key"], "c")
        records = TestTableManager.i.read("value == 'b'", None, "key desc")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["key"], "c")
        self.assertEqual(records[1]["key"], "a")

    def test_read_count(self):
        TestTableManager.i.create_many([
            {"key": "a", "value": "b"},
            {"key": "c", "value": "b"},
            {"key": "d", "value": "g"},
        ])
        records, count = TestTableManager.i.read_and_count(None, None, "key asc", 2, 0)
        self.assertEqual(len(records), 2)
        self.assertEqual(count, 3)
        self.assertEqual(records[0]["key"], "a")
        self.assertEqual(records[1]["key"], "c")
        records, count = TestTableManager.i.read_and_count(None, None, "key asc", 2, 1)
        self.assertEqual(len(records), 2)
        self.assertEqual(count, 3)
        self.assertEqual(records[0]["key"], "c")
        self.assertEqual(records[1]["key"], "d")

    def test_read_id(self):
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        record = TestTableManager.i.read_by_id(id, ["id", "key"])
        self.assertEqual(record["id"], id)
        self.assertEqual(record["key"], "a")
        self.assertEqual("value" in record, False)
        record = TestTableManager.i.read_by_id(id, ["key", "value"])
        self.assertEqual(record["key"], "a")
        self.assertEqual(record["value"], "b")
        self.assertEqual("id" in record, False)

    def test_read_in_order(self):
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        id2 = TestTableManager.i.create({"key": "c", "value": "d"})
        records = TestTableManager.i.read_many_by_id([id, id2])
        self.assertEqual([x["id"] for x in records], [id, id2])
        records = TestTableManager.i.read_many_by_id([id2, id])
        self.assertEqual([x["id"] for x in records], [id2, id])

    def test_read_no_id(self):
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.read_by_id(69)
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        id2 = TestTableManager.i.create({"key": "c", "value": "d"})
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.read_many_by_id([id, id2, 69])
    
    def test_update_id(self):
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        TestTableManager.i.update_by_id(id, {"value": "c"})
        record = TestTableManager.i.read_by_id(id)
        self.assertEqual(record["value"], "c")

    def test_update_no_id(self):
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.update_by_id(69, {"value": "x"})
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        id2 = TestTableManager.i.create({"key": "c", "value": "d"})
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.update_many_by_id([id, id2, 69], {"value": "x"})

    def test_delete_id(self):
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        TestTableManager.i.delete_by_id(id)
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.read_by_id(id)

    def test_delete_no_id(self):
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.delete_by_id(69)
        id = TestTableManager.i.create({"key": "a", "value": "b"})
        id2 = TestTableManager.i.create({"key": "c", "value": "d"})
        with self.assertRaises(table_manager.PersistenceException):
            TestTableManager.i.delete_many_by_id([id, id2, 69])

    def test_like(self):
        TestTableManager.i.create_many([
            {"key": "arkanoid", "value": "noid"},
            {"key": "pacman", "value": "pac"},
            {"key": "supergirl", "value": "ergi"},
        ])
        records = TestTableManager.i.read('key like ("%" + value)')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["key"], "arkanoid")
        records = TestTableManager.i.read('key like (value + "%")')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["key"], "pacman")
        records = TestTableManager.i.read('key like ("%" + value + "%")')
        self.assertEqual(len(records), 3)
