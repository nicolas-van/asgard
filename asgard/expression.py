# Copyright (c) 2014, Nicolas Vanhoren
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
SAQL
====

A small domain-specific language to create expressions representing SQL where-clauses. Those expressions
will be compiled into SQLAlchemy objects.

The goal is to allow arbitrary clients interrogating a server to specify filters when searching a table.
These expressions are language agnostic (they are just strings) and are sufficiently restrictive to be considered
safe even if they were generated by an unsafe environment.

Documentation of the SAQL Language
----------------------------------

SAQL is *not* SQL. It has characteristics coming from SQL, JavaScript and Python. Example expression:

::
    name like "%Smith%" and account != null and status in ["married", "single"]

Simple Types
~~~~~~~~~~~~

* Integers: ``1``, ``2``, ``3``
* Floats: ``1.2``, ``3.4``, ``5.``
* Strings: ``"some string"``, ``'some other string'``. Both simple and double quotes are considered valid.
* Booleans: ``true``, ``false``
* Null: ``null``

Column Names
~~~~~~~~~~~~

Just specify the name of the column, like ``my_column``.

Variables
~~~~~~~~~~~~

You can specify variables to be inserted by the evaluator. Example:

::
    credit > :min_value

If the evaluator is given the integer ``100`` for ``min_value``, the resulting expression will be ``credit > 100``.
Please note that the evaluator will take care of the escaping of the variables it is given. So here we should
give an integer to it. If we give it the value ``"100"`` (as a string), the resulting expression will be
``credit > "100"`` which will probably result in a invalid expression if those types are not comparable.

Variables are the recommended way to pass values coming from forms or similar stuff. They also are the only way to
specify values for dates and datetimes, as there is no way currently to specify those using the SAQL syntax.

Lists
~~~~~

Lists use the ``[`` and ``]`` delimiters.

::
    [1, 2, 3]

They are mostly used in conjonction with the ``in`` operator.

Operators
~~~~~~~~~

Here is a list of the supported binary operators: or, and, ==, !=, in, like, ilike, <=, >=, <, >, +, -, *, / and %.

Additionaly, ``not`` is supported as an unary operators as well as + and -.

Please note that, contrary to SQL, operators like ``not in`` or ``not like`` are not supported. Instead, you should
use the ``not`` operator in front of the condition to inverse. Example:

::
    not (status in ["married", "single"])

