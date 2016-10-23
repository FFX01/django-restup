from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'readme.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='django-restup',

    version='0.1.0',

    description='A Library for creating REST APIs fro Django applications',
    long_description=long_description,

    url='https://github.com/FFX01/django-restup',

    author='Justin Walters',
    author_email='walters.justin01@gmail.com',

    license='BSD',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Database :: Front-Ends'
    ],

    keywords='django rest api',

    packages=find_packages(),

    install_requires=[
        'django>=1.8'
    ]
)