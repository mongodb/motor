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

"""Framework-agnostic type stubs for Motor, an asynchronous driver for MongoDB."""

from __future__ import annotations

from asyncio import Future
from typing import (
    Any,
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    NoReturn,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

import pymongo.common
import pymongo.database
import pymongo.errors
import pymongo.mongo_client
from bson import Binary, Code, CodecOptions, DBRef, Timestamp
from bson.raw_bson import RawBSONDocument
from pymongo import IndexModel, ReadPreference, WriteConcern
from pymongo.change_stream import ChangeStream
from pymongo.client_options import ClientOptions
from pymongo.client_session import _T, ClientSession, SessionOptions, TransactionOptions
from pymongo.collection import ReturnDocument, _IndexKeyHint, _IndexList, _WriteOp
from pymongo.command_cursor import CommandCursor, RawBatchCommandCursor
from pymongo.cursor import Cursor, RawBatchCursor, _Hint, _Sort
from pymongo.database import Database
from pymongo.encryption import ClientEncryption, RewrapManyDataKeyResult
from pymongo.encryption_options import RangeOpts
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import _ServerMode
from pymongo.results import (
    BulkWriteResult,
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)
from pymongo.topology_description import TopologyDescription
from pymongo.typings import (
    _Address,
    _CollationIn,
    _DocumentType,
    _DocumentTypeArg,
    _Pipeline,
)

try:
    from pymongo import SearchIndexModel
except ImportError:
    SearchIndexModel = Any

_WITH_TRANSACTION_RETRY_TIME_LIMIT: int

_CodecDocumentType = TypeVar("_CodecDocumentType", bound=Mapping[str, Any])

def _within_time_limit(start_time: float) -> bool: ...
def _max_time_expired_error(exc: Exception) -> bool: ...

class AgnosticBase(object):
    delegate: Any

    def __eq__(self, other: Any) -> bool: ...
    def __init__(self, delegate: Any) -> None: ...
    def __repr__(self) -> str: ...

class AgnosticBaseProperties(AgnosticBase):
    codec_options: CodecOptions
    read_preference: _ServerMode
    read_concern: ReadConcern
    write_concern: WriteConcern

class AgnosticClient(AgnosticBaseProperties):
    __motor_class_name__: str
    __delegate_class__: Type[pymongo.MongoClient]

    def address(self) -> Optional[Tuple[str, int]]: ...
    def arbiters(self) -> Set[Tuple[str, int]]: ...
    def close(self) -> None: ...
    def __hash__(self) -> int: ...
    async def drop_database(
        self,
        name_or_database: Union[str, AgnosticDatabase],
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
    ) -> None: ...
    def options(self) -> ClientOptions: ...
    def get_database(
        self,
        name: Optional[str] = None,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> Database[_DocumentType]: ...
    def get_default_database(
        self,
        default: Optional[str] = None,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> Database[_DocumentType]: ...

    HOST: str

    def is_mongos(self) -> bool: ...
    def is_primary(self) -> bool: ...
    async def list_databases(
        self,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AgnosticCommandCursor: ...
    async def list_database_names(
        self,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
    ) -> List[str]: ...
    def nodes(self) -> FrozenSet[_Address]: ...
    PORT: int
    def primary(self) -> Optional[Tuple[str, int]]: ...
    read_concern: ReadConcern
    def secondaries(self) -> Set[Tuple[str, int]]: ...
    async def server_info(
        self, session: Optional[AgnosticClientSession] = None
    ) -> Dict[str, Any]: ...
    def topology_description(self) -> TopologyDescription: ...
    async def start_session(
        self,
        causal_consistency: Optional[bool] = None,
        default_transaction_options: Optional[TransactionOptions] = None,
        snapshot: Optional[bool] = False,
    ) -> AgnosticClientSession: ...

    _io_loop: Optional[Any]
    _framework: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    @property
    def io_loop(self) -> Any: ...
    def get_io_loop(self) -> Any: ...
    def watch(
        self,
        pipeline: Optional[_Pipeline] = None,
        full_document: Optional[str] = None,
        resume_after: Optional[Mapping[str, Any]] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[_CollationIn] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AgnosticClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[str] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> AgnosticChangeStream: ...
    def __getattr__(self, name: str) -> AgnosticDatabase: ...
    def __getitem__(self, name: str) -> AgnosticDatabase: ...
    def wrap(self, obj: Any) -> Any: ...

class _MotorTransactionContext:
    _session: AgnosticClientSession

    def __init__(self, session: AgnosticClientSession): ...
    async def __aenter__(self) -> _MotorTransactionContext: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

class AgnosticClientSession(AgnosticBase):
    __motor_class_name__: str
    __delegate_class__: Type[ClientSession]

    async def commit_transaction(self) -> None: ...
    async def abort_transaction(self) -> None: ...
    async def end_session(self) -> None: ...
    def cluster_time(self) -> Optional[Mapping[str, Any]]: ...
    def has_ended(self) -> bool: ...
    def in_transaction(self) -> bool: ...
    def options(self) -> SessionOptions: ...
    def operation_time(self) -> Optional[Timestamp]: ...
    def session_id(self) -> Mapping[str, Any]: ...
    def advance_cluster_time(self, cluster_time: Mapping[str, Any]) -> None: ...
    def advance_operation_time(self, operation_time: Timestamp) -> None: ...
    def __init__(self, delegate: ClientSession, motor_client: AgnosticClient): ...
    def get_io_loop(self) -> Any: ...
    async def with_transaction(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        read_concern: Optional[ReadConcern] = None,
        write_concern: Optional[WriteConcern] = None,
        read_preference: Optional[_ServerMode] = None,
        max_commit_time_ms: Optional[int] = None,
    ) -> _T: ...
    def start_transaction(
        self,
        read_concern: Optional[ReadConcern] = None,
        write_concern: Optional[WriteConcern] = None,
        read_preference: Optional[_ServerMode] = None,
        max_commit_time_ms: Optional[int] = None,
    ) -> _MotorTransactionContext: ...
    @property
    def client(self) -> AgnosticClient: ...
    async def __aenter__(self) -> AgnosticClientSession: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

class AgnosticDatabase(AgnosticBaseProperties):
    __motor_class_name__: str
    __delegate_class__: Type[Database]

    def __hash__(self) -> int: ...
    def __bool__(self) -> int: ...
    async def cursor_command(
        self,
        command: Union[str, MutableMapping[str, Any]],
        value: Any = 1,
        read_preference: Optional[_ServerMode] = None,
        codec_options: Optional[CodecOptions[_CodecDocumentType]] = None,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        max_await_time_ms: Optional[int] = None,
        **kwargs: Any,
    ) -> AgnosticCommandCursor: ...
    async def command(
        self,
        command: Union[str, MutableMapping[str, Any]],
        value: Any = 1,
        check: bool = True,
        allowable_errors: Optional[Sequence[Union[str, int]]] = None,
        read_preference: Optional[_ServerMode] = None,
        codec_options: Optional[CodecOptions[_CodecDocumentType]] = None,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> Union[Dict[str, Any], _CodecDocumentType]: ...
    async def create_collection(
        self,
        name: str,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
        session: Optional[AgnosticClientSession] = None,
        check_exists: Optional[bool] = True,
        **kwargs: Any,
    ) -> AgnosticCollection: ...
    async def dereference(
        self,
        dbref: DBRef,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> Optional[_DocumentType]: ...
    async def drop_collection(
        self,
        name_or_collection: Union[str, AgnosticCollection],
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        encrypted_fields: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]: ...
    async def get_collection(
        self,
        name: str,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AgnosticCollection: ...
    async def list_collection_names(
        self,
        session: Optional[AgnosticClientSession] = None,
        filter: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[str]: ...
    async def list_collections(
        self,
        session: Optional[AgnosticClientSession] = None,
        filter: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AgnosticCommandCursor: ...
    def name(self) -> str: ...
    async def validate_collection(
        self,
        name_or_collection: Union[str, AgnosticCollection],
        scandata: bool = False,
        full: bool = False,
        session: Optional[AgnosticClientSession] = None,
        background: Optional[bool] = None,
        comment: Optional[Any] = None,
    ) -> Dict[str, Any]: ...
    def with_options(
        self,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AgnosticDatabase: ...
    async def _async_aggregate(
        self, pipeline: _Pipeline, session: Optional[AgnosticClientSession] = None, **kwargs: Any
    ) -> AgnosticCommandCursor: ...
    def __init__(self, client: AgnosticClient, name: str, **kwargs: Any) -> None: ...
    def aggregate(
        self, pipeline: _Pipeline, *args: Any, **kwargs: Any
    ) -> AgnosticLatentCommandCursor: ...
    def watch(
        self,
        pipeline: Optional[_Pipeline] = None,
        full_document: Optional[str] = None,
        resume_after: Optional[Mapping[str, Any]] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[_CollationIn] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AgnosticClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> AgnosticChangeStream: ...
    @property
    def client(self) -> AgnosticClient: ...
    def __getattr__(self, name: str) -> AgnosticCollection: ...
    def __getitem__(self, name: str) -> AgnosticCollection: ...
    def __call__(self, *args: Any, **kwargs: Any) -> None: ...
    def wrap(self, obj: Any) -> Any: ...
    def get_io_loop(self) -> Any: ...

class AgnosticCollection(AgnosticBaseProperties):
    __motor_class_name__: str
    __delegate_class__: Type[Collection]

    def __hash__(self) -> int: ...
    def __bool__(self) -> bool: ...
    async def bulk_write(
        self,
        requests: Sequence[_WriteOp[_DocumentType]],
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        let: Optional[Mapping] = None,
    ) -> BulkWriteResult: ...
    async def count_documents(
        self,
        filter: Mapping[str, Any],
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> int: ...
    async def create_index(
        self,
        keys: _IndexKeyHint,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> str: ...
    async def create_indexes(
        self,
        indexes: Sequence[IndexModel],
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[str]: ...
    async def delete_many(
        self,
        filter: Mapping[str, Any],
        collation: Optional[_CollationIn] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> DeleteResult: ...
    async def delete_one(
        self,
        filter: Mapping[str, Any],
        collation: Optional[_CollationIn] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> DeleteResult: ...
    async def distinct(
        self,
        key: str,
        filter: Optional[Mapping[str, Any]] = None,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[Any]: ...
    async def drop(
        self,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        encrypted_fields: Optional[Mapping[str, Any]] = None,
    ) -> None: ...
    async def drop_index(
        self,
        index_or_name: _IndexKeyHint,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...
    async def drop_indexes(
        self,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...
    async def estimated_document_count(
        self, comment: Optional[Any] = None, **kwargs: Any
    ) -> int: ...
    async def find_one(
        self, filter: Optional[Any] = None, *args: Any, **kwargs: Any
    ) -> Optional[_DocumentType]: ...
    async def find_one_and_delete(
        self,
        filter: Mapping[str, Any],
        projection: Optional[Union[Mapping[str, Any], Iterable[str]]] = None,
        sort: Optional[_IndexList] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> _DocumentType: ...
    async def find_one_and_replace(
        self,
        filter: Mapping[str, Any],
        replacement: Mapping[str, Any],
        projection: Optional[Union[Mapping[str, Any], Iterable[str]]] = None,
        sort: Optional[_IndexList] = None,
        upsert: bool = False,
        return_document: bool = ReturnDocument.BEFORE,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> _DocumentType: ...
    async def find_one_and_update(
        self,
        filter: Mapping[str, Any],
        update: Union[Mapping[str, Any], _Pipeline],
        projection: Optional[Union[Mapping[str, Any], Iterable[str]]] = None,
        sort: Optional[_IndexList] = None,
        upsert: bool = False,
        return_document: bool = ReturnDocument.BEFORE,
        array_filters: Optional[Sequence[Mapping[str, Any]]] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> _DocumentType: ...
    def full_name(self) -> str: ...
    async def index_information(
        self, session: Optional[AgnosticClientSession] = None, comment: Optional[Any] = None
    ) -> MutableMapping[str, Any]: ...
    async def insert_many(
        self,
        documents: Iterable[Union[_DocumentType, RawBSONDocument]],
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
    ) -> InsertManyResult: ...
    async def insert_one(
        self,
        document: Union[_DocumentType, RawBSONDocument],
        bypass_document_validation: bool = False,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
    ) -> InsertOneResult: ...
    def name(self) -> str: ...
    async def options(
        self, session: Optional[AgnosticClientSession] = None, comment: Optional[Any] = None
    ) -> MutableMapping[str, Any]: ...
    async def rename(
        self,
        new_name: str,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]: ...
    async def replace_one(
        self,
        filter: Mapping[str, Any],
        replacement: Mapping[str, Any],
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: Optional[_CollationIn] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> UpdateResult: ...
    async def update_many(
        self,
        filter: Mapping[str, Any],
        update: Union[Mapping[str, Any], _Pipeline],
        upsert: bool = False,
        array_filters: Optional[Sequence[Mapping[str, Any]]] = None,
        bypass_document_validation: Optional[bool] = None,
        collation: Optional[_CollationIn] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[AgnosticClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> UpdateResult: ...
    async def update_one(
        self,
        filter: Mapping[str, Any],
        update: Union[Mapping[str, Any], _Pipeline],
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: Optional[_CollationIn] = None,
        array_filters: Optional[Sequence[Mapping[str, Any]]] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Union[Optional[AgnosticClientSession], Optional[AgnosticClientSession]] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> UpdateResult: ...
    def with_options(
        self,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreference] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> Collection[Mapping[str, Any]]: ...
    async def list_search_indexes(
        self,
        name: Optional[str] = None,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AgnosticCommandCursor: ...
    async def create_search_index(
        self,
        model: Union[Mapping[str, SearchIndexModel], Any],
        session: Optional[AgnosticClientSession] = None,
        comment: Any = None,
        **kwargs: Any,
    ) -> str: ...
    async def create_search_indexes(
        self,
        models: List[SearchIndexModel],
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[str]: ...
    async def drop_search_index(
        self,
        name: str,
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...
    async def update_search_index(
        self,
        name: str,
        definition: Mapping[str, Any],
        session: Optional[AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...
    def __init__(
        self,
        database: Database[_DocumentType],
        name: str,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
        _delegate: Any = None,
        **kwargs: Any,
    ) -> None: ...
    def __getattr__(self, name: str) -> AgnosticCollection: ...
    def __getitem__(self, name: str) -> AgnosticCollection: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def find(self, *args: Any, **kwargs: Any) -> AgnosticCursor: ...
    def find_raw_batches(self, *args: Any, **kwargs: Any) -> AgnosticCursor: ...
    def aggregate(
        self, pipeline: _Pipeline, *args: Any, **kwargs: Any
    ) -> AgnosticCommandCursor: ...
    def aggregate_raw_batches(
        self, pipeline: _Pipeline, **kwargs: Any
    ) -> AgnosticCommandCursor: ...
    def watch(
        self,
        pipeline: Optional[_Pipeline] = None,
        full_document: Optional[str] = None,
        resume_after: Optional[Mapping[str, Any]] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[_CollationIn] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AgnosticClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> Any: ...
    def list_indexes(
        self, session: Optional[AgnosticClientSession] = None, **kwargs: Any
    ) -> AgnosticCommandCursor: ...
    def wrap(self, obj: Any) -> Any: ...
    def get_io_loop(self) -> Any: ...

class AgnosticBaseCursor(AgnosticBase):
    def __init__(
        self, cursor: Union[Cursor, CommandCursor, _LatentCursor], collection: AgnosticCollection
    ) -> None: ...
    def address(self) -> Optional[_Address]: ...
    def cursor_id(self) -> Optional[int]: ...
    def alive(self) -> bool: ...
    def session(self) -> Optional[AgnosticClientSession]: ...
    async def _async_close(self) -> None: ...
    async def _refresh(self) -> int: ...
    def __aiter__(self) -> Any: ...
    async def next(self) -> _DocumentType: ...
    __anext__ = next
    async def __aenter__(self) -> Any: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any: ...
    def _get_more(self) -> int: ...
    @property
    def fetch_next(self) -> Future[Any]: ...
    def next_object(self) -> Any: ...
    def each(self, callback: Callable) -> None: ...
    def _each_got_more(self, callback: Callable, future: Any) -> None: ...
    def to_list(self, length: int) -> Future[List]: ...
    def _to_list(self, length: int, the_list: List, future: Any, get_more_result: Any) -> None: ...
    def get_io_loop(self) -> Any: ...
    def batch_size(self, batch_size: int) -> AgnosticBaseCursor: ...
    def _buffer_size(self) -> int: ...
    def _query_flags(self) -> Optional[int]: ...
    def _data(self) -> None: ...
    def _killed(self) -> None: ...
    async def close(self) -> None: ...

class AgnosticCursor(AgnosticBaseCursor):
    __motor_class_name__: str
    __delegate_class__: Type[Cursor]
    def collation(self, collation: Optional[_CollationIn]) -> AgnosticCursor: ...
    async def distinct(self, key: str) -> List: ...
    async def explain(self) -> _DocumentType: ...
    def add_option(self, mask: int) -> AgnosticCursor: ...
    def remove_option(self, mask: int) -> AgnosticCursor: ...
    def limit(self, limit: int) -> AgnosticCursor: ...
    def skip(self, skip: int) -> AgnosticCursor: ...
    def max_scan(self, max_scan: Optional[int]) -> AgnosticCursor: ...
    def sort(
        self, key_or_list: _Hint, direction: Optional[Union[int, str]] = None
    ) -> AgnosticCursor: ...
    def hint(self, index: Optional[_Hint]) -> AgnosticCursor: ...
    def where(self, code: Union[str, Code]) -> AgnosticCursor: ...
    def max_await_time_ms(self, max_await_time_ms: Optional[int]) -> AgnosticCursor: ...
    def max_time_ms(self, max_time_ms: Optional[int]) -> AgnosticCursor: ...
    def min(self, spec: _Sort) -> AgnosticCursor: ...
    def max(self, spec: _Sort) -> AgnosticCursor: ...
    def comment(self, comment: Any) -> AgnosticCursor: ...
    def allow_disk_use(self, allow_disk_use: bool) -> AgnosticCursor: ...
    def rewind(self) -> AgnosticCursor: ...
    def clone(self) -> AgnosticCursor: ...
    def __copy__(self) -> AgnosticCursor: ...
    def __deepcopy__(self, memo: Any) -> AgnosticCursor: ...
    def _query_flags(self) -> int: ...
    def _data(self) -> Any: ...
    def _killed(self) -> Any: ...

class AgnosticRawBatchCursor(AgnosticCursor):
    __motor_class_name__: str
    __delegate_class__: Type[RawBatchCursor]

class AgnosticCommandCursor(AgnosticBaseCursor):
    __motor_class_name__: str
    __delegate_class__: Type[CommandCursor]

    def _query_flags(self) -> int: ...
    def _data(self) -> Any: ...
    def _killed(self) -> Any: ...

class AgnosticRawBatchCommandCursor(AgnosticCommandCursor):
    __motor_class_name__: str
    __delegate_class__: Type[RawBatchCommandCursor]

class _LatentCursor:
    def __init__(self, collection: AgnosticCollection): ...
    def _CommandCursor__end_session(self, *args: Any, **kwargs: Any) -> None: ...
    def _CommandCursor__die(self, *args: Any, **kwargs: Any) -> None: ...
    def clone(self) -> _LatentCursor: ...
    def rewind(self) -> _LatentCursor: ...

class AgnosticLatentCommandCursor(AgnosticCommandCursor):
    __motor_class_name__: str
    def __init__(self, collection: AgnosticCollection, start: Any, *args: Any, **kwargs: Any): ...
    def _on_started(self, original_future: Any, future: Any) -> None: ...

class AgnosticChangeStream(AgnosticBase):
    __motor_class_name__: str
    __delegate_class__: Type[ChangeStream]

    async def _close(self) -> None: ...
    def resume_token(self) -> Optional[Mapping[str, Any]]: ...
    def __init__(
        self,
        target: Union[
            pymongo.MongoClient[_DocumentType], Database[_DocumentType], Collection[_DocumentType]
        ],
        pipeline: Optional[_Pipeline],
        full_document: Optional[str],
        resume_after: Optional[Mapping[str, Any]],
        max_await_time_ms: Optional[int],
        batch_size: Optional[int],
        collation: Optional[_CollationIn],
        start_at_operation_time: Optional[Timestamp],
        session: Optional[AgnosticClientSession],
        start_after: Optional[Mapping[str, Any]],
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ): ...
    def _lazy_init(self) -> None: ...
    def _try_next(self) -> Optional[_DocumentType]: ...
    def alive(self) -> bool: ...
    async def next(self) -> _DocumentType: ...
    async def try_next(self) -> Optional[_DocumentType]: ...
    async def close(self) -> None: ...
    def __aiter__(self) -> AgnosticChangeStream: ...
    __anext__ = next
    async def __aenter__(self) -> AgnosticChangeStream: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    def get_io_loop(self) -> Any: ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

class AgnosticClientEncryption(AgnosticBase):
    __motor_class_name__: str
    __delegate_class__: Type[ClientEncryption]
    def __init__(
        self,
        kms_providers: Mapping[str, Any],
        key_vault_namespace: str,
        key_vault_client: AgnosticClient,
        codec_options: CodecOptions,
        io_loop: Optional[Any] = None,
        kms_tls_options: Optional[Mapping[str, Any]] = None,
    ): ...
    async def create_data_key(
        self,
        kms_provider: str,
        master_key: Optional[Mapping[str, Any]] = None,
        key_alt_names: Optional[Sequence[str]] = None,
        key_material: Optional[bytes] = None,
    ) -> Binary: ...
    async def encrypt(
        self,
        value: Any,
        algorithm: str,
        key_id: Optional[Binary] = None,
        key_alt_name: Optional[str] = None,
        query_type: Optional[str] = None,
        contention_factor: Optional[int] = None,
        range_opts: Optional[RangeOpts] = None,
    ) -> Binary: ...
    async def decrypt(self, value: Binary) -> Any: ...
    async def close(self) -> None: ...
    async def rewrap_many_data_key(
        self,
        filter: Mapping[str, Any],
        provider: Optional[str] = None,
        master_key: Optional[Mapping[str, Any]] = None,
    ) -> RewrapManyDataKeyResult: ...
    async def delete_key(self, id: Binary) -> DeleteResult: ...
    async def get_key(self, id: Binary) -> Optional[RawBSONDocument]: ...
    async def add_key_alt_name(self, id: Binary, key_alt_name: str) -> Any: ...
    async def get_key_by_alt_name(self, key_alt_name: str) -> Optional[RawBSONDocument]: ...
    async def remove_key_alt_name(
        self, id: Binary, key_alt_name: str
    ) -> Optional[RawBSONDocument]: ...
    async def encrypt_expression(
        self,
        expression: Mapping[str, Any],
        algorithm: str,
        key_id: Optional[Binary] = None,
        key_alt_name: Optional[str] = None,
        query_type: Optional[str] = None,
        contention_factor: Optional[int] = None,
        range_opts: Optional[RangeOpts] = None,
    ) -> RawBSONDocument: ...
    @property
    def io_loop(self) -> Any: ...
    def get_io_loop(self) -> Any: ...
    async def __aenter__(self) -> AgnosticClientEncryption: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    def __enter__(self) -> NoReturn: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    async def get_keys(self) -> AgnosticCursor: ...
    async def create_encrypted_collection(
        self,
        database: AgnosticDatabase,
        name: str,
        encrypted_fields: Mapping[str, Any],
        kms_provider: Optional[str] = None,
        master_key: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> Tuple[AgnosticCollection, Mapping[str, Any]]: ...
