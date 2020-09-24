==============
Motor Releases
==============

Versioning
----------

Motor's version numbers follow `semantic versioning <http://semver.org/>`_:
each version number is structured "major.minor.patch". Patch releases fix
bugs, minor releases add features (and may fix bugs), and major releases
include API changes that break backwards compatibility (and may add features
and fix bugs).

In between releases we add .devN to the version number to denote the version
under development. So if we just released 2.3.0, then the current dev
version might be 2.3.1.dev0 or 2.4.0.dev0. When we make the next release we
replace all instances of 2.x.x.devN in the docs with the new version number.

https://www.python.org/dev/peps/pep-0440/

Release Process
---------------

Motor ships a `pure Python wheel <https://packaging.python.org/guides/distributing-packages-using-setuptools/#pure-python-wheels>`_
and a `source distribution <https://packaging.python.org/guides/distributing-packages-using-setuptools/#source-distributions>`_.

#. Motor is tested on Evergreen. Ensure that the latest commit is passing CI as
   expected: https://evergreen.mongodb.com/waterfall/motor.

#. Check JIRA to ensure all the tickets in this version have been completed.

#. Add release notes to `doc/changelog.rst`. Generally just summarize/clarify
   the git log, but you might add some more long form notes for big changes.

#. Search and replace the `devN` version number w/ the new version number (see
   note above in `Versioning`_). Make sure version number is updated in
   `setup.py` and `motor/__init__.py`. Commit the change and tag the release.
   Immediately bump the version number to `dev0` in a new commit::

     $ # Bump to release version number
     $ git commit -a -m "BUMP <release version number>"
     $ git tag -a "<release version number>" -m "BUMP <release version number>"
     $ # Bump to dev version number
     $ git commit -a -m "BUMP <dev version number>"
     $ git push
     $ git push --tags

#. Build the release packages by running the `release.sh`
   script on macOS::

     $ git clone git@github.com:mongodb/mongo-python-driver.git
     $ cd mongo-python-driver
     $ git checkout "<release version number>"
     $ ./release.sh

   This will create the following distributions::

     $ ls dist
     motor-<version>.tar.gz
     motor-<version>-py3-none-any.whl

#. Upload all the release packages to PyPI with twine::

     $ python3 -m twine upload dist/*

#. Trigger a build of the docs on https://readthedocs.org/.

#. Announce!
