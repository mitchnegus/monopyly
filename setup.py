#!/usr/bin/env python3
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='monopyly',
    version='1.0.0dev0',
    description='A homemade personal finance manager.',
    author='Mitch Negus',
    author_email='mitchnegus57@gmail.com',
    license='GNU GPLv3',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/mitchnegus/monopyly',
    download_url='https://pypi.org/project/monopyly',
    packages=['monopyly'],
    scripts=['scripts/monopyly', 'scripts/backup_db.py'],
    python_requires='>=3.7'
)
