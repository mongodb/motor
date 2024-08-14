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
    "MotorClient",
    "MotorClientSession",
    "MotorDatabase",
    "MotorCollection",
    "MotorCursor",
    "MotorCommandCursor",
    "MotorChangeStream",
    "MotorGridFSBucket",
    "MotorGridIn",
    "MotorGridOut",
    "MotorGridOutCursor",
    "MotorClientEncryption",
]

class MotorClient(core.AgnosticClient[_DocumentType]):
    def get_database(
        self,
        name: Optional[str] = None,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> MotorDatabase[_DocumentType]: ...
    def get_default_database(
        self,
        default: Optional[str] = None,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> MotorDatabase[_DocumentType]: ...
    async def list_databases(
        self,
        session: Optional[core.AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> MotorCommandCursor[dict[str, Any]]: ...
    async def start_session(
        self,
        causal_consistency: Optional[bool] = None,
        default_transaction_options: Optional[TransactionOptions] = None,
        snapshot: Optional[bool] = False,
    ) -> MotorClientSession: ...
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
    ) -> MotorChangeStream[_DocumentType]: ...
    def __getattr__(self, name: str) -> MotorDatabase[_DocumentType]: ...
    def __getitem__(self, name: str) -> MotorDatabase[_DocumentType]: ...

class MotorClientSession(core.AgnosticClientSession):
    @property
    def client(self) -> MotorClient: ...
    async def __aenter__(self) -> MotorClientSession: ...

class MotorDatabase(core.AgnosticDatabase[_DocumentType]):
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
    ) -> MotorCommandCursor[_DocumentType]: ...
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
    ) -> MotorCollection[_DocumentType]: ...
    def get_collection(
        self,
        name: str,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> MotorCollection[_DocumentType]: ...
    async def list_collections(
        self,
        session: Optional[core.AgnosticClientSession] = None,
        filter: Optional[Mapping[str, Any]] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> MotorCommandCursor[MutableMapping[str, Any]]: ...
    def with_options(
        self,
        codec_options: Optional[CodecOptions[_DocumentTypeArg]] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> MotorDatabase[_DocumentType]: ...
    def aggregate(
        self, pipeline: _Pipeline, *args: Any, **kwargs: Any
    ) -> MotorLatentCommandCursor[_DocumentType]: ...
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
    ) -> MotorChangeStream[_DocumentType]: ...
    @property
    def client(self) -> MotorClient[_DocumentType]: ...
    def __getattr__(self, name: str) -> MotorCollection[_DocumentType]: ...
    def __getitem__(self, name: str) -> MotorCollection[_DocumentType]: ...

class MotorCollection(core.AgnosticCollection[_DocumentType]):
    def with_options(
        self,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreference] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> MotorCollection[_DocumentType]: ...
    def list_search_indexes(
        self,
        name: Optional[str] = None,
        session: Optional[core.AgnosticClientSession] = None,
        comment: Optional[Any] = None,
        **kwargs: Any,
    ) -> MotorLatentCommandCursor[Mapping[str, Any]]: ...
    def __getattr__(self, name: str) -> MotorCollection[_DocumentType]: ...
    def __getitem__(self, name: str) -> MotorCollection[_DocumentType]: ...
    def find(self, *args: Any, **kwargs: Any) -> MotorCursor[_DocumentType]: ...
    def find_raw_batches(self, *args: Any, **kwargs: Any) -> MotorRawBatchCursor[_DocumentType]: ...
    def aggregate(
        self, pipeline: _Pipeline, *args: Any, **kwargs: Any
    ) -> MotorCommandCursor[_DocumentType]: ...
    def aggregate_raw_batches(
        self, pipeline: _Pipeline, **kwargs: Any
    ) -> MotorRawBatchCursor[_DocumentType]: ...
    def list_indexes(
        self, session: Optional[core.AgnosticClientSession] = None, **kwargs: Any
    ) -> MotorLatentCommandCursor[MutableMapping[str, Any]]: ...

class MotorLatentCommandCursor(core.AgnosticLatentCommandCursor[_DocumentType]): ...

class MotorCursor(core.AgnosticCursor[_DocumentType]):
    def collation(self, collation: Optional[_CollationIn]) -> MotorCursor[_DocumentType]: ...
    def add_option(self, mask: int) -> MotorCursor[_DocumentType]: ...
    def remove_option(self, mask: int) -> MotorCursor[_DocumentType]: ...
    def limit(self, limit: int) -> MotorCursor[_DocumentType]: ...
    def skip(self, skip: int) -> MotorCursor[_DocumentType]: ...
    def max_scan(self, max_scan: Optional[int]) -> MotorCursor[_DocumentType]: ...
    def sort(
        self, key_or_list: _Hint, direction: Optional[Union[int, str]] = None
    ) -> MotorCursor[_DocumentType]: ...
    def hint(self, index: Optional[_Hint]) -> MotorCursor[_DocumentType]: ...
    def where(self, code: Union[str, Code]) -> MotorCursor[_DocumentType]: ...
    def max_await_time_ms(self, max_await_time_ms: Optional[int]) -> MotorCursor[_DocumentType]: ...
    def max_time_ms(self, max_time_ms: Optional[int]) -> MotorCursor[_DocumentType]: ...
    def min(self, spec: _Sort) -> MotorCursor[_DocumentType]: ...
    def max(self, spec: _Sort) -> MotorCursor[_DocumentType]: ...
    def comment(self, comment: Any) -> MotorCursor[_DocumentType]: ...
    def allow_disk_use(self, allow_disk_use: bool) -> MotorCursor[_DocumentType]: ...
    def rewind(self) -> MotorCursor[_DocumentType]: ...
    def clone(self) -> MotorCursor[_DocumentType]: ...
    def __copy__(self) -> MotorCursor[_DocumentType]: ...
    def __deepcopy__(self, memo: Any) -> MotorCursor[_DocumentType]: ...

class MotorRawBatchCursor(core.AgnosticRawBatchCursor[_DocumentType]): ...
class MotorCommandCursor(core.AgnosticCommandCursor[_DocumentType]): ...
class MotorRawBatchCommandCursor(core.AgnosticRawBatchCommandCursor[_DocumentType]): ...

class MotorChangeStream(core.AgnosticChangeStream[_DocumentType]):
    def __aiter__(self) -> MotorChangeStream[_DocumentType]: ...
    async def __aenter__(self) -> MotorChangeStream[_DocumentType]: ...

class MotorClientEncryption(core.AgnosticClientEncryption[_DocumentType]):
    async def __aenter__(self) -> MotorClientEncryption[_DocumentType]: ...
    async def get_keys(self) -> MotorCursor[RawBSONDocument]: ...
    async def create_encrypted_collection(
        self,
        database: core.AgnosticDatabase[_DocumentTypeArg],
        name: str,
        encrypted_fields: Mapping[str, Any],
        kms_provider: Optional[str] = None,
        master_key: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> tuple[MotorCollection[_DocumentTypeArg], Mapping[str, Any]]: ...

class MotorGridOutCursor(motor_gridfs.AgnosticGridOutCursor):
    def next_object(self) -> MotorGridOutCursor: ...

class MotorGridOut(motor_gridfs.AgnosticGridOut):
    def __aiter__(self) -> MotorGridOut: ...

class MotorGridIn(motor_gridfs.AgnosticGridIn):
    async def __aenter__(self) -> MotorGridIn: ...

class MotorGridFSBucket(motor_gridfs.AgnosticGridFSBucket):
    async def open_download_stream_by_name(
        self,
        filename: str,
        revision: int = -1,
        session: Optional[core.AgnosticClientSession] = None,
    ) -> MotorGridOut: ...
    async def open_download_stream(
        self, file_id: Any, session: Optional[core.AgnosticClientSession] = None
    ) -> MotorGridOut: ...
    def open_upload_stream(
        self,
        filename: str,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[core.AgnosticClientSession] = None,
    ) -> MotorGridIn: ...
    def open_upload_stream_with_id(
        self,
        file_id: Any,
        filename: str,
        chunk_size_bytes: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        session: Optional[core.AgnosticClientSession] = None,
    ) -> MotorGridIn: ...
    def find(self, *args: Any, **kwargs: Any) -> MotorGridOutCursor: ...
