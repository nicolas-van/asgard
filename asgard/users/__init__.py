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

import sqlalchemy as sa
import datetime
import re
import asgard
import werkzeug.security


class UsersPlugin(asgard.Plugin):

    config_key = "users"
    dependencies = []

    def __init__(self, app):
        plugin = self
        self.app = app
        self.config = {
            "preferred_encryption" : "werkzeug",
            "bcrypt_turns" : 10,
            "werkzeug_method" : "pbkdf2:sha512:10000",
        }
        self.users = sa.Table('users', app.metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('email', sa.String(50), nullable=True, unique=True),
            sa.Column('password_hash', sa.String(200), nullable=False),
            sa.Column('creation_date', sa.DateTime(), nullable=False, default=datetime.datetime.now),
        )

        @app.manager
        class UsersManager(asgard.table_manager(self.users)):

            def _encode_password(self, password):
                password = unicode(password)
                if plugin.config["preferred_encryption"] == "bcrypt":
                    import bcrypt
                    password = password.encode("utf8")
                    phash = bcrypt.hashpw(password, bcrypt.gensalt(plugin.config["bcrypt_turns"]))
                    return "bcrypt:://" + phash
                elif plugin.config["preferred_encryption"] == "werkzeug":
                    return "werkzeug:://" + werkzeug.security.generate_password_hash(password, plugin.config["werkzeug_method"])
                else:
                    raise ValueError("unknown encryption")

            def _check_password(self, password, to_compare):
                password = unicode(password)
                found = re.match("^(\w+)\:\:\/\/(.*)$", to_compare)
                if found.group(1) == "bcrypt":
                    import bcrypt
                    password = password.encode("utf8")
                    phash = unicode(found.group(2)).encode("utf8")
                    if bcrypt.hashpw(password, phash) == phash:
                        return True
                    else:
                        return False
                if found.group(1) == "werkzeug":
                    return werkzeug.security.check_password_hash(found.group(2), password)
                else:
                    raise ValueError("unknown encryption")

            def create_user(self, email, password):
                hash_ = self._encode_password(password)
                return self.create({"email": email, "password_hash": hash_})

            def set_password(self, user_id, password):
                hash_ = self._encode_password(password)
                updated = self.update_by_id(user_id, {"password_hash": hash_})
                return updated

            def test_user(self, email, password):
                try:
                    hash_ = self.read_by_email(email, ["password_hash"])["password_hash"]
                except asgard.PersistenceException:
                    return False
                return self._check_password(password, hash_)

            def read_by_email(self, email, fields=None):
                users = self.read(["email == :email", {"email": email}], fields)
                if len(users) == 0:
                    raise asgard.PersistenceException("Unknown email: %s" % email)
                return users[0]

        self.UsersManager = UsersManager

    def configure(self, config):
        self.config.update(config)
