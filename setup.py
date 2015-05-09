# Don't force people to install distribute unless we have to.
try:
    from setuptools import setup, Feature
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, Feature

from distutils.cmd import Command
from distutils.errors import DistutilsOptionError

classifiers = """\
Intended Audience :: Developers
License :: OSI Approved :: Apache Software License
Development Status :: 4 - Beta
Natural Language :: English
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Operating System :: MacOS :: MacOS X
Operating System :: Unix
Programming Language :: Python
Programming Language :: Python :: Implementation :: CPython
"""

description = 'Non-blocking MongoDB driver for Tornado'

long_description = open("README.rst").read()

import sys
if sys.version_info[:2] < (2, 7):
    tests_require = 'unittest2'
    test_suite = 'unittest2.collector'
else:
    # In Python 2.7+, unittest has a built-in collector.
    # Test everything under 'test/'.
    tests_require = None
    test_suite = 'test'


class test(Command):
    description = "run the tests"

    user_options = [
        ("test-module=", "m", "Discover tests in specified module"),
        ("test-suite=", "s",
         "Test suite to run (e.g. 'some_module.test_suite')"),
        ("failfast", "f", "Stop running tests on first failure or error"),
        ("tornado-warnings", "w", "Let Tornado log warnings")]

    def initialize_options(self):
        self.test_module = None
        self.test_suite = None
        self.failfast = False
        self.tornado_warnings = False

    def finalize_options(self):
        if self.test_suite is None and self.test_module is None:
            self.test_module = 'test'
        elif self.test_module is not None and self.test_suite is not None:
            raise DistutilsOptionError(
                "You may specify a module or suite, but not both")

    def run(self):
        # Installing required packages, running egg_info and build_ext are
        # part of normal operation for setuptools.command.test.test. Motor
        # has no extensions so build_ext is a no-op.
        if self.distribution.install_requires:
            self.distribution.fetch_build_eggs(
                self.distribution.install_requires)
        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)
        self.run_command('egg_info')
        build_ext_cmd = self.reinitialize_command('build_ext')
        build_ext_cmd.inplace = 1
        self.run_command('build_ext')

        # Construct a MotorTestRunner directly from the unittest imported from
        # test (this will be unittest2 under Python 2.6), which creates a
        # TestResult that supports the 'addSkip' method. setuptools will by
        # default create a TextTestRunner that uses the old TestResult class,
        # resulting in DeprecationWarnings instead of skipping tests under 2.6.
        from test import unittest, MotorTestRunner
        if self.test_suite is None:
            suite = unittest.defaultTestLoader.discover(self.test_module)
        else:
            suite = unittest.defaultTestLoader.loadTestsFromName(
                self.test_suite)

        runner_kwargs = dict(
            verbosity=2,
            failfast=self.failfast,
            tornado_warnings=self.tornado_warnings)

        if sys.version_info[:3] >= (3, 2):
            # 'warnings' argument added to TextTestRunner in Python 3.2.
            runner_kwargs['warnings'] = 'default'

        runner = MotorTestRunner(**runner_kwargs)
        result = runner.run(suite)
        sys.exit(not result.wasSuccessful())


setup(name='motor',
      version='0.4.1',
      packages=['motor'],
      description=description,
      long_description=long_description,
      author='A. Jesse Jiryu Davis',
      author_email='jesse@mongodb.com',
      url='https://github.com/mongodb/motor/',
      install_requires=[
          'tornado >= 3.1',
          'greenlet >= 0.4.0',
          'pymongo == 2.8.0',
      ],
      license='http://www.apache.org/licenses/LICENSE-2.0',
      classifiers=filter(None, classifiers.split('\n')),
      keywords=[
          "mongo", "mongodb", "pymongo", "gridfs", "bson", "motor", "tornado",
      ],
      tests_require=tests_require,
      test_suite=test_suite,
      zip_safe=False,
      cmdclass={'test': test})
