# Task 8.9 Final Regression Report

Final status: **READY_FOR_USER_TESTING**  
This is not `READY_FOR_RELEASE`; Task 09 and Windows smoke testing were not executed.

## Automated evidence

- Full pytest: 288 passed, 6 skipped.
- Coverage: 84%.
- Python compileall: PASS.
- JavaScript syntax (`node --check`): PASS.
- Workspace validation: PASS.
- Production KB validation: PASS, 21 runtime items.
- Clinical gate: 34 clinical-sensitive development items remain pending and excluded from production.
- Static whitespace/import checks: PASS.

## Skipped/unavailable

Six real-model tests were skipped because the source-review bundle intentionally excludes model binaries and artifact manifests. Ruff and Pyright could not be installed/executed because the tools were absent and the package gateway returned HTTP 503. Their unavailability is recorded rather than reported as a pass.

## Validated contracts

- legacy prediction compatibility;
- persisted confirmed/anonymous analysis;
- optional patient code;
- strict filename parser;
- bounded upload;
- shared probability normalization;
- schema v2 migration/verification;
- Unicode search;
- cleanup queue and retry;
- loopback/no-store privacy boundary;
- history CRUD, thumbnail and report;
- assistant safety/conversation/context;
- modular UI static contracts;
- production Knowledge Base gate.

## Manual user tests still required

Windows Python 3.12 install, real model smoke inference, desktop/tablet/mobile visual QA, keyboard/focus behavior, PDF print rendering, restart persistence and offline operation.
