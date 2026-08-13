
# Gemini Online Assistant Patch

This patch converts the existing controlled offline assistant into a hybrid assistant:

1. Existing safety guard and production Knowledge Base run first.
2. Safe, approved context may be sent to Gemini.
3. Raw X-ray images, thumbnails, patient names, patient codes, local paths and history records are not sent.
4. Gemini requests use `store=False`.
5. When Gemini is unavailable, the existing offline assistant remains operational.

## Critical security action

The API key visible in the screenshot must be revoked before use. This package intentionally does not contain that key or any replacement key.

After applying the patch:

```powershell
.\scripts\SET_GEMINI_KEY.ps1
python .\scripts\test_gemini_connection.py
python -m lung_xray_api
```

The setup script writes the newly rotated key only to the local `.env` file.
