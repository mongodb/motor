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
)

import pymongo.common
import pymongo.database
import pymongo.errors
import pymongo.mongo_client
from bson import Binary, CodecOptions, DBRef, Timestamp
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

from .metaprogramming import AsyncCommand, AsyncRead, DelegateMethod, ReadOnlyProperty

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
    __delegate_class__: pymongo.mongo_client.MongoClient

    def address(self) -> Optional[Tuple[str, int]]: ...
    def arbiters(self) -> Set[Tuple[str, int]]: ...
    def close(self) -> None: ...
    def __hash__(self) -> int: ...
    def drop_database(
        self,
        name_or_database: Union[str, Database[_DocumentTypeArg]],
        session: Optional[ClientSession] = None,
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
    def list_databases(
        self,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> CommandCursor[Dict[str, Any]]: ...
    def list_database_names(
        self,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
    ) -> List[str]: ...
    def nodes(self) -> FrozenSet[_Address]: ...
    PORT: int
    def primary(self) -> Optional[Tuple[str, int]]: ...
    read_concern: ReadConcern
    def secondaries(self) -> Set[Tuple[str, int]]: ...
    def server_info(self, session: Optional[ClientSession] = None) -> Dict[str, Any]: ...
    def topology_description(self) -> TopologyDescription: ...
    def start_session(
        self,
        causal_consistency: Optional[bool] = None,
        default_transaction_options: Optional[TransactionOptions] = None,
        snapshot: Optional[bool] = False,
    ) -> Coroutine[None, None, AgnosticClientSession]: ...

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
        session: Optional[ClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[str] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> ChangeStream[_DocumentType]: ...
    def __getattr__(self, name: str) -> Any: ...
    def __getitem__(self, name: str) -> Any: ...
    def wrap(self, obj: Any) -> Any: ...

class _MotorTransactionContext:
    _session: AgnosticClientSession

    def __init__(self, session: AgnosticClientSession): ...
    async def __aenter__(self) -> _MotorTransactionContext: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

class AgnosticClientSession(AgnosticBase):
    __motor_class_name__: str
    __delegate_class__: ClientSession

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
        coro: Coroutine,
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
    __delegate_class__: Database

    def __hash__(self) -> int: ...
    def __bool__(self) -> int: ...
    async def command(
        self,
        command: Union[str, MutableMapping[str, Any]],
        value: Any = 1,
        check: bool = True,
        allowable_errors: Optional[Sequence[Union[str, int]]] = None,
        read_preference: Optional[_ServerMode] = None,
        codec_options: Optional[CodecOptions[_CodecDocumentType]] = None,
        session: Optional[ClientSession] = None,
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
        session: Optional[ClientSession] = None,
        check_exists: Optional[bool] = True,
        **kwargs: Any,
    ) -> Collection[_DocumentType]: ...
    async def dereference(
        self,
        dbref: DBRef,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> Optional[_DocumentType]: ...
    async def drop_collection(
        self,
        name_or_collection: Union[str, Collection[_DocumentTypeArg]],
        session: Optional[ClientSession] = None,
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
    ) -> Collection[_DocumentType]: ...
    async def list_collection_names(
        self,
        session: Optional[ClientSession] = None,
        filter: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[str]: ...
    async def list_collections(
        self,
        session: Optional[ClientSession] = None,
        filter: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AgnosticCommandCursor: ...
    def name(self) -> str: ...
    async def validate_collection(
        self,
        name_or_collection: Union[str, Collection[_DocumentTypeArg]],
        scandata: bool = False,
        full: bool = False,
        session: Optional[ClientSession] = None,
        background: Optional[bool] = None,
        comment: Optional[Any] = None,
    ) -> Dict[str, Any]: ...
    def with_options(
        self,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> Database[_DocumentType]: ...
    async def _async_aggregate(
        self, pipeline: _Pipeline, session: Optional[ClientSession] = None, **kwargs: Any
    ) -> AgnosticCommandCursor: ...
    def __init__(
        self, client: pymongo.MongoClient[_DocumentType], name: str, **kwargs: Any
    ) -> None: ...
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
        session: Optional[ClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> AgnosticChangeStream: ...
    @property
    def client(self) -> pymongo.MongoClient[_DocumentType]: ...
    def __getattr__(self, name: str) -> Any: ...
    def __getitem__(self, name: str) -> AgnosticCollection: ...
    def __call__(self, *args: Any, **kwargs: Any) -> None: ...
    def wrap(self, obj: Any) -> Any: ...
    def get_io_loop(self) -> Any: ...

class AgnosticCollection(AgnosticBaseProperties):
    __motor_class_name__: str
    __delegate_class__: Any

    async def bulk_write(
        self,
        requests: Sequence[_WriteOp[_DocumentType]],
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        let: Optional[Mapping] = None,
    ) -> BulkWriteResult: ...
    async def count_documents(
        self,
        filter: Mapping[str, Any],
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> int: ...
    async def create_index(
        self,
        keys: _IndexKeyHint,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> str: ...
    async def create_indexes(
        self,
        indexes: Sequence[IndexModel],
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[str]: ...
    async def delete_many(
        self,
        filter: Mapping[str, Any],
        collation: Optional[_CollationIn] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[ClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> DeleteResult: ...
    async def delete_one(
        self,
        filter: Mapping[str, Any],
        collation: Optional[_CollationIn] = None,
        hint: Optional[_IndexKeyHint] = None,
        session: Optional[ClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> DeleteResult: ...
    async def distinct(
        self,
        key: str,
        filter: Optional[Mapping[str, Any]] = None,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[Any]: ...
    async def drop(
        self,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        encrypted_fields: Optional[Mapping[str, Any]] = None,
    ) -> None: ...
    async def drop_index(
        self,
        index_or_name: _IndexKeyHint,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> None: ...
    async def drop_indexes(
        self,
        session: Optional[ClientSession] = None,
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
        session: Optional[ClientSession] = None,
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
        session: Optional[ClientSession] = None,
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
        session: Optional[ClientSession] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> _DocumentType: ...
    async def index_information(
        self, session: Optional[ClientSession] = None, comment: Optional[Any] = None
    ) -> MutableMapping[str, Any]: ...
    async def insert_many(
        self,
        documents: Iterable[Union[_DocumentType, RawBSONDocument]],
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[ClientSession] = None,
        comment: Optional[Any] = None,
    ) -> InsertManyResult: ...
    async def insert_one(
        self,
        document: Union[_DocumentType, RawBSONDocument],
        bypass_document_validation: bool = False,
        session: Union[Optional[ClientSession], Optional[AgnosticClientSession]] = None,
        comment: Optional[Any] = None,
    ) -> InsertOneResult: ...
    async def options(
        self, session: Optional[ClientSession] = None, comment: Optional[Any] = None
    ) -> MutableMapping[str, Any]: ...
    async def rename(
        self,
        new_name: str,
        session: Optional[ClientSession] = None,
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
        session: Optional[ClientSession] = None,
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
        session: Optional[ClientSession] = None,
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
        session: Union[Optional[ClientSession], Optional[AgnosticClientSession]] = None,
        let: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
    ) -> UpdateResult: ...
    async def with_options(
        self,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreference] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> Collection[Mapping[str, Any]]: ...
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
    def __getattr__(self, name: str) -> Any: ...
    def __getitem__(self, name: str) -> Any: ...
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
        session: Optional[ClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> Any: ...
    def list_indexes(
        self, session: Optional[ClientSession] = None, **kwargs: Any
    ) -> AgnosticCommandCursor: ...
    def wrap(self, obj: Any) -> Any: ...
    def get_io_loop(self) -> Any: ...

class AgnosticBaseCursor(AgnosticBase):
    _async_close: Any
    _refresh: Any
    address: Optional[_Address]
    cursor_id: Optional[int]
    alive: bool
    session: Optional[ClientSession]

    def __init__(
        self, cursor: Union[Cursor, CommandCursor, _LatentCursor], collection: Collection
    ) -> None: ...
    def __aiter__(self) -> Any: ...
    async def next(self) -> _DocumentType: ...
    __anext__ = next
    async def __aenter__(self) -> Any: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any: ...
    def _get_more(self) -> Mapping[str, Any]: ...
    @property
    def fetch_next(self) -> Any: ...
    def next_object(self) -> Any: ...
    def each(self, callback: Callable) -> None: ...
    def _each_got_more(self, callback: Callable, future: Any) -> None: ...
    def to_list(self, length: int) -> List: ...
    def _to_list(self, length: int, the_list: List, future: Any, get_more_result: Any) -> None: ...
    def get_io_loop(self) -> Any: ...
    async def close(self) -> None: ...
    def batch_size(self, batch_size: int) -> AgnosticBaseCursor: ...
    def _buffer_size(self) -> int: ...
    def _query_flags(self) -> Optional[int]: ...
    def _data(self) -> None: ...
    def _killed(self) -> None: ...

class AgnosticCursor(AgnosticBaseCursor):
    __motor_class_name__: str
    __delegate_class__: Cursor
    address: Optional[_Address]
    collation: _CollationIn
    distinct: List
    explain: Mapping[str, Any]
    add_option: Cursor[Mapping[str, Any]]
    remove_option: Cursor[Mapping[str, Any]]
    limit: int
    skip: int
    max_scan: Optional[int]
    sort: Optional[_Sort]
    hint: Optional[_Hint]
    where: Any
    max_await_time_ms: Optional[int]
    max_time_ms: Optional[int]
    min: Optional[_Sort]
    max: Optional[_Sort]
    comment: Optional[Any]
    allow_disk_use: Optional[bool]

    def rewind(self) -> AgnosticCursor: ...
    def clone(self) -> AgnosticCursor: ...
    def __copy__(self) -> AgnosticCursor: ...
    def __deepcopy__(self, memo: Any) -> AgnosticCursor: ...
    def _query_flags(self) -> int: ...
    def _data(self) -> Any: ...
    def _killed(self) -> Any: ...

class AgnosticRawBatchCursor(AgnosticCursor):
    __motor_class_name__: str
    __delegate_class__: RawBatchCursor

class AgnosticCommandCursor(AgnosticBaseCursor):
    __motor_class_name__: str
    __delegate_class__: CommandCursor

    def _query_flags(self) -> int: ...
    def _data(self) -> Any: ...
    def _killed(self) -> Any: ...

class AgnosticRawBatchCommandCursor(AgnosticCommandCursor):
    __motor_class_name__: str
    __delegate_class__: RawBatchCommandCursor

class _LatentCursor:
    alive: bool
    _CommandCursor__data: List
    _CommandCursor__id: None
    _CommandCursor__killed: bool
    _CommandCursor__sock_mgr: None
    _CommandCursor__session: None
    _CommandCursor__explicit_session: None
    cursor_id: None

    def __init__(self, collection: Any): ...
    def _CommandCursor__end_session(self, *args: Any, **kwargs: Any) -> None: ...
    def _CommandCursor__die(self, *args: Any, **kwargs: Any) -> None: ...
    def clone(self) -> _LatentCursor: ...
    def rewind(self): ...

class AgnosticLatentCommandCursor(AgnosticCommandCursor):
    __motor_class_name__: str

    def __init__(self, collection: Any, start: Any, *args: Any, **kwargs: Any): ...
    def batch_size(self, batch_size: int) -> AgnosticLatentCommandCursor: ...
    def _get_more(self): ...
    def _on_started(self, original_future: Any, future: Any) -> None: ...

class AgnosticChangeStream(AgnosticBase):
    __delegate_class__: ChangeStream
    __motor_class_name__: str

    _close: AsyncCommand
    resume_token: Optional[Mapping[str, Any]]

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
        session: Optional[ClientSession],
        start_after: Optional[Mapping[str, Any]],
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ): ...
    def _lazy_init(self): ...
    def _try_next(self): ...
    @property
    def alive(self) -> bool: ...
    async def next(self) -> _DocumentType: ...
    async def try_next(self) -> Optional[_DocumentType]: ...
    async def close(self): ...
    def __aiter__(self) -> AgnosticChangeStream: ...
    __anext__ = next
    async def __aenter__(self) -> AgnosticChangeStream: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    def get_io_loop(self): ...
    def __enter__(self): ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

class AgnosticClientEncryption(AgnosticBase):
    __motor_class_name__: str
    __delegate_class__: ClientEncryption
    create_data_key: Awaitable[Binary]
    encrypt: Awaitable[Binary]
    decrypt: Awaitable[Binary]
    close: Awaitable[None]
    rewrap_many_data_key: Awaitable[RewrapManyDataKeyResult]
    delete_key: Awaitable[DeleteResult]
    get_key: Awaitable[Optional[RawBSONDocument]]
    add_key_alt_name: Awaitable[Any]
    get_key_by_alt_name: Awaitable[Optional[RawBSONDocument]]
    remove_key_alt_name: Awaitable[Optional[RawBSONDocument]]
    encrypt_expression: Optional[Awaitable[RawBSONDocument]]

    def __init__(
        self,
        kms_providers: Mapping[str, Any],
        key_vault_namespace: str,
        key_vault_client: pymongo.MongoClient,
        codec_options: CodecOptions,
        io_loop: Optional[Any] = None,
        kms_tls_options: Optional[Mapping[str, Any]] = None,
    ): ...
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
    ) -> Tuple[Collection[_DocumentType], Mapping[str, Any]]: ...
