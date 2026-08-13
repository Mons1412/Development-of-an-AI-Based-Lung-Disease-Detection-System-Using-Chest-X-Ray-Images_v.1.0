# SQLite Schema Final

Schema version: **2**

## analysis_history

Lưu UUID, optional patient code, required display name cho ca định danh, normalized search key, source/confirmation mode, filename provenance, sanitized original filename, thumbnail relative filename, predicted label, ba normalized probabilities, model/KB version, disclaimer, source IDs, latency và timestamps UTC.

## thumbnail_cleanup_queue

Record được xóa và cleanup job được tạo trong cùng transaction. Thumbnail được xóa sau transaction; lỗi file system giữ job để retry ở startup. Không dùng blind deletion của `*.delete-pending`.

## Migration invariant

Migration tăng dần, idempotent và không xóa database người dùng. Startup xác minh table, columns, indexes và schema version. Dữ liệu cũ được migrate sang schema 2 với provenance mặc định an toàn.
