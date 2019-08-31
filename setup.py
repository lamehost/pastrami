import codecs

from os.path import abspath, dirname, join
from setuptools import setup

NAME = 'pastrami'
HERE = abspath(dirname(__file__))

ABOUT = dict()
with open(join(NAME, '__about__.py')) as _:
    exec(_.read(), ABOUT)

HERE = abspath(dirname(__file__))
with codecs.open(join(HERE, 'README.md'), encoding='utf-8') as _:
    README = _.read()

with open('requirements.txt') as file:
    REQS = [line.strip() for line in file if line and not line.startswith("#")]

setup(
    name=NAME,
    author=ABOUT['__author__'],
    author_email=ABOUT['__author_email__'],
    url=ABOUT['__url__'],
    version=ABOUT['__version__'],
    packages=[NAME],
    package_data={NAME: [
        '*.yml'
    ]},
    install_requires=REQS,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            '%s = %s.__main__:main' % (NAME, NAME),
        ],
    },
    long_description=README,
    zip_safe=False
)
