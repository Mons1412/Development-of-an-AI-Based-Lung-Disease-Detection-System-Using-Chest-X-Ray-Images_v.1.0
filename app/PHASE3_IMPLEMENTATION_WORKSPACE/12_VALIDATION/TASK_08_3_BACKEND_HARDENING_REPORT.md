# Task 8.3 Backend Hardening Report

Implemented:

- shared probability normalization (`1e-4`, `math.fsum`);
- bounded chunked upload cho legacy và persisted endpoints;
- patient code optional, name required for identified case;
- Knowledge Base metadata provider tách khỏi assistant startup;
- history remains usable when KB/assistant is unavailable;
- real client loopback gate and loopback server configuration gate;
- `no-store` headers for analyses/report;
- UTC storage and explicit timezone offset for calendar filters;
- safe validation/persistence error responses;
- report provenance persisted with each record.

Legacy `/predict` contracts remain non-persistent.
