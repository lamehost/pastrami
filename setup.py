import codecs
import uuid

from os.path import abspath, dirname, join
from setuptools import setup, find_packages
try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip < 10
    from pip.req import parse_requirements

import pastrami as this_package



def get_long_description():
    here = abspath(dirname(__file__))
    with codecs.open(join(here, 'README.md'), encoding='utf-8') as readme:
        return readme.read()

def get_requirements():
    install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
    return [str(ir.req) for ir in install_reqs]


setup(
    name=this_package.__name__,
    author=this_package.__author__,
    author_email=this_package.__author_email__,
    url=this_package.__url__,
    version=this_package.__version__,
    packages=find_packages(),
    package_data={this_package.__name__: [
        'html/*'
    ]},
    install_requires=get_requirements(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            '%s = %s.cli:main' % (this_package.__name__, this_package.__name__),
        ],
    },
    long_description=get_long_description(),
    zip_safe=True
)
