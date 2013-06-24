# Don't force people to install distribute unless we have to.
try:
    from setuptools import setup, Feature
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, Feature

import sys

classifiers = """\
Intended Audience :: Developers
License :: OSI Approved :: Apache Software License
Development Status :: 4 - Beta
Natural Language :: English
Programming Language :: Python :: 2
Programming Language :: Python :: 2.5
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.2
Programming Language :: Python :: 3.3
Operating System :: MacOS :: MacOS X
Operating System :: Unix
Programming Language :: Python
Programming Language :: Python :: Implementation :: CPython
"""

description = 'Non-blocking MongoDB driver for Tornado'

long_description = open("README.rst").read()

major, minor = sys.version_info[:2]

kwargs = {}
if major >= 3:
    sys.stdout.write('using 2to3\n')
    kwargs['use_2to3'] = True

# HACK: implement "setup.py build --test" to work around
# https://github.com/nose-devs/nose/issues/556, which causes e.g.
# "python setup.py nosetests --tests test.test_motor_ssl" to run all the tests,
# not just the ones specified.

# For now, "setup.py build --test" builds Motor and its tests, so you can then
# "cd build/lib; nosetests test.test_motor_ssl" and test specific modules in
# the built package.

packages = ['motor']
if 'test' in sys.argv or 'nosetests' in sys.argv or '--test' in sys.argv:
    if '--test' in sys.argv:
        sys.stdout.write('including test modules\n')
        sys.argv.remove('--test')

    packages.append('test')

setup(name='motor',
      version='0.1+',
      packages=packages,
      description=description,
      long_description=long_description,
      author='A. Jesse Jiryu Davis',
      author_email='jesse@10gen.com',
      url='https://github.com/mongodb/motor/',
      install_requires=[
          'pymongo == 2.5.0',
          'tornado >= 2.4.0',
          'greenlet >= 0.4.0',
      ],
      license='http://www.apache.org/licenses/LICENSE-2.0',
      classifiers=filter(None, classifiers.split('\n')),
      keywords=[
          "mongo", "mongodb", "pymongo", "gridfs", "bson", "motor", "tornado",
      ],
      # use 'python setup.py test' to test
      setup_requires=['nose'],
      test_suite='nose.main',
      zip_safe=False,
      **kwargs)
