#!/usr/bin/python
import sys
from setuptools import setup

needs_pytest = set(['pytest', 'test']).intersection(sys.argv)
pytest_runner = ['pytest_runner>=2.1'] if needs_pytest else []

setup(
    name='sseclient',
    version='0.0.15',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    py_modules=['sseclient'],
    install_requires=['requests>=2.0.0', 'six'],
    tests_require=['pytest', 'backports.unittest_mock'],
    setup_requires=[] + pytest_runner,
    description=(
        'Python client library for reading Server Sent Event streams.'),
    long_description=open('README.rst').read(),
    url='https://github.com/btubbs/sseclient',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
)
