from setuptools import setup


def parse_reqs_file(fname):
    with open(fname) as fid:  # noqa:PTH123
        lines = [li.strip() for li in fid.readlines()]
    return [li for li in lines if li and not li.startswith("#")]


extras_require = dict(  # noqa:C408
    aws=parse_reqs_file("requirements/aws-requirements.txt"),
    encryption=parse_reqs_file("requirements/encryption-requirements.txt"),
    gssapi=parse_reqs_file("requirements/gssapi-requirements.txt"),
    ocsp=parse_reqs_file("requirements/ocsp-requirements.txt"),
    snappy=parse_reqs_file("requirements/snappy-requirements.txt"),
    srv=parse_reqs_file("requirements/srv-requirements.txt"),
    test=parse_reqs_file("requirements/test-requirements.txt"),
    zstd=parse_reqs_file("requirements/zstd-requirements.txt"),
)

setup(install_requires=parse_reqs_file("requirements.txt"), extras_require=extras_require)
