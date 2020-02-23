#!/usr/bin/env python
from __future__ import print_function

import io
from setuptools import find_packages, setup

with io.open('README.rst', encoding='utf-8') as readme:
    description = readme.read()

with open('requirements.txt') as req:
    requirements = [line.strip() for line in req.readlines() if line.strip() and not line.strip().startswith('#')]


setup(
    name='drf-yasg-json-api',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    extras_require={},
    license='BSD License',
    description='Automated generation of real Swagger/OpenAPI 2.0 schemas for JSON API Django Rest Framework '
                'endpoints.',
    long_description=description,
    url='https://github.com/name/drf-yasg-json-api',
    author='',
    author_email='',
    keywords='drf django django-rest-framework schema swagger openapi codegen swagger-codegen '
             'documentation drf-yasg django-rest-swagger drf-openapi json-api',
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Topic :: Documentation',
        'Topic :: Software Development :: Code Generators',
    ],
)
