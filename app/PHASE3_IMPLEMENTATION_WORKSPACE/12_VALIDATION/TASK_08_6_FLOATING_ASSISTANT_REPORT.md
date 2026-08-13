# Task 8.6 Floating Assistant Report

Implemented a bottom-right floating launcher and viewport-aware panel. Mobile uses full-screen presentation. The assistant supports open/close/minimize, new conversation, suggestions, Enter/Shift+Enter, source/disclaimer details and a skip-reveal control.

The thinking label is `Đang tra cứu kho kiến thức ngoại tuyến...`. Answers reveal by bounded chunks rather than per-character updates; reduced-motion renders immediately. Greeting, thanks, goodbye, help, capabilities and start-over are deterministic local intents. Current prediction context comes only from the central store and is reset on a new/failed/reset analysis.
