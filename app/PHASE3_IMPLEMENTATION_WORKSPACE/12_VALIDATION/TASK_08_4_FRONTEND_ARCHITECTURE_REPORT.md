# Task 8.4 Frontend Architecture Report

The former long demo was refactored into Jinja partials, component CSS and native ES modules.

Key modules:

- core app store/API/events;
- prediction and file preview;
- patient form/parser;
- history API/controller/renderer;
- floating assistant API/controller/animation;
- SVG result/history visualizations;
- report controller and reusable modal/toast helpers.

No React/Vue/Tailwind/Bootstrap/bundler was introduced. Compatibility entries `/static/demo.js`, `/static/assistant.js`, `/static/report_export.js` remain available. The desktop UI is a compact analysis workspace, not an oversized landing-page hero.
