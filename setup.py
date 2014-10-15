#! /usr/bin/python
# -*- coding: utf-8 -*-

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

from setuptools import setup
import os.path

setup(name='asgard',
      version='0.5.0',
      description='asgard',
      author='Nicolas Vanhoren',
      author_email='nicolas.vanhoren@unknown.com',
      url='http://nowhere.com',
      py_modules = [],
      packages=["asgard", "asgard.users", "asgard.mails"],
      scripts=[],
      long_description="",
      keywords="",
      license="MIT",
      classifiers=[
          ],
      install_requires=[
        'werkzeug>=0.9.6',
        'flask',
        'sqlalchemy',
        'pyparsing',
        'pylru',
        'python-dateutil',
        'sjoh',
        'mailflash==0.1.0',
        ],
      extras_require={
        "bcrypt": ["bcrypt"],
      },
      tests_require=[
        "bcrypt",
      ],
     )

