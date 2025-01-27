from typing import Any, Mapping, MutableMapping, Optional, Union

from bson import Code, CodecOptions, Timestamp
from bson.raw_bson import RawBSONDocument
from pymongo.client_session import TransactionOptions
from pymongo.cursor_shared import _Hint, _Sort
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import ReadPreference, _ServerMode
from pymongo.typings import _CollationIn, _DocumentType, _DocumentTypeArg, _Pipeline
from pymongo.write_concern import WriteConcern

from motor import core, motor_gridfs

__all__: list[str] = [
    "AsyncIOMotorClient",
    "AsyncIOMotorClientSession",
    "AsyncIOMotorDatabase",
    "AsyncIOMotorCollection",
    "AsyncIOMotorCursor",
    "AsyncIOMotorCommandCursor",
    "AsyncIOMotorChangeStream",
    "AsyncIOMotorGridFSBucket",
    "AsyncIOMotorGridIn",
    "AsyncIOMotorGridOut",
    "AsyncIOMotorGridOutCursor",
    "AsyncIOMotorClientEncryption",
    "AsyncIOMotorLatentCommandCursor",
]

class AsyncIOMotorClient(core.AgnosticClient[_DocumentType]):
    def get_database(
        self,
        name: Optional[str] = None,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AsyncIOMotorDatabase[_DocumentType]: ...
    def get_default_database(
        self,
        default: Optional[str] = None,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AsyncIOMotorDatabase[_DocumentType]: ...
    async def list_databases(
        self,
        session: Optional[core.AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIOMotorCommandCursor[dict[str, Any]]: ...
    async def start_session(
        self,
        causal_consistency: Optional[bool] = None,
        default_transaction_options: Optional[TransactionOptions] = None,
        snapshot: Optional[bool] = False,
    ) -> AsyncIOMotorClientSession: ...
    def watch(
        self,
        pipeline: Optional[_Pipeline] = None,
        full_document: Optional[str] = None,
        resume_after: Optional[Mapping[str, Any]] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[_CollationIn] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[core.AgnosticClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[str] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> AsyncIOMotorChangeStream[_DocumentType]: ...
    def __getattr__(self, name: str) -> AsyncIOMotorDatabase[_DocumentType]: ...
    def __getitem__(self, name: str) -> AsyncIOMotorDatabase[_DocumentType]: ...

class AsyncIOMotorClientSession(core.AgnosticClientSession):
    @property
    def client(self) -> AsyncIOMotorClient: ...
    async def __aenter__(self) -> AsyncIOMotorClientSession: ...

class AsyncIOMotorDatabase(core.AgnosticDatabase[_DocumentType]):
    async def cursor_command(
        self,
        command: Union[str, MutableMapping[str, Any]],
        value: Any = 1,
        read_preference: Optional[_ServerMode] = None,
        codec_options: Optional[CodecOptions[core._CodecDocumentType]] = None,
        session: Optional[core.AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        max_await_time_ms: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIOMotorCommandCursor[_DocumentType]: ...
    async def create_collection(
        self,
        name: str,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
        session: Optional[core.AgnosticClientSession] = None,
        check_exists: Optional[bool] = True,
        **kwargs: Any,
    ) -> AsyncIOMotorCollection[_DocumentType]: ...
    def get_collection(
        self,
        name: str,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AsyncIOMotorCollection[_DocumentType]: ...
    async def list_collections(
        self,
        session: Optional[core.AgnosticClientSession] = None,
        filter: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIOMotorCommandCursor[MutableMapping[str, Any]]: ...
    def with_options(
        self,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AsyncIOMotorDatabase[_DocumentType]: ...
    def aggregate(
        self, pipeline: _Pipeline, *args: Any, **kwargs: Any
    ) -> AsyncIOMotorLatentCommandCursor[_DocumentType]: ...
    def watch(
        self,
        pipeline: Optional[_Pipeline] = None,
        full_document: Optional[str] = None,
        resume_after: Optional[Mapping[str, Any]] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[_CollationIn] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[core.AgnosticClientSession] = None,
        start_after: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        full_document_before_change: Optional[str] = None,
        show_expanded_events: Optional[bool] = None,
    ) -> AsyncIOMotorChangeStream[_DocumentType]: ...
    @property
    def client(self) -> AsyncIOMotorClient[_DocumentType]: ...
    def __getattr__(self, name: str) -> AsyncIOMotorCollection[_DocumentType]: ...
    def __getitem__(self, name: str) -> AsyncIOMotorCollection[_DocumentType]: ...

class AsyncIOMotorCollection(core.AgnosticCollection[_DocumentType]):
    def with_options(
        self,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreference] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AsyncIOMotorCollection[_DocumentType]: ...
    def list_search_indexes(
        self,
        name: Optional[str] = None,
        session: Optional[core.AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIOMotorLatentCommandCursor[Mapping[str, Any]]: ...
    def __getattr__(self, name: str) -> AsyncIOMotorCollection[_DocumentType]: ...
    def __getitem__(self, name: str) -> AsyncIOMotorCollection[_DocumentType]: ...
    def find(self, *args: Any, **kwargs: Any) -> AsyncIOMotorCursor[_DocumentType]: ...
    def find_raw_batches(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIOMotorRawBatchCursor[_DocumentType]: ...
    def aggregate(
        self, pipeline: _Pipeline, *args: Any, **kwargs: Any
    ) -> AsyncIOMotorCommandCursor[_DocumentType]: ...
    def aggregate_raw_batches(
        self, pipeline: _Pipeline, **kwargs: Any
    ) -> AsyncIOMotorRawBatchCursor[_DocumentType]: ...
    def list_indexes(
        self, session: Optional[core.AgnosticClientSession] = None, **kwargs: Any
    ) -> AsyncIOMotorLatentCommandCursor[MutableMapping[str, Any]]: ...

class AsyncIOMotorLatentCommandCursor(core.AgnosticLatentCommandCursor[_DocumentType]): ...

class AsyncIOMotorCursor(core.AgnosticCursor[_DocumentType]):
    def collation(self, collation: Optional[_CollationIn]) -> AsyncIOMotorCursor[_DocumentType]: ...
    def add_option(self, mask: int) -> AsyncIOMotorCursor[_DocumentType]: ...
    def remove_option(self, mask: int) -> AsyncIOMotorCursor[_DocumentType]: ...
    def limit(self, limit: int) -> AsyncIOMotorCursor[_DocumentType]: ...
    def skip(self, skip: int) -> AsyncIOMotorCursor[_DocumentType]: ...
    def max_scan(self, max_scan: Optional[int]) -> AsyncIOMotorCursor[_DocumentType]: ...
    def sort(
        self, key_or_list: _Hint, direction: Optional[Union[int, str]] = None
    ) -> AsyncIOMotorCursor[_DocumentType]: ...
    def hint(self, index: Optional[_Hint]) -> AsyncIOMotorCursor[_DocumentType]: ...
    def where(self, code: Union[str, Code]) -> AsyncIOMotorCursor[_DocumentType]: ...
    def max_await_time_ms(
        self, max_await_time_ms: Optional[int]
    ) -> AsyncIOMotorCursor[_DocumentType]: ...
    def max_time_ms(self, max_time_ms: Optional[int]) -> AsyncIOMotorCursor[_DocumentType]: ...
    def min(self, spec: _Sort) -> AsyncIOMotorCursor[_DocumentType]: ...
    def max(self, spec: _Sort) -> AsyncIOMotorCursor[_DocumentType]: ...
    def comment(self, comment: Any) -> AsyncIOMotorCursor[_DocumentType]: ...
    def allow_disk_use(self, allow_disk_use: bool) -> AsyncIOMotorCursor[_DocumentType]: ...
    def rewind(self) -> AsyncIOMotorCursor[_DocumentType]: ...
    def clone(self) -> AsyncIOMotorCursor[_DocumentType]: ...
    def __copy__(self) -> AsyncIOMotorCursor[_DocumentType]: ...
    def __deepcopy__(self, memo: Any) -> AsyncIOMotorCursor[_DocumentType]: ...

class AsyncIOMotorRawBatchCursor(core.AgnosticRawBatchCursor[_DocumentType]): ...
class AsyncIOMotorCommandCursor(core.AgnosticCommandCursor[_DocumentType]): ...
class AsyncIOMotorRawBatchCommandCursor(core.AgnosticRawBatchCommandCursor[_DocumentType]): ...

class AsyncIOMotorChangeStream(core.AgnosticChangeStream[_DocumentType]):
    def __aiter__(self) -> AsyncIOMotorChangeStream[_DocumentType]: ...
    async def __aenter__(self) -> AsyncIOMotorChangeStream[_DocumentType]: ...

class AsyncIOMotorClientEncryption(core.AgnosticClientEncryption[_DocumentType]):
    async def __aenter__(self) -> AsyncIOMotorClientEncryption[_DocumentType]: ...
    async def get_keys(self) -> AsyncIOMotorCursor[RawBSONDocument]: ...
    async def create_encrypted_collection(
        self,
        database: core.AgnosticDatabase[_DocumentTypeArg],
        name: str,
        encrypted_fields: Mapping[str, Any],
        kms_provider: Optional[str] = None,
        master_key: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> tuple[AsyncIOMotorCollection[_DocumentTypeArg], Mapping[str, Any]]: ...

class AsyncIOMotorGridOutCursor(motor_gridfs.AgnosticGridOutCursor):
    def next_object(self) -> AsyncIOMotorGridOutCursor: ...

class AsyncIOMotorGridOut(motor_gridfs.AgnosticGridOut):
    def __aiter__(self) -> AsyncIOMotorGridOut: ...

class AsyncIOMotorGridIn(motor_gridfs.AgnosticGridIn):
    async def __aenter__(self) -> AsyncIOMotorGridIn: ...

class AsyncIOMotorGridFSBucket(motor_gridfs.AgnosticGridFSBucket):
    async def open_download_stream_by_name(
        self,
        filename: str,
        revision: int = -1,
        session: Optional[core.AgnosticClientSession] = None,
    ) -> AsyncIOMotorGridOut: ...
    async def open_download_stream(
        self, file_id: Any, session: Optional[core.AgnosticClientSession] = None
    ) -> AsyncIOMotorGridOut: ...
    def open_upload_stream(
        self,
        filename: str,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[core.AgnosticClientSession] = None,
    ) -> AsyncIOMotorGridIn: ...
    def open_upload_stream_with_id(
        self,
        file_id: Any,
        filename: str,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[core.AgnosticClientSession] = None,
    ) -> AsyncIOMotorGridIn: ...
    def find(self, *args: Any, **kwargs: Any) -> AsyncIOMotorGridOutCursor: ...
