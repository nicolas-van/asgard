#! /usr/bin/python
# -*- coding: utf-8 -*-

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

from setuptools import setup
import os.path

setup(name='asgard',
      version='0.1.0',
      description='asgard',
      author='Nicolas Vanhoren',
      author_email='nicolas.vanhoren@unknown.com',
      url='http://nowhere.com',
      py_modules = ['asgard'],
      packages=[],
      scripts=[],
      long_description="",
      keywords="",
      license="LGPL",
      classifiers=[
          ],
      install_requires=[
        'flask',
        'sqlalchemy',
        'pyparsing',
        'pylru',
        'bcrypt',
        'python-dateutil',
        'sjoh',
        ],
     )

