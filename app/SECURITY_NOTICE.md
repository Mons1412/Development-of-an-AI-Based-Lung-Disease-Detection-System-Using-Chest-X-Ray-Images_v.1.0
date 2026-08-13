
# Security notice

The API key shown in the conversation screenshot is considered exposed.

Required action:

1. Delete or revoke that key in Google AI Studio.
2. Create a new key.
3. Apply this source patch.
4. Run `scripts/SET_GEMINI_KEY.ps1` and paste the new key locally.
5. Do not upload `.env`, screenshots of the key, or the release folder containing a key.

The patch contains no API key and never sends the key to the browser.
