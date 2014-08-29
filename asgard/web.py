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

import sjoh.flask
import flask

COOKIE_DURATION = 3 * 7 * 34 * 60 * 60 # 3 weeks

class WebApp(flask.Flask):
    def __init__(self, app, import_name, **kwargs):
        self.app = app
        self.sjoh = sjoh.flask.SjohFlask(self)

        super(WebApp, self).__init__(import_name, **kwargs)

    def full_dispatch_request(self, *args, **kw):
        with self.app:
            sid = flask.request.cookies.get('sid')
            with self.app.declare_session(sid):
                response = super(WebApp, self).full_dispatch_request(*args, **kw)
                response.set_cookie('sid', self.app.session.sid, COOKIE_DURATION)
            return response

    def add_url_rule(self, rule, endpoint=None, view_func=None, *args, **kwargs):
        no_transaction = kwargs.get("no_transaction", False)
        if "no_transaction" in kwargs: del kwargs["no_transaction"]
        trans_func = self.app.transactional(view_func) if not no_transaction else view_func
        trans_func.__name__ = view_func.__name__
        trans_func.__module__ = view_func.__module__

        return super(WebApp, self).add_url_rule(rule, endpoint, trans_func, *args, **kwargs)

    def add_url_rule_for_json(self, rule, endpoint=None, view_func=None, *args, **kwargs):
        no_transaction = kwargs.get("no_transaction", False)
        if "no_transaction" in kwargs: del kwargs["no_transaction"]
        trans_func = self.app.transactional(view_func) if not no_transaction else view_func
        return self.sjoh.add_url_rule_for_json(rule, endpoint, trans_func, *args, no_transaction=True, **kwargs)

    def json(self, rule, **options):
        def decorator(f):
            endpoint = options.pop('endpoint', None)
            self.add_url_rule_for_json(rule, endpoint, f, **options)
            return f
        return decorator

