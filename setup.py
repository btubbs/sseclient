#!/usr/bin/python
from setuptools import setup

setup(
    name='sseclient',
    version='0.0.2',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    py_modules=['sseclient'],
    install_requires=['requests==0.14.2'],
    description=(
        'Python client library for reading Server Sent Event streams.'),
    long_description=open('README.rst').read(),
    url='http://bits.btubbs.com/sseclient',
)
