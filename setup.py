import sys
from distutils.cmd import Command
from distutils.errors import DistutilsOptionError

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools('28.0')
    from setuptools import setup

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
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Operating System :: MacOS :: MacOS X
Operating System :: Unix
Programming Language :: Python
Programming Language :: Python :: Implementation :: CPython
"""

description = 'Non-blocking MongoDB driver for Tornado or asyncio'

long_description = open("README.rst").read()

install_requires = ['pymongo>=2.9.4,<3']

tests_require = ['mockupdb']

if sys.version_info[0] < 3:
    # Need concurrent.futures backport in Python 2 for MotorMockServerTest.
    tests_require.append('futures')
    install_requires.append('futures')

if sys.version_info[:2] < (2, 7):
    tests_require.append('unittest2')
    test_suite = 'unittest2.collector'
else:
    # In Python 2.7+, unittest has a built-in collector.
    # Test everything under 'test/'.
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
        from test import (unittest, MotorTestLoader, MotorTestRunner,
                          test_environment as testenv)

        loader = MotorTestLoader()
        loader.avoid('high_availability', 'Runs separately')

        if not (testenv.HAVE_ASYNCIO or testenv.HAVE_TORNADO):
            raise ImportError("No tornado nor asyncio")
        elif not testenv.HAVE_TORNADO:
            loader.avoid('tornado_tests', reason='no tornado')
        elif not testenv.HAVE_ASYNCIO:
            loader.avoid('asyncio_tests', reason='no asyncio')

        if sys.version_info[:2] < (3, 5):
            loader.avoid('asyncio_tests.test_asyncio_await',
                         reason='python < 3.5')

        # Decide if we can run async / await tests with Tornado.
        test_motor_await = 'tornado_tests.test_motor_await'
        if not testenv.HAVE_TORNADO:
            loader.avoid(test_motor_await, reason='no tornado')
        # We need Tornado after this patch to wrap "async def" with gen_test:
        # https://github.com/tornadoweb/tornado/pull/1550
        elif not testenv.TORNADO_VERSION[:2] > (4, 2):
            loader.avoid(test_motor_await, reason='tornado < 4.3')
        elif sys.version_info[:2] < (3, 5):
            loader.avoid(test_motor_await, reason='python < 3.5')

        if self.test_suite is None:
            suite = loader.discover(self.test_module)
        else:
            suite = loader.loadTestsFromName(self.test_suite)

        runner_kwargs = dict(
            verbosity=2,
            failfast=self.failfast,
            tornado_warnings=self.tornado_warnings)

        if sys.version_info[:2] >= (3, 2) and unittest.__name__ != 'unittest2':
            # 'warnings' argument added to TextTestRunner in Python 3.2.
            runner_kwargs['warnings'] = 'default'

        runner = MotorTestRunner(**runner_kwargs)
        result = runner.run(suite)
        sys.exit(not result.wasSuccessful())


packages = ['motor', 'motor.frameworks', 'motor.frameworks.tornado']

if sys.version_info[0] >= 3:
    # Trying to install and byte-compile motor/frameworks/asyncio/__init__.py
    # causes SyntaxError in Python 2.
    packages.append('motor.frameworks.asyncio')

setup(name='motor',
      version='0.7',
      packages=packages,
      description=description,
      long_description=long_description,
      author='A. Jesse Jiryu Davis',
      author_email='jesse@mongodb.com',
      url='https://github.com/mongodb/motor/',
      install_requires=install_requires,
      license='http://www.apache.org/licenses/LICENSE-2.0',
      classifiers=[c for c in classifiers.split('\n') if c],
      keywords=[
          "mongo", "mongodb", "pymongo", "gridfs", "bson", "motor", "tornado",
          "asyncio",
      ],
      tests_require=tests_require,
      test_suite=test_suite,
      zip_safe=False,
      cmdclass={'test': test})
