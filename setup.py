from setuptools import setup


def parse_reqs_file(fname):
    with open(fname) as fid:  # noqa:PTH123
        lines = [li.strip() for li in fid.readlines()]
    return [li for li in lines if li and not li.startswith("#")]


extras_require = dict(  # noqa:C408
    aws=parse_reqs_file("requirements/aws.txt"),
    encryption=parse_reqs_file("requirements/encryption.txt"),
    gssapi=parse_reqs_file("requirements/gssapi.txt"),
    ocsp=parse_reqs_file("requirements/ocsp.txt"),
    snappy=parse_reqs_file("requirements/snappy.txt"),
    srv=parse_reqs_file("requirements/srv.txt"),
    test=parse_reqs_file("requirements/test.txt"),
    zstd=parse_reqs_file("requirements/zstd.txt"),
)

setup(install_requires=parse_reqs_file("requirements"), extras_require=extras_require)
