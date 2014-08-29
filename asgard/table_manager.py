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

import os.path
import sqlalchemy as sa
import sqlalchemy.sql as sql
import sqlalchemy.sql.expression
import werkzeug.local
import contextlib
import collections
from . import expression as expr
import re
import datetime

"""
The engine used to connect to the database.
"""
engine = None

def configure(configuration):
    global engine
    engine = sa.engine_from_config(configuration)

"""
The metadata object containing all the information about the db schema.
"""
metadata = sa.MetaData()

_conn_stack = werkzeug.local.LocalStack()

"""
A proxy to a connection object currently used to perform calls to the database.
"""
conn = _conn_stack()

@contextlib.contextmanager
def transaction():
    """
    A context manager that initializes a connection and store it in the ``conn`` proxy. When the operations
    terminate normally, the transaction is commited. If there is an exception, the transaction is rollbacked.
    """
    assert _conn_stack.top is None, "Only one connection can be opened at the same time"
    _conn_stack.push(engine.connect())
    try:
        conn.current_transaction = conn.begin()
        try:
            yield
            conn.current_transaction.commit()
        except:
            conn.current_transaction.rollback()
            raise
    finally:
        try:
            conn.close()
        except:
            pass
        _conn_stack.pop()

def transactional(func):
    """
    A decorator that will call ``transaction`` before the invocation of the function.
    """
    def alt(*args, **kwargs):
        with transaction():
            return func(*args, **kwargs)
    alt.__name__ = func.__name__
    alt.__module__ = func.__module__
    return alt

"""
An array where functions can be pushed to be called during the database initialization.
Those functions are ensured to be called during a transaction.
"""
data_initializers = []

class ManagersHandler(object):

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

app = ManagersHandler()

class PersistenceException(Exception):
    pass

class UnrecoverablePersistenceException(PersistenceException):
    """
        This is a type of exception that occurs when we attempted data modification but not all data
        could be modified correctly. When this exception occurs, it is mandatory to rollback the whole
        transaction or the database could contain inconsistencies.
    """
    pass

_order_regex = re.compile("^([a-zA-Z_][a-zA-Z_0-9]*(?:\.[a-zA-Z_][a-zA-Z_0-9]*)*)(?:\s+(asc|desc))?$")

class TableManager(object):
    table = None

    @property
    def table(self):
        return self.__class__.table

    def _expression(self, expression):
        """
            Converts any type of expression into a valid SqlAlchemy clause element which can be
            inserted into any query using the `where_clause()` method.
        """
        exp, values = _convert_expression(expression)
        if isinstance(exp, sqlalchemy.sql.expression.ClauseElement):
            return exp
        if exp is None:
            return sqlalchemy.sql.expression.literal(True)
        qbh = expr.QueryBuilderHelper(self.table)
        where_clause = qbh.where_clause(exp, values)
        subselect = sql.select([self.table.c.id]).select_from(qbh.from_clause())
        subselect = subselect.where(where_clause)
        return self.table.c.id.in_(subselect)

    def create(self, values=None):
        return self.create_many([values])[0]

    def create_many(self, values_list=None):
        """
        Create multiple records in the table using the given list of dictionaries.
        """
        assert isinstance(values_list, collections.Iterable), "Expected a list: %s" % values_list
        ins = self.table.insert()
        created = []
        for val in values_list:
            val = val or {}
            assert isinstance(val, dict), "Expected a dictionary: %s" % val
            if __debug__:
                for k in val.keys():
                    assert hasattr(self.table.c, k), "Table %s doesn't contain a column named %s" % (self.table, k)
            created.append(conn.execute(ins.values(**val)).inserted_primary_key[0])
        return created

    def read_by_id(self, id, fields=None):
        """
        Returns a dictionary containing the asked fields for the current table where the record is identified by
        the given id.

        If the id is not found in the table this method will raise a ``PersistenceException``.
        """
        assert id is not None, "id can not be None"
        return self.read_many_by_id([id], fields)[0]

    def read_many_by_id(self, ids, fields=None):
        """
        Returns a list of dictionaries containing the asked fields for the current table where records are identified by
        the given ids.

        The records will always be returned in the same order they were asked. If one id is not found in the table
        this method will raise a ``PersistenceException``.
        """
        assert isinstance(ids, collections.Iterable), "Expected a list: %s" % ids
        hasid = fields is None or "id" in fields
        res = self.read(self.table.c.id.in_(ids), fields if hasid else fields + ["id"])
        index = dict([(x["id"], x) for x in res])
        res = []
        for id in ids:
            if id not in index:
                raise PersistenceException("Id %s was not found in table %s" % (id, self.table.name))
            res.append(index[id])
        if not hasid:
            for el in res:
                del el["id"]
        return res

    def read(self, expression=None, fields=None, order=None, limit=None, offset=None):
        if fields is None:
            fields = self.table.c.keys()
        exp, values = _convert_expression(expression)

        qbh = expr.QueryBuilderHelper(self.table)
        # list of fields
        selectable = [qbh.column(k) for k in fields]
        # where clause
        where_clause = qbh.where_clause(exp, values)
        # orders
        order = order or []
        order = order if not isinstance(order, (sqlalchemy.sql.expression.ClauseElement, str, unicode)) else [order]
        order_bys = []
        for o in order:
            if isinstance(o, (str, unicode)):
                match = _order_regex.match(o)
                assert match is not None, "Not a valid order specifier: %s" % o
                o = qbh.column(match.group(1))
                o = o.asc() if match.group(2) != "desc" else o.desc()
            order_bys.append(o)
        # query
        query = sql.select(selectable)
        query = query.select_from(qbh.from_clause())
        if where_clause is not None:
            query = query.where(where_clause)
        for o in order_bys:
            query = query.order_by(o)
        # limit & offeset
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        # execution
        res = conn.execute(query)
        # convertion to dict
        lst = []
        for el in res:
            dct = {}
            for i in range(len(fields)):
                dct[fields[i]] = el[selectable[i]]
            lst.append(dct)
        return lst

    def count(self, expression=None):
        exp, values = _convert_expression(expression)
        qbh = expr.QueryBuilderHelper(self.table)
        where_clause = qbh.where_clause(exp, values)
        query = sql.select([sql.func.count(self.table.c.id)])
        if where_clause is not None:
            query = query.where(where_clause)
        res = conn.execute(query).fetchone()[0]
        return res

    def read_and_count(self, expression=None, fields=None, order=None, limit=None, offset=None):
        count = self.count(expression)
        res = self.read(expression, fields, order, limit, offset)
        return [res, count]

    def update_by_id(self, id, values):
        self.update_many_by_id([id], values)

    def update_many_by_id(self, ids, values):
        assert isinstance(ids, collections.Iterable), "Expected a list: %s" % ids
        rowcount = self.update(self.table.c.id.in_(ids), values)
        if rowcount != len(ids):
            raise UnrecoverablePersistenceException("One or more ids where not found while updating table %s", self.table.name)

    def update(self, expression=None, values=None):
        values = values or {}
        assert isinstance(values, dict), "Expected a dictionary: %s" % values
        if __debug__:
            for k in values.keys():
                assert hasattr(self.table.c, k), "Table %s doesn't contain a column named %s" % (self.table, k)
        query = self.table.update()
        query = query.where(self._expression(expression))
        query = query.values(values)
        rowcount = conn.execute(query).rowcount
        return rowcount

    def delete_by_id(self, id):
        self.delete_many_by_id([id])

    def delete_many_by_id(self, ids):
        assert isinstance(ids, collections.Iterable), "Expected a list: %s" % ids
        rowcount = self.delete(self.table.c.id.in_(ids))
        if rowcount != len(ids):
            raise UnrecoverablePersistenceException("One or more ids where not found while deleting rows in table %s", self.table.name)

    def delete(self, expression=None):
        query = self.table.delete()
        query = query.where(self._expression(expression))
        rowcount = conn.execute(query).rowcount
        return rowcount

