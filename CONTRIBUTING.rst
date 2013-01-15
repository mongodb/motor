Contributing to Motor
=====================

Contributions are encouraged. Please read these guidelines before sending a
pull request.

Bugfixes and New Features
-------------------------

Before starting to write code, look for existing tickets or create one in `Jira
<https://jira.mongodb.org/browse/MOTOR>`_ for your specific issue or feature
request.

General Guidelines
------------------

- Avoid backward breaking changes if at all possible.
- Write inline documentation for new classes and methods.
- Write tests and make sure they pass (make sure you have a mongod
  running on the default port, then execute ``python setup.py nosetests``
  from the command line to run the test suite).
- Add yourself to doc/contributors.rst :)
