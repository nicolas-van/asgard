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

print("yop")

import unittest

import sqlalchemy as sa
import asgard.expression as expression
import sqlalchemy.sql.expression as saexpr
import sqlalchemy.sql as sql

class ExpressionsParserTest(unittest.TestCase):

    def test_identifier(self):
        result = expression._parser.parseString("test")[0]
        self.assertEqual(result, ("identifier", "test"))

    def test_identifier_complex(self):
        result = expression._parser.parseString("test . x . y")[0]
        self.assertEqual(result, ("identifier", "test.x.y"))

    def test_variable(self):
        result = expression._parser.parseString(":test")[0]
        self.assertEqual(result, ("variable", "test"))

    def test_boolean(self):
        result = expression._parser.parseString("true")[0]
        self.assertEqual(result, ("literal", True))
        result = expression._parser.parseString("false")[0]
        self.assertEqual(result, ("literal", False))

    def test_integer(self):
        result = expression._parser.parseString("5")[0]
        self.assertEqual(result, ("literal", 5))

    def test_float(self):
        result = expression._parser.parseString("5.")[0]
        self.assertEqual(result, ("literal", 5.))
        result = expression._parser.parseString("5.2")[0]
        self.assertEqual(result, ("literal", 5.2))

    def test_string(self):
        result = expression._parser.parseString("'test'")[0]
        self.assertEqual(result, ("literal", 'test'))
        result = expression._parser.parseString('"test"')[0]
        self.assertEqual(result, ("literal", 'test'))

    def test_null(self):
        result = expression._parser.parseString("null")[0]
        self.assertEqual(result, ("literal", expression._none_val))

    def test_list(self):
        result = expression._parser.parseString("[1, 2]")[0]
        self.assertEqual(result, ("list", [("literal", 1), ("literal", 2)]))

    def _test_op2(self, op):
        result = expression._parser.parseString("1 %s 2" % op)[0]
        self.assertEqual(result, ("op2", op, ("literal", 1), ("literal", 2)))

    def test_or(self):
        self._test_op2("or")

    def test_and(self):
        self._test_op2("and")

    def test_eq(self):
        self._test_op2("==")

    def test_ne(self):
        self._test_op2("!=")

    def test_in(self):
        self._test_op2("in")

    def test_like(self):
        self._test_op2("like")

    def test_ilike(self):
        self._test_op2("ilike")

    def test_gt(self):
        self._test_op2(">")

    def test_lt(self):
        self._test_op2("<")

    def test_ge(self):
        self._test_op2(">=")

    def test_le(self):
        self._test_op2("<=")

    def test_plus(self):
        self._test_op2("+")

    def test_minus(self):
        self._test_op2("-")

    def test_mult(self):
        self._test_op2("*")

    def test_div(self):
        self._test_op2("/")

    def test_mod(self):
        self._test_op2("%")

    def test_op1(self):
        result = expression._parser.parseString("+1")[0]
        self.assertEqual(result, ("op1", "+", ("literal", 1)))
        result = expression._parser.parseString("-1")[0]
        self.assertEqual(result, ("op1", "-", ("literal", 1)))
        result = expression._parser.parseString("not 1")[0]
        self.assertEqual(result, ("op1", "not", ("literal", 1)))

    def test_precedence(self):
        result = expression._parser.parseString("1 + 2 * 3")[0]
        self.assertEqual(result, ("op2", "+", ("literal", 1), ("op2", "*", ("literal", 2), ("literal", 3))))
        result = expression._parser.parseString("(1 + 2) * 3")[0]
        self.assertEqual(result, ("op2", "*", ("op2", "+", ("literal", 1), ("literal", 2)), ("literal", 3)))

    def test_multi_operator(self):
        result = expression._parser.parseString("'%' + value + '%'")[0]
        self.assertEqual(result, ("op2", "+", ("op2", "+", ("literal", "%"), ("identifier", "value")), ("literal", "%")))

metadata = sa.MetaData()

test_table2 = sa.Table('test_table2', metadata,
   sa.Column('id', sa.Integer, primary_key=True),
   sa.Column('key', sa.String(50), unique=True),
   sa.Column('value', sa.String(50)),
)

test_table3 = sa.Table('test_table3', metadata,
   sa.Column('id', sa.Integer, primary_key=True),
   sa.Column('key', sa.String(50), unique=True),
   sa.Column('table2', None, sa.ForeignKey("test_table2.id")),
)

class ExpressionEvaluatorTest(unittest.TestCase):

    def test_identifier(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("key")
        self.assertEqual(str(result), str(test_table2.c.key))
    
    def test_boolean(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("true")
        self.assertEqual(str(result), str(saexpr.literal(True)))
        result = expression.QueryBuilderHelper(test_table2).where_clause("false")
        self.assertEqual(str(result), str(saexpr.literal(False)))

    def test_integer(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("5")
        self.assertEqual(str(result), str(saexpr.literal(5)))

    def test_float(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("5.")
        self.assertEqual(str(result), str(saexpr.literal(5.)))
        result = expression.QueryBuilderHelper(test_table2).where_clause("5.2")
        self.assertEqual(str(result), str(saexpr.literal(5.2)))

    def test_string(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("'test'")
        self.assertEqual(str(result), str(saexpr.literal("test")))
        result = expression.QueryBuilderHelper(test_table2).where_clause('"test"')
        self.assertEqual(str(result), str(saexpr.literal("test")))

    def test_null(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("null")
        self.assertEqual(str(result), str(saexpr.literal(None)))

    def test_list(self):
        result = expression.QueryBuilderHelper(test_table2).where_clause("[1, 2]")
        self.assertEqual(str(result), str(saexpr.literal([1, 2])))

    def _test_op2(self, op):
        operation = "2. %s 2." % op
        result = expression.QueryBuilderHelper(test_table2).where_clause(operation)
        self.assertEqual(str(result), str(saexpr.literal(eval(operation))))

    def test_eq(self):
        self._test_op2("==")

    def test_ne(self):
        self._test_op2("!=")

    def test_gt(self):
        self._test_op2(">")

    def test_lt(self):
        self._test_op2("<")

    def test_ge(self):
        self._test_op2(">=")

    def test_le(self):
        self._test_op2("<=")

    def test_plus(self):
        self._test_op2("+")

    def test_minus(self):
        self._test_op2("-")

    def test_mult(self):
        self._test_op2("*")

    def test_div(self):
        self._test_op2("/")

    def test_mod(self):
        self._test_op2("%")
    
    def test_foreign_key(self):
        qbh = expression.QueryBuilderHelper(test_table3)
        qbh.column("table2.key")
        result = qbh.from_clause()
        alias_table2 = test_table2.alias()
        query = test_table3.outerjoin(alias_table2)
        self.assertEqual(str(result), str(query))
    
    """
    # only to test performances
    def test_speed(self):
        expressions = []
        for i in range(500):
            expressions.append("id == %s and (key != true or value in ['yes', 'no', 'maybe'])" % i)
        self.ee.set_cache_size(500)
        for i in range(10):
            for req in expressions:
                self.ee.embedded_where_clause(test_table2, req)
        import pudb; pudb.set_trace()
        self.assertTrue(True)
    """
    """
    def test_speed2(self):
        exp = " and ".join(["(id == 2)" for x in range(100)])
        exp = " and ".join(["(%s)" % exp for x in range(10)])
        print("lenght", len(exp))
        self.ee.embedded_where_clause(test_table2, exp)
        self.assertTrue(True)
    """

