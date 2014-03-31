#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

from setuptools import setup, find_packages

setup(
    name='gofer',
    version='1.0.4',
    description='Universal python agent',
    author='Jeff Ortel',
    author_email='jortel@redhat.com',
    url='https://github.com/jortel/gofer',
    license='GPLv2+',
    packages=find_packages(),
    scripts=[
        '../bin/goferd',
    ],
    include_package_data=False,
    data_files=[],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python',
        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Distributed Computing',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
    ],
    install_requires=[
    ],
)

