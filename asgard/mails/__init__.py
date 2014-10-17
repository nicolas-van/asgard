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

import asgard
import mailflash
import os.path
import jinja2

class MailsPlugin(asgard.Plugin):

    config_key = "mails"
    dependencies = []

    def __init__(self, app):
        self.app = app
        self.mail = mailflash.Mail()
        self.template_folder = "email_templates"
        self._jinja_env = None

    def configure(self, config):
        if "template_folder" in config:
            self.template_folder = config["template_folder"]
            del config["template_folder"]
        self.mail.init_from_dict(config)

    @property
    def jinja_env(self):
        if self._jinja_env is None:
            self._jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
                os.path.join(self.app.root_path, self.template_folder)))
        return self._jinja_env

    def build_message(self,
                template,
                template_params=None,
                subject=None,
                recipients=None,
                sender=None,
                cc=None,
                bcc=None,
                attachments=None,
                reply_to=None,
                date=None,
                charset=None,
                extra_headers=None,
                mail_options=None,
                rcpt_options=None):
        """Creates a message by rendering a template.

        :param template: Name of the jinja2 template.
        :param template_params: Parameters of the template (dictionary).
        :param subject: email subject header
        :param recipients: list of email addresses
        :param body: plain text message
        :param html: HTML message
        :param sender: email sender address, or **MAIL_DEFAULT_SENDER** by default
        :param cc: CC list
        :param bcc: BCC list
        :param attachments: list of Attachment instances
        :param reply_to: reply-to address
        :param date: send date
        :param charset: message character set
        :param extra_headers: A dictionary of additional headers for the message
        :param mail_options: A list of ESMTP options to be used in MAIL FROM command
        :param rcpt_options:  A list of ESMTP options to be used in RCPT commands
        """
        template_params = template_params or {}
        rendered = self.jinja_env.get_template(template).render(**template_params)
        return mailflash.Message(subject, recipients, None, rendered, sender, cc, bcc, attachments,
            reply_to, date, charset, extra_headers, mail_options, rcpt_options)

    def send_message(self, message):
        """Sends a mailflash.Message object."""
        self.mail.send(message)

    def send_mail(self, *args, **kwargs):
        message = self.build_message(*args, **kwargs)
        self.send_message(message)