def _convert_expression(expression):
    if isinstance(expression, sqlalchemy.sql.expression.ClauseElement):
        return expression, {}
    if isinstance(expression, (str, unicode, type(None))):
        return expression, {}
    else:
        assert isinstance(expression, collections.Iterable), "Expected a list: %s" % expression
        assert len(expression) == 2, "Expected a list of 2 elements: %s" % expression
        return expression

def table_manager(table):
    """
    A function creating a class binded to a specific SqlAlchemy table. That class will contain generic methods to ease
    manipulation of that table.
    """
    assert table is not None, "Must provide a table"
    assert hasattr(table.c, "id"), "Table %s must contain a field named id" % table
    assert isinstance(table.c.id.type, sa.Integer), "Field id in table %s must be an integer" % table
    assert table.c.id.primary_key, "Field id in table %s must be a primary key" % table

    ttable = table
    class BindedTableManager(TableManager):
        table = ttable

    return BindedTableManager

class StateTableManager(TableManager):
    def __init__(self, *args, **kwargs):
        super(StateTableManager, self).__init__(*args, **kwargs)
        table = self.table
        assert hasattr(table.c, "state"), "Table %s must contain a field named state" % table
        assert isinstance(table.c.state.type, sa.Enum), "Field state in table %s must be an enumeration" % table
        assert table.c.state.nullable == False, "Field state in table %s must be non-nullable" % table
        if hasattr(self.table.c, "last_state_change"):
            assert isinstance(table.c.last_state_change.type, sa.DateTime), "Field last_state_change in table %s must be a datetime" % table
            self._has_state_change = True
        else:
            self._has_state_change = False

    def change_state_by_id(self, id, old_state, new_state, other_values=None):
        return self.change_state_many_by_id([id], old_state, new_state, other_values)

    def change_state_many_by_id(self, ids, old_state, new_state, other_values=None):
        assert isinstance(ids, collections.Iterable), "Expected a list: %s" % ids
        rowcount = self.change_state(self.table.c.id.in_(ids), old_state, new_state, other_values)
        if rowcount != len(ids):
            raise UnrecoverablePersistenceException("One or more ids where not found while updating table %s", self.table.name)

    def change_state(self, expression, old_state, new_state, other_values=None):
        other_values = other_values or {}
        clause = sqlalchemy.sql.expression.and_(self._expression(expression), self.table.c.state == old_state)
        values = {
            "state": new_state,
        }
        if self._has_state_change:
            values["last_state_change"] = datetime.datetime.now()
        return self.update(clause, dict(other_values, **values))
