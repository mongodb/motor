# Motor Releases

## Versioning

Motor's version numbers follow [semantic
versioning](http://semver.org/): each version number is structured
"major.minor.patch". Patch releases fix bugs, minor releases add
features (and may fix bugs), and major releases include API changes that
break backwards compatibility (and may add features and fix bugs).

In between releases we add .devN to the version number to denote the
version under development. So if we just released 2.3.0, then the
current dev version might be 2.3.1.dev0 or 2.4.0.dev0. When we make the
next release we replace all instances of 2.x.x.devN in the docs with the
new version number.

<https://www.python.org/dev/peps/pep-0440/>

## Release Process

Motor ships a [pure Python
wheel](https://packaging.python.org/guides/distributing-packages-using-setuptools/#pure-python-wheels)
and a [source
distribution](https://packaging.python.org/guides/distributing-packages-using-setuptools/#source-distributions).

1.  Motor is tested on Evergreen. Ensure that the latest commit is
    passing CI as expected:
    <https://evergreen.mongodb.com/waterfall/motor>.

2.  Check JIRA to ensure all the tickets in this version have been
    completed.

3.  Add release notes to `doc/changelog.rst`. Generally just
    summarize/clarify the git log, but you might add some more long form
    notes for big changes.

4.  Replace the `devN` version number w/ the new version number (see
    note above in [Versioning](#versioning)) in `motor/_version.py`.
    Commit the change and tag the release. Immediately bump the version
    number to `dev0` in a new commit:

        $ # Bump to release version number
        $ git commit -a -m "BUMP <release version number>"
        $ git tag -a "<release version number>" -m "BUMP <release version number>"
        $ # Bump to dev version number
        $ git commit -a -m "BUMP <dev version number>"
        $ git push
        $ git push --tags

5.  Bump the version number to `<next version>.dev0` in
    `motor/_version.py`, commit, then push.

6.  Authorize the deployment for the tagged version on the release
    GitHub Action and wait for it to successfully publish to PyPI.

7.  Make sure the new version appears on
    <https://motor.readthedocs.io/>. If the new version does not show up
    automatically, trigger a rebuild of "latest":
    <https://readthedocs.org/projects/motor/builds/>

8.  Publish the release version in Jira and add a brief description
    about the reason for the release or the main feature.

9.  Announce the release on:
    <https://www.mongodb.com/community/forums/c/announcements/driver-releases>

10. Create a GitHub Release for the tag using
    <https://github.com/mongodb/motor/releases/new>. The title should be
    "Motor X.Y.Z", and the description should contain a link to the
    release notes on the the community forum, e.g. "Release notes:
    mongodb.com/community/forums/t/motor-2-5-1-released/120313."
