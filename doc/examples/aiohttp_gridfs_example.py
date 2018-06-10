"""Serve pre-compressed static content from GridFS with aiohttp.

Requires Python 3.5 or later and aiohttp 3.0 or later.

Start a MongoDB server on its default port, run this script, and visit:

http://localhost:8080/fs/my_file
"""
# -- include-start --
import asyncio
import gzip
import tempfile

import aiohttp.web

from motor.aiohttp import AIOHTTPGridFS
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

client = AsyncIOMotorClient()


# Use Motor to put compressed data in GridFS, with filename "my_file".
async def put_gridfile():
    with tempfile.TemporaryFile() as tmp:
        with gzip.GzipFile(mode='wb', fileobj=tmp) as gzfile:
            for _ in range(10):
                gzfile.write(b'Nonesuch nonsense\n')

        gfs = AsyncIOMotorGridFSBucket(client.my_database)
        tmp.seek(0)
        await gfs.upload_from_stream(filename='my_file',
                                     source=tmp,
                                     metadata={'contentType': 'text',
                                               'compressed': True})

asyncio.get_event_loop().run_until_complete(put_gridfile())


# Add "Content-Encoding: gzip" header for compressed data.
def gzip_header(response, gridout):
    if gridout.metadata.get('compressed'):
        response.headers['Content-Encoding'] = 'gzip'

gridfs_handler = AIOHTTPGridFS(client.my_database,
                               set_extra_headers=gzip_header)

app = aiohttp.web.Application()

# The GridFS URL pattern must have a "{filename}" variable.
resource = app.router.add_resource('/fs/{filename}')
resource.add_route('GET', gridfs_handler)
resource.add_route('HEAD', gridfs_handler)

aiohttp.web.run_app(app)
