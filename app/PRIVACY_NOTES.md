# Data and Privacy Notes

## Stored locally

- analysis UUID;
- confirmed patient/case display metadata;
- sanitized source filename;
- normalized probabilities and model metadata;
- derived thumbnail after re-encoding;
- report provenance;
- timestamps.

## Not stored

- original full-resolution upload;
- EXIF metadata;
- chat transcript;
- generated PDF files;
- chat transcripts in the local application.

## Optional Gemini online mode

The assistant is local by default. When a local administrator explicitly enables
Gemini online mode, the application sends only the resolved application intent
as a canonical non-identifying question, non-identifying model output, approved
local reference text, and source IDs to Gemini. Raw chat text is not forwarded.
The server does not send the original image, thumbnail, filename, patient display
name, patient code, or local analysis ID.

Do not enter patient identifiers, contact details, or clinical records in the
chat. The application blocks common identifier patterns and constructs the
provider request from the resolved intent rather than raw free text. This is
still not a substitute for user judgment or a full data-loss-prevention system.
The Gemini request uses `store=false`; external-provider handling remains subject
to Google's applicable terms and settings.

## Network boundary

The assistant and model run locally. Sensitive history/report APIs require loopback configuration and an actual loopback client. This is containment for a single-machine academic app, not an authorization system for LAN/Internet deployment.

## Logging and caching

Patient identity is not intentionally logged at INFO level. Analyses, thumbnail and report responses use `Cache-Control: no-store`.

## Deletion

Deleting a record removes database metadata and attempts to remove its thumbnail. File-system failure leaves a database cleanup job for retry on startup.
