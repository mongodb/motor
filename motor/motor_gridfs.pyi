# Copyright 2023-present MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""GridFS type stubs for Motor, an asynchronous driver for MongoDB."""

import datetime
import os
from typing import Any, Iterable, Mapping, NoReturn, Optional

from bson import ObjectId
from gridfs import DEFAULT_CHUNK_SIZE, GridFSBucket, GridIn, GridOut, GridOutCursor
from pymongo import WriteConcern
from pymongo.read_preferences import _ServerMode

from motor.core import (
    AgnosticClientSession,
    AgnosticCollection,
    AgnosticCursor,
    AgnosticDatabase,
)

_SEEK_SET = os.SEEK_SET
_SEEK_CUR = os.SEEK_CUR
_SEEK_END = os.SEEK_END

class AgnosticGridOutCursor(AgnosticCursor):
    __motor_class_name__: str
    __delegate_class__ = type[GridOutCursor]
    async def _Cursor__die(self, synchronous: bool = False) -> None: ...
    def next_object(self) -> AgnosticGridOutCursor: ...

class AgnosticGridOut:
    __motor_class_name__: str
    __delegate_class__: type[GridOut]
    _id: Any
    aliases: Optional[list[str]]
    chunk_size: int
    filename: Optional[str]
    name: Optional[str]
    content_type: Optional[str]
    length: int
    upload_date: datetime.datetime
    metadata: Optional[Mapping[str, Any]]
    async def _ensure_file(self) -> None: ...
    def close(self) -> None: ...
    async def read(self, size: int = -1) -> NoReturn: ...
    def readable(self) -> bool: ...
    async def readchunk(self) -> bytes: ...
    async def readline(self, size: int = -1) -> bytes: ...
    def seek(self, pos: int, whence: int = _SEEK_SET) -> int: ...
    def seekable(self) -> bool: ...
    def tell(self) -> int: ...
    def write(self, data: Any) -> None: ...
    def __init__(
        self,
        root_collection: AgnosticCollection,
        file_id: Optional[int] = None,
        file_document: Optional[Any] = None,
        delegate: Any = None,
        session: Optional[AgnosticClientSession] = None,
    ) -> None: ...
    def __aiter__(self) -> AgnosticGridOut: ...
    async def __anext__(self) -> bytes: ...
    def __getattr__(self, item: str) -> Any: ...
    def open(self) -> Any: ...
    def get_io_loop(self) -> Any: ...
    async def stream_to_handler(self, request_handler: Any) -> None: ...

class AgnosticGridIn:
    __motor_class_name__: str
    __delegate_class__: type[GridIn]
    __getattr__: Any
    _id: Any
    filename: str
    name: str
    content_type: Optional[str]
    length: int
    chunk_size: int
    upload_date: datetime.datetime

    async def abort(self) -> None: ...
    def closed(self) -> bool: ...
    async def close(self) -> None: ...
    def read(self, size: int = -1) -> NoReturn: ...
    def readable(self) -> bool: ...
    def seekable(self) -> bool: ...
    async def write(self, data: Any) -> None: ...
    def writeable(self) -> bool: ...
    async def writelines(self, sequence: Iterable[Any]) -> None: ...
    async def _exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any: ...
    async def set(self, name: str, value: Any) -> None: ...
    def __init__(
        self,
        root_collection: AgnosticCollection,
        delegate: Any = None,
        session: Optional[AgnosticClientSession] = None,
        **kwargs: Any,
    ) -> None: ...
    async def __aenter__(self) -> AgnosticGridIn: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    def get_io_loop(self) -> Any: ...

class AgnosticGridFSBucket:
    __motor_class_name__: str
    __delegate_class__: type[GridFSBucket]
    async def delete(
        self, file_id: Any, session: Optional[AgnosticClientSession] = None
    ) -> None: ...
    async def download_to_stream(
        self, file_id: Any, destination: Any, session: Optional[AgnosticClientSession] = None
    ) -> None: ...
    async def download_to_stream_by_name(
        self,
        filename: str,
        destination: Any,
        revision: int = -1,
        session: Optional[AgnosticClientSession] = None,
    ) -> None: ...
    async def open_download_stream_by_name(
        self, filename: str, revision: int = -1, session: Optional[AgnosticClientSession] = None
    ) -> GridOut: ...
    async def open_download_stream(
        self, file_id: Any, session: Optional[AgnosticClientSession] = None
    ) -> GridOut: ...
    def open_upload_stream(
        self,
        filename: str,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[AgnosticClientSession] = None,
    ) -> GridIn: ...
    def open_upload_stream_with_id(
        self,
        file_id: Any,
        filename: str,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[AgnosticClientSession] = None,
    ) -> GridIn: ...
    async def rename(
        self, file_id: Any, new_filename: str, session: Optional[AgnosticClientSession] = None
    ) -> None: ...
    async def upload_from_stream(
        self,
        filename: str,
        source: Any,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[AgnosticClientSession] = None,
    ) -> ObjectId: ...
    async def upload_from_stream_with_id(
        self,
        file_id: Any,
        filename: str,
        source: Any,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[AgnosticClientSession] = None,
    ) -> None: ...
    def __init__(
        self,
        database: AgnosticDatabase,
        bucket_name: str = "fs",
        chunk_size_bytes: int = DEFAULT_CHUNK_SIZE,
        write_concern: Optional[WriteConcern] = None,
        read_preference: Optional[_ServerMode] = None,
        collection: Optional[AgnosticCollection] = None,
    ) -> None: ...
    def get_io_loop(self) -> Any: ...
    def wrap(self, obj: Any) -> Any: ...
    def find(self, *args: Any, **kwargs: Any) -> AgnosticGridOutCursor: ...

def _hash_gridout(gridout: AgnosticGridOut) -> str: ...
