"""Trust boundary cho file ảnh upload.

Không tin filename hoặc MIME do client gửi.

File chỉ được chuyển sang bước preprocessing/model sau khi vượt qua:

1. Kiểm tra dữ liệu không rỗng.
2. Kiểm tra dung lượng byte.
3. Kiểm tra extension nếu filename có extension.
4. Kiểm tra MIME chuẩn hoặc MIME trung tính.
5. Kiểm tra magic bytes/file signature.
6. Đối chiếu extension và MIME với format thực tế.
7. Pillow verify.
8. Pillow full decode.
9. Kiểm tra giới hạn pixel và kích thước ảnh.

Mendix có thể gửi file dưới MIME application/octet-stream. MIME này chỉ
được xem là MIME trung tính; nội dung file vẫn phải vượt qua toàn bộ kiểm
tra magic bytes và Pillow.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFile, UnidentifiedImageError

from lung_xray_api.core.exceptions import ImageValidationError


# CHANGE 1:
# Giới hạn số pixel để giảm nguy cơ decompression bomb.
# Ví dụ 20 triệu pixel tương đương ảnh khoảng 4472 x 4472.
MAX_IMAGE_PIXELS = 20_000_000

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Không cho Pillow âm thầm chấp nhận ảnh bị cắt hoặc thiếu dữ liệu.
ImageFile.LOAD_TRUNCATED_IMAGES = False


@dataclass(frozen=True)
class ValidatedImage:
    """Kết quả validation an toàn trước khi preprocessing."""

    content: bytes
    filename: str
    content_type: str | None
    detected_format: str
    width: int
    height: int


class ImageValidator:
    """Validate file JPG/JPEG/PNG tại trust boundary."""

    allowed_extensions = frozenset({".jpg", ".jpeg", ".png"})

    # CHANGE 2:
    # MIME chỉ rõ loại ảnh và phải khớp với nội dung thực tế.
    standard_mime_types = frozenset({"image/jpeg", "image/png"})

    # CHANGE 3:
    # Mendix hoặc một số client có thể không xác định MIME ảnh và gửi
    # application/octet-stream. MIME này được phép đi tiếp nhưng không
    # được dùng làm bằng chứng file là ảnh.
    neutral_mime_types = frozenset({"application/octet-stream"})

    # CHANGE 4:
    # Mapping dùng để kiểm tra extension có khớp magic bytes hay không.
    format_extensions = {
        "jpeg": frozenset({".jpg", ".jpeg"}),
        "png": frozenset({".png"}),
    }

    # CHANGE 5:
    # Mapping dùng để kiểm tra MIME chuẩn có khớp nội dung thật hay không.
    format_mime_types = {
        "jpeg": frozenset({"image/jpeg"}),
        "png": frozenset({"image/png"}),
    }

    # Chỉ cho Pillow thử mở đúng hai format thuộc contract.
    pillow_formats = ("JPEG", "PNG")

    def __init__(self, max_upload_bytes: int) -> None:
        # CHANGE 6:
        # Fail fast nếu cấu hình upload limit bị sai.
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes phải lớn hơn 0")

        self.max_upload_bytes = max_upload_bytes

    def validate(
        self,
        content: bytes,
        filename: str = "upload",
        content_type: str | None = None,
    ) -> ValidatedImage:
        """Validate ảnh upload và trả metadata đã được xác minh.

        Raises:
            ImageValidationError:
                Khi file rỗng, quá lớn, sai extension, sai MIME,
                sai file signature hoặc Pillow không decode được.
        """

        # ------------------------------------------------------------------
        # 1. Kiểm tra dữ liệu và dung lượng
        # ------------------------------------------------------------------

        if not content:
            raise ImageValidationError("File ảnh rỗng")

        if len(content) > self.max_upload_bytes:
            raise ImageValidationError(
                "File ảnh vượt quá giới hạn dung lượng"
            )

        # CHANGE 7:
        # Loại bỏ path phía client và chỉ giữ basename.
        # Ví dụ C:\\fakepath\\xray.jpg -> xray.jpg
        safe_filename = self._sanitize_filename(filename)

        extension = Path(safe_filename).suffix.lower()

        # Vẫn cho phép filename không có extension vì một số client có thể
        # không truyền tên file. Nhưng nếu có extension thì bắt buộc hợp lệ.
        if extension and extension not in self.allowed_extensions:
            raise ImageValidationError(
                "Extension ảnh không được hỗ trợ; chỉ chấp nhận "
                "JPG, JPEG hoặc PNG"
            )

        # ------------------------------------------------------------------
        # 2. Chuẩn hóa và kiểm tra MIME
        # ------------------------------------------------------------------

        # CHANGE 8:
        # Chuẩn hóa MIME:
        # - bỏ khoảng trắng;
        # - chuyển lowercase;
        # - bỏ MIME parameter phía sau dấu chấm phẩy.
        normalized_content_type = self._normalize_content_type(content_type)

        if (
            normalized_content_type is not None
            and normalized_content_type not in self.standard_mime_types
            and normalized_content_type not in self.neutral_mime_types
        ):
            raise ImageValidationError(
                "MIME type ảnh không được hỗ trợ"
            )

        # ------------------------------------------------------------------
        # 3. Kiểm tra magic bytes/file signature
        # ------------------------------------------------------------------

        detected_format = self._detect_format(content)

        if detected_format is None:
            raise ImageValidationError(
                "Nội dung file không phải JPG/JPEG/PNG hợp lệ"
            )

        # CHANGE 9:
        # Nếu filename có extension thì extension phải khớp với nội dung.
        # Ví dụ file tên image.jpg nhưng byte thực tế là PNG sẽ bị từ chối.
        if extension:
            expected_extensions = self.format_extensions[detected_format]

            if extension not in expected_extensions:
                raise ImageValidationError(
                    "Extension file không khớp với định dạng ảnh thực tế"
                )

        # CHANGE 10:
        # Chỉ đối chiếu khi client gửi MIME cụ thể image/jpeg hoặc image/png.
        # application/octet-stream là MIME trung tính nên không đối chiếu.
        if normalized_content_type in self.standard_mime_types:
            expected_mime_types = self.format_mime_types[detected_format]

            if normalized_content_type not in expected_mime_types:
                raise ImageValidationError(
                    "MIME type không khớp với định dạng ảnh thực tế"
                )

        # ------------------------------------------------------------------
        # 4. Pillow verify và full decode
        # ------------------------------------------------------------------

        try:
            # CHANGE 11:
            # Chuyển DecompressionBombWarning thành exception.
            # Nếu không có đoạn này, ảnh vượt MAX_IMAGE_PIXELS nhưng chưa
            # tới mức gấp đôi có thể chỉ phát warning và vẫn đi tiếp.
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "error",
                    Image.DecompressionBombWarning,
                )

                # verify() kiểm tra cấu trúc và tính toàn vẹn file.
                with Image.open(
                    BytesIO(content),
                    formats=self.pillow_formats,
                ) as image:
                    pillow_format = self._normalize_pillow_format(
                        image.format
                    )

                    if pillow_format != detected_format:
                        raise ImageValidationError(
                            "File signature không khớp với định dạng "
                            "Pillow phát hiện"
                        )

                    image.verify()

                # CHANGE 12:
                # Phải mở lại sau verify().
                # load() buộc Pillow giải mã dữ liệu pixel hoàn chỉnh.
                with Image.open(
                    BytesIO(content),
                    formats=self.pillow_formats,
                ) as image:
                    image.load()
                    width, height = image.size

        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise ImageValidationError(
                "Ảnh vượt giới hạn pixel an toàn"
            ) from error

        except UnidentifiedImageError as error:
            raise ImageValidationError(
                "Nội dung file không phải ảnh hợp lệ"
            ) from error

        except (OSError, SyntaxError, ValueError) as error:
            raise ImageValidationError(
                "Không decode được ảnh upload"
            ) from error

        # Không cho ảnh có kích thước rỗng hoặc bất hợp lệ.
        if width <= 0 or height <= 0:
            raise ImageValidationError(
                "Kích thước ảnh không hợp lệ"
            )

        return ValidatedImage(
            content=content,
            filename=safe_filename,
            content_type=normalized_content_type,
            detected_format=detected_format,
            width=width,
            height=height,
        )

    @staticmethod
    def _sanitize_filename(filename: str | None) -> str:
        """Chỉ giữ basename, không tin path client gửi lên."""

        raw_filename = (filename or "upload").strip()

        if not raw_filename:
            return "upload"

        # Path trên Linux không tự hiểu backslash của Windows.
        normalized_path = raw_filename.replace("\\", "/")
        safe_filename = Path(normalized_path).name

        return safe_filename or "upload"

    @staticmethod
    def _normalize_content_type(
        content_type: str | None,
    ) -> str | None:
        """Chuẩn hóa MIME thành dạng lowercase không có parameters."""

        if content_type is None:
            return None

        normalized = content_type.split(";", maxsplit=1)[0].strip().lower()

        # MIME rỗng được xem như client không cung cấp MIME.
        return normalized or None

    @staticmethod
    def _normalize_pillow_format(
        pillow_format: str | None,
    ) -> str | None:
        """Chuyển format của Pillow về format nội bộ."""

        if pillow_format is None:
            return None

        normalized = pillow_format.strip().lower()

        if normalized == "jpg":
            return "jpeg"

        return normalized

    @staticmethod
    def _detect_format(content: bytes) -> str | None:
        """Phát hiện JPEG/PNG bằng magic bytes."""

        # JPEG bắt đầu bằng FF D8 FF.
        if content.startswith(b"\xff\xd8\xff"):
            return "jpeg"

        # PNG bắt đầu bằng signature 8 byte cố định.
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"

        return None