"""

from __future__ import unicode_literals, print_function, absolute_import

import sqlalchemy as sa
import sqlalchemy.sql as sql
import sqlalchemy.sql.expression as expr
import operator
from pyparsing import *
import ast
import pylru

CACHE_SIZE = 200

class _NoneVal(object):
    pass

_none_val = _NoneVal()

def _define_parser():
    ParserElement.enablePackrat()

    identifier_part = Word(alphas + "_", alphanums + "_")
    identifier = delimitedList(identifier_part, ".").setParseAction(lambda x: ('identifier', ".".join(x)))

    variable = Combine(":" + Word(alphas + "_", alphanums + "_")).setParseAction(lambda x: ('variable', x[0][1:]))

    boolean_literal = (Keyword("true") | Keyword("false")).setParseAction(lambda x: x[0] == "true")
    integer_literal = Word(nums).setParseAction(lambda x: int(x[0]))
    float_literal = Combine(Word(nums) + "." + Optional(Word(nums))).setParseAction(lambda x: float(x[0]))
    string_literal = quotedString.setParseAction(lambda x: ast.literal_eval(x[0]))
    null_literal = Keyword("null").setParseAction(lambda x: _none_val)

    literal = (boolean_literal | string_literal | float_literal | integer_literal | null_literal).setParseAction(lambda x: ('literal', x[0]))

    logical_or = Keyword("or")
    logical_and = Keyword("and")
    equality = Literal("==") | Literal("!=") | Keyword("in") | Keyword("like") | Keyword("ilike")
    relational = Literal("<=") | Literal(">=") | Literal("<") | Literal(">")
    additive = Literal("+") | Literal("-")
    mult = Literal("*") | Literal("/") | Literal("%")
    non = Keyword("not")

    expression = Forward()

    # can we put a trailing comma?
    list_expr = ("[" + delimitedList(expression) + "]").setParseAction(lambda x: ('list', x[1:-1]))

    rvalue = literal | identifier | variable | list_expr

    def op1_action(x):
        x = x[0]
        assert len(x) == 2
        return ('op1', x[0], x[1])

    def op2_action(x):
        x = x[0]
        if len(x) == 1:
            return x
        return op2_action([[('op2', x[1], x[0], x[2])] + x[3:]])

    expression << operatorPrecedence(rvalue, [
            (additive, 1, opAssoc.RIGHT, op1_action),
            (non, 1, opAssoc.RIGHT, op1_action),
            (mult, 2, opAssoc.LEFT, op2_action),
            (additive, 2, opAssoc.LEFT, op2_action),
            (relational, 2, opAssoc.LEFT, op2_action),
            (equality, 2, opAssoc.LEFT, op2_action),
            (logical_and, 2, opAssoc.LEFT, op2_action),
            (logical_or, 2, opAssoc.LEFT, op2_action),
        ])

    program = expression + stringEnd

    return program

_parser = _define_parser()

def _in(elem1, elem2):
    assert isinstance(elem1, expr.ColumnElement), "Invalid left operand for 'in' operator: %s" % elem1
    return elem1.in_(elem2)

def _like(elem1, elem2):
    assert isinstance(elem1, expr.ColumnElement), "Invalid left operand for 'like' operator: %s" % elem1
    return elem1.like(elem2)

def _ilike(elem1, elem2):
    assert isinstance(elem1, expr.ColumnElement), "Invalid left operand for 'ilike' operator: %s" % elem1
    return elem1.ilike(elem2)

_operators = {
    "or": expr.or_,
    "and": expr.and_,
    "==": operator.eq,
    "!=": operator.ne,
    "in": _in,
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.div,
    "%": operator.mod,
    "like": _like,
    "ilike": _ilike,
}

_cache = pylru.lrucache(CACHE_SIZE)

def _compile(expression):
    try:
        return _cache[expression]
    except KeyError:
        pass
    tree = _parser.parseString(expression)[0]
    _cache[expression] = tree
    return tree

class QueryBuilderHelper(object):
    def __init__(self, table):
        """
        :param name: The SqlAlchemy Metadata object.
        :param cache_size: The size of the cache to store compilation results. Can be deactivated by using ``0``.
        """
        assert hasattr(table.c, "id"), "Table %s must contain a column named id" % table
        self.table = table
        self.fk_columns = {}

    def where_clause(self, expression, values=None):
        values = values or {}
        if isinstance(expression, expr.ClauseElement):
            return expression
        elif expression is None:
            return None
        tree = _compile(expression)
        where_clause = self._walk(values, tree)
        if not isinstance(where_clause, expr.ClauseElement):
            where_clause = expr.literal(where_clause)
        return where_clause

    def _walk(self, values, elem):
        kind = elem[0]
        val = elem[1:]
        if kind == "identifier":
            return self.column(val[0])
        elif kind == "variable":
            return values[val[0]]
        elif kind == "literal":
            return val[0] if val[0] != _none_val else None
        elif kind == "list":
            nlist = []
            for el in val[0]:
                nlist.append(self._walk(values, el))
            return nlist
        elif kind == "op1":
            return self._op1(values, *val)
        elif kind == "op2":
            return self._op2(values, *val)
        assert False, "should not happen"

    def column(self, val):
        vals = val.split(".")
        return self._column_walk(self, vals)

    def _column_walk(self, current, vals):
        table = current.table
        column_name = vals[0]
        assert hasattr(table.c, column_name), "Table %s doesn't contain a column named %s" % (table, column_name)
        if len(vals) == 1:
            return getattr(table.c, column_name)
        fk_columns = current.fk_columns
        if column_name not in fk_columns:
            col = getattr(table.c, column_name)
            assert len(col.foreign_keys) > 0, "Column %s is not a foreign key" % col
            assert len(col.foreign_keys) < 2, "Column %s has multiple foreign keys attached to it, this is not supported" % col
            other_column = list(col.foreign_keys)[0].column
            other_table = other_column.table
            assert other_column is other_table.c.id, "Column %s in table %s must reference the column id in table %s" % (col, table, other_table)
            table_alias = other_table.alias()
            fk_columns[column_name] = _JoinPart()
            fk_columns[column_name].table = table_alias
            fk_columns[column_name].fk_columns = {}
        # an assertion to inform about an easy-to-avoid bug, it could be a good idea to fix this one day or later
        assert vals[1] != "id", "Querying the id of a row through a foreign key is not supported, use the foreign key instead"
        return self._column_walk(fk_columns[column_name], vals[1:])

    def from_clause(self):
        return self._walk_tables(self.table, self)

    def _walk_tables(self, current_from, ctx):
        foreign_keys = sorted(ctx.fk_columns.keys())
        for fk in foreign_keys:
            fkctx = ctx.fk_columns[fk]
            current_from = current_from.outerjoin(fkctx.table, fkctx.table.c.id == getattr(ctx.table.c, fk))
            current_from = self._walk_tables(current_from, fkctx)
        return current_from

    def _op1(self, values, op, elem):
        elem = self._walk(values, elem)
        if op == "+":
            return + elem
        elif op == "-":
            return - elem
        elif op == "not":
            return expr.not_(elem)
        assert False, "should not happen"

    def _op2(self, values, op, elem1, elem2):
        elem1 = self._walk(values, elem1)
        elem2 = self._walk(values, elem2)
        assert op in _operators.keys(), "Unsupported operator: %s" % op
        return _operators[op](elem1, elem2)

class _JoinPart(object):
    pass
