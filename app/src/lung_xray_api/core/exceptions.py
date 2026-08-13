"""Ngoại lệ domain dùng chung cho Phase 02.

Các exception này tách lỗi nghiệp vụ khỏi FastAPI để application service
không phụ thuộc framework HTTP.
"""


class PersistenceError(Exception):
    """Local analysis-history persistence could not complete safely."""


class DatabaseBusyError(PersistenceError):
    """SQLite could not acquire its bounded local lock in time."""


class SchemaVersionError(PersistenceError):
    """Database schema is incompatible with this application version."""


class AnalysisNotFoundError(PersistenceError):
    """Requested local analysis-history record does not exist."""


class ThumbnailCleanupError(PersistenceError):
    """Thumbnail cleanup/rollback needs explicit retry instead of silent loss."""


class LungXrayAPIError(Exception):
    """Base exception cho lỗi có chủ đích trong service."""


class ArtifactError(LungXrayAPIError):
    """Artifact thiếu, sai checksum hoặc sai contract."""


class ImageValidationError(LungXrayAPIError):
    """Ảnh upload không vượt qua trust boundary."""


class ModelRuntimeError(LungXrayAPIError):
    """Model runtime chưa sẵn sàng hoặc trả output không hợp lệ."""


class ServiceUnavailableError(LungXrayAPIError):
    """Service chưa ready để xử lý inference."""
