#!/usr/bin/env python3
import os
from setuptools import setup, find_packages


# Set the package version
MAJOR = 1
MINOR = 2
PATCH = 0
DEV = 0

def name_version(major, minor, patch, dev):
    version_number = f'{MAJOR}.{MINOR}.{PATCH}'
    suffix = f'.dev{dev}' if dev else ''
    return version_number + suffix


def convert_markdown(raw_markdown, github_user, github_repo):
    """Convert images in a string of raw markdown to display on PyPI."""
    url = 'https://raw.githubusercontent.com'
    repo_raw_content_url = f'{url}/{github_user}/{github_repo}/master/'
    markdown = raw_markdown.replace('src="', f'src="{repo_raw_content_url}')
    return markdown


raw_long_description = open('README.md').read()
long_description = convert_markdown(
    raw_long_description,
    "mitchnegus",
    "monopyly",
)

metadata = dict(
    name='monopyly',
    version=name_version(MAJOR, MINOR, PATCH, DEV),
    description='A homemade personal finance manager.',
    author='Mitch Negus',
    author_email='mitchnegus57@gmail.com',
    license='GNU GPLv3',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/mitchnegus/monopyly',
    download_url='https://pypi.org/project/monopyly',
    packages=find_packages(),
    include_package_data=True,
    package_data = {
        "": ["database/*.sql"]
    },
    scripts=[
        "scripts/monopyly",
        "scripts/backup_db.py",
    ],
    python_requires=">=3.9",
    install_requires=[
        "flask>=2.2.2",
        "flask-wtf",
        "python-dateutil",
        "sqlalchemy>=2.0.0",
    ],
)


if __name__ == '__main__':
    setup(**metadata)

