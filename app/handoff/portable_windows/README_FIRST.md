# Lung X-ray FastAPI - Portable Windows x64

Đây là bản chạy độc lập dành cho Windows 10/11 64-bit. Gói đã chứa sẵn:

- Python 3.12.10 64-bit;
- FastAPI và toàn bộ dependency runtime;
- TensorFlow 2.20.0, Keras 3.13.2;
- source của `02_fastapi_inference`;
- model Lung X-ray phiên bản 1.1.0;
- tài liệu API và Mendix handoff.

Khách hàng không cần cài Python, không cần tạo `.venv`, không cần chạy
`pip install` và không cần Internet để khởi động ứng dụng.

## Chạy ứng dụng

1. Giải nén toàn bộ ZIP vào một thư mục trên máy Windows 64-bit.
2. Mở thư mục vừa giải nén.
3. Chạy:

```text
START_API.cmd
```

4. Đợi đến khi console hiện `Application startup complete`.
5. Mở:

```text
http://127.0.0.1:8000/demo
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Dừng ứng dụng bằng `Ctrl+C` trong cửa sổ console.

Nếu cổng 8000 đang được chương trình khác sử dụng, chạy từ Command Prompt:

```text
START_API.cmd 8080
```

Sau đó mở `http://127.0.0.1:8080/demo`.

## Tự kiểm tra gói

Chạy:

```text
VERIFY_PACKAGE.cmd
```

Lệnh này kiểm tra Python portable, checksum model, load/warm-up model thật và
health routes của FastAPI. Lần load model đầu tiên có thể mất từ vài chục giây
đến khoảng hai phút tùy máy và phần mềm antivirus.

## Yêu cầu máy khách

- Windows 10/11 64-bit;
- CPU 64-bit hiện đại;
- tối thiểu 4 GB RAM, khuyến nghị 8 GB RAM;
- đủ dung lượng để giải nén toàn bộ gói.

Không chạy trực tiếp file trong cửa sổ xem trước của ZIP. Phải giải nén đầy đủ
để Python và các DLL native hoạt động đúng.

## Cấu trúc chính

```text
START_API.cmd          Lệnh chạy dành cho khách hàng
VERIFY_PACKAGE.cmd     Lệnh tự kiểm tra
app/                   FastAPI source, model, docs và tests
runtime/               Python và dependency portable
PACKAGE_INFO.txt       Phiên bản và nguồn đóng gói
PACKAGE_MANIFEST.txt   Danh sách file và dung lượng trong gói
```

File `.sha256` nằm cạnh ZIP dùng để kiểm tra tính toàn vẹn của toàn bộ archive.

## Lưu ý

- API mặc định chỉ lắng nghe tại `127.0.0.1`, không tự mở ra Internet/LAN.
- API key mặc định tắt trong bản local portable.
- Không đổi tên hoặc di chuyển riêng các thư mục `app` và `runtime`.
- Kết quả chỉ phục vụ mục đích học thuật, không thay thế chẩn đoán của bác sĩ.
