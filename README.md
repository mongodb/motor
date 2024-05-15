# Motor

[![PyPI Version](https://img.shields.io/pypi/v/motor)](https://pypi.org/project/motor)
[![Python Versions](https://img.shields.io/pypi/pyversions/motor)](https://pypi.org/project/motor)
[![Monthly Downloads](https://static.pepy.tech/badge/motor/month)](https://pepy.tech/project/motor)
[![Documentation Status](https://readthedocs.org/projects/motor/badge/?version=stable)](http://motor.readthedocs.io/en/stable/?badge=stable)

![image](https://raw.github.com/mongodb/motor/master/doc/_static/motor.png)

## About

Motor is a full-featured, non-blocking [MongoDB](http://mongodb.org/)
driver for Python [asyncio](https://docs.python.org/3/library/asyncio.html) and
[Tornado](http://tornadoweb.org/) applications. Motor presents a coroutine-based API
for non-blocking access to MongoDB.

> "We use Motor in high throughput environments, processing tens of
> thousands of requests per second. It allows us to take full advantage
> of modern hardware, ensuring we utilise the entire capacity of our
> purchased CPUs. This helps us be more efficient with computing power,
> compute spend and minimises the environmental impact of our
> infrastructure as a result."
>
> --*David Mytton, Server Density*
>
> "We develop easy-to-use sensors and sensor systems with open source
> software to ensure every innovator, from school child to laboratory
> researcher, has the same opportunity to create. We integrate Motor
> into our software to guarantee massively scalable sensor systems for
> everyone."
>
> --*Ryan Smith, inXus Interactive*

## Support / Feedback

For issues with, questions about, or feedback for PyMongo, please look
into our [support channels](https://support.mongodb.com/welcome). Please
do not email any of the Motor developers directly with issues or
questions - you're more likely to get an answer on the
[StackOverflow](https://stackoverflow.com/questions/tagged/mongodb)
(using a "mongodb" tag).

## Bugs / Feature Requests

Think you've found a bug? Want to see a new feature in Motor? Please
open a case in our issue management tool, JIRA:

- [Create an account and login](https://jira.mongodb.org).
- Navigate to [the MOTOR
  project](https://jira.mongodb.org/browse/MOTOR).
- Click **Create Issue** - Please provide as much information as
  possible about the issue type and how to reproduce it.

Bug reports in JIRA for all driver projects (i.e. MOTOR, CSHARP, JAVA)
and the Core Server (i.e. SERVER) project are **public**.

### How To Ask For Help

Please include all of the following information when opening an issue:

- Detailed steps to reproduce the problem, including full traceback, if
  possible.

- The exact python version used, with patch level:

```bash
python -c "import sys; print(sys.version)"
```

- The exact version of Motor used, with patch level:

```bash
python -c "import motor; print(motor.version)"
```

- The exact version of PyMongo used, with patch level:

```bash
python -c "import pymongo; print(pymongo.version); print(pymongo.has_c())"
```

- The exact Tornado version, if you are using Tornado:

```bash
python -c "import tornado; print(tornado.version)"
```

- The operating system and version (e.g. RedHat Enterprise Linux 6.4,
  OSX 10.9.5, ...)

### Security Vulnerabilities

If you've identified a security vulnerability in a driver or any other
MongoDB project, please report it according to the [instructions
here](https://mongodb.com/docs/manual/tutorial/create-a-vulnerability-report).

## Installation

Motor can be installed with [pip](http://pypi.python.org/pypi/pip):

```bash
pip install motor
```

## Dependencies

Motor works in all the environments officially supported by Tornado or
by asyncio. It requires:

- Unix (including macOS) or Windows.
- [PyMongo](http://pypi.python.org/pypi/pymongo/) >=4.1,<5
- Python 3.8+

Optional dependencies:

Motor supports same optional dependencies as PyMongo. Required
dependencies can be installed along with Motor.

GSSAPI authentication requires `gssapi` extra dependency. The correct
dependency can be installed automatically along with Motor:

```bash
pip install "motor[gssapi]"
```

similarly,

MONGODB-AWS authentication requires `aws` extra dependency:

```bash
pip install "motor[aws]"
```

Support for mongodb+srv:// URIs requires `srv` extra dependency:

```bash
pip install "motor[srv]"
```

OCSP requires `ocsp` extra dependency:

```bash
pip install "motor[ocsp]"
```

Wire protocol compression with snappy requires `snappy` extra
dependency:

```bash
pip install "motor[snappy]"
```

Wire protocol compression with zstandard requires `zstd` extra
dependency:

```bash
pip install "motor[zstd]"
```

Client-Side Field Level Encryption requires `encryption` extra
dependency:

```bash
pip install "motor[encryption]"
```

You can install all dependencies automatically with the following
command:

```bash
pip install "motor[gssapi,aws,ocsp,snappy,srv,zstd,encryption]"
```

See
[requirements](https://motor.readthedocs.io/en/stable/requirements.html)
for details about compatibility.

## Examples

See the [examples on
ReadTheDocs](https://motor.readthedocs.io/en/stable/examples/index.html).

## Documentation

Motor's documentation is on
[ReadTheDocs](https://motor.readthedocs.io/en/stable/).

Build the documentation with Python 3.8+. Install
[sphinx](http://sphinx.pocoo.org/), [Tornado](http://tornadoweb.org/),
and [aiohttp](https://github.com/aio-libs/aiohttp), and do
`cd doc; make html`.

## Learning Resources

- MongoDB Learn - [Python
courses](https://learn.mongodb.com/catalog?labels=%5B%22Language%22%5D&values=%5B%22Python%22%5D).
- [Python Articles on Developer
Center](https://www.mongodb.com/developer/languages/python/).

## Testing

Run `python setup.py test`. Tests are located in the `test/` directory.
