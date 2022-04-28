import sys

if sys.version_info[:2] < (3, 10):
    from distutils.cmd import Command
    from distutils.errors import DistutilsOptionError as OptionError
else:
    from setuptools import Command
    from setuptools.errors import OptionError


from setuptools import setup

if sys.version_info[:2] < (3, 7):
    raise Exception("This version of Motor requires Python>=3.7")

classifiers = """\
Intended Audience :: Developers
License :: OSI Approved :: Apache Software License
Development Status :: 5 - Production/Stable
Natural Language :: English
Programming Language :: Python :: 3
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Operating System :: MacOS :: MacOS X
Operating System :: Unix
Operating System :: Microsoft :: Windows
Programming Language :: Python
Programming Language :: Python :: Implementation :: CPython
Programming Language :: Python :: Implementation :: PyPy
"""

description = "Non-blocking MongoDB driver for Tornado or asyncio"

with open("README.rst") as readme:
    long_description = readme.read()

pymongo_ver = ">=4.1,<5"

install_requires = ["pymongo" + pymongo_ver]

extras_require = {
    "encryption": ["pymongo[encryption]" + pymongo_ver],
    "ocsp": ["pymongo[ocsp]" + pymongo_ver],
    "snappy": ["pymongo[snappy]" + pymongo_ver],
    "zstd": ["pymongo[zstd]" + pymongo_ver],
    "aws": ["pymongo[aws]" + pymongo_ver],
    "srv": ["pymongo[srv]" + pymongo_ver],
    "gssapi": ["pymongo[gssapi]" + pymongo_ver],
}

tests_require = ["mockupdb>=1.4.0"]


class test(Command):
    description = "run the tests"

    user_options = [
        ("test-module=", "m", "Discover tests in specified module"),
        ("test-suite=", "s", "Test suite to run (e.g. 'some_module.test_suite')"),
        ("failfast", "f", "Stop running tests on first failure or error"),
        ("tornado-warnings", "w", "Let Tornado log warnings"),
        ("xunit-output=", "x", "Generate a results directory with XUnit XML format"),
    ]

    def initialize_options(self):
        self.test_module = None
        self.test_suite = None
        self.failfast = False
        self.tornado_warnings = False
        self.xunit_output = None

    def finalize_options(self):
        if self.test_suite is None and self.test_module is None:
            self.test_module = "test"
        elif self.test_module is not None and self.test_suite is not None:
            raise OptionError("You may specify a module or suite, but not both")

    def run(self):
        # Installing required packages, running egg_info and build_ext are
        # part of normal operation for setuptools.command.test.test. Motor
        # has no extensions so build_ext is a no-op.
        if self.distribution.install_requires:
            self.distribution.fetch_build_eggs(self.distribution.install_requires)
        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)
        if self.xunit_output:
            self.distribution.fetch_build_eggs(["unittest-xml-reporting>=1.14.0,<2.0.0a0"])
        self.run_command("egg_info")
        build_ext_cmd = self.reinitialize_command("build_ext")
        build_ext_cmd.inplace = 1
        self.run_command("build_ext")

        from test import MotorTestLoader, env, suppress_tornado_warnings
        from test import test_environment as testenv

        loader = MotorTestLoader()
        loader.avoid("high_availability", reason="Runs separately")

        if not (testenv.HAVE_ASYNCIO or testenv.HAVE_TORNADO):
            raise ImportError("No tornado nor asyncio")
        elif not testenv.HAVE_TORNADO:
            loader.avoid("tornado_tests", reason="no tornado")
        elif not testenv.HAVE_ASYNCIO:
            loader.avoid("asyncio_tests", reason="no asyncio")

        if not testenv.HAVE_AIOHTTP:
            loader.avoid("asyncio_tests.test_aiohttp_gridfs", reason="no aiohttp")

        # Decide if we can run async / await tests with Tornado.
        if not testenv.HAVE_TORNADO:
            test_motor_await = "tornado_tests.test_motor_await"
            loader.avoid(test_motor_await, reason="no tornado")

        if self.test_suite is None:
            suite = loader.discover(self.test_module)
        else:
            suite = loader.loadTestsFromName(self.test_suite)

        runner_kwargs = dict(verbosity=2, failfast=self.failfast)

        if self.xunit_output:
            runner_kwargs["output"] = self.xunit_output
            from xmlrunner import XMLTestRunner

            runner_class = XMLTestRunner
        else:
            import unittest

            runner_class = unittest.TextTestRunner

        runner = runner_class(**runner_kwargs)
        env.setup()
        if not self.tornado_warnings:
            suppress_tornado_warnings()

        result = runner.run(suite)
        sys.exit(not result.wasSuccessful())


packages = [
    "motor",
    "motor.frameworks",
    "motor.frameworks.tornado",
    "motor.frameworks.asyncio",
    "motor.aiohttp",
]


setup(
    name="motor",
    version="3.1.0.dev0",
    packages=packages,
    description=description,
    long_description=long_description,
    author="A. Jesse Jiryu Davis",
    author_email="jesse@mongodb.com",
    url="https://github.com/mongodb/motor/",
    python_requires=">=3.7",
    install_requires=install_requires,
    extras_require=extras_require,
    license="http://www.apache.org/licenses/LICENSE-2.0",
    classifiers=[c for c in classifiers.split("\n") if c],
    keywords=[
        "mongo",
        "mongodb",
        "pymongo",
        "gridfs",
        "bson",
        "motor",
        "tornado",
        "asyncio",
    ],
    tests_require=tests_require,
    test_suite="test",
    zip_safe=False,
    cmdclass={"test": test},
)
