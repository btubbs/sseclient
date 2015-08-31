#!/usr/bin/python
import sys
from setuptools import setup

needs_pytest = {'pytest', 'test'}.intersection(sys.argv)
pytest_runner = ['pytest_runner>=2.1'] if needs_pytest else []

setup(
    name='sseclient',
    version='0.0.9',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    py_modules=['sseclient'],
    install_requires=['requests>=2.0.0', 'six'],
    tests_require=['pytest', 'mock'],
    setup_requires=[] + pytest_runner,
    description=(
        'Python client library for reading Server Sent Event streams.'),
    long_description=open('README.rst').read(),
    url='https://bitbucket.org/btubbs/sseclient/',
)
