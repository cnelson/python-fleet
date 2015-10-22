from setuptools import setup, find_packages

setup(
    name='fleet',

    version='0.1.3',

    description='A python client for the fleet v1 API',

    url='https://github.com/cnelson/python-fleet',

    author='Chris Nelson',
    author_email='cnelson@cnelson.org',

    license='Apache License (2.0)',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Distributed Computing',

        'Intended Audience :: Developers',

        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    keywords='coreos fleet v1 api client',

    packages=find_packages(),

    install_requires=[
        'google-api-python-client>=1.4.2',
        'paramiko>=1.15.1',
        'mock',
        'argparse'
    ],

    test_suite='fleet.v1.tests'

)
