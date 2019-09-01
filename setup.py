#!/usr/bin/env python3
DOCLINES = (__doc__ or '').split("\n")

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='monopyly',
    version='0.1dev',
    description='My pet project for tracking finances.',
    author='Mitch Negus',
    author_email='mitchell.negus.17@gmail.com',
    license='GNU GPLv3',
    long_description='\n'.join(DOCLINES),
    url='',
    packages=['monopyly']
)
