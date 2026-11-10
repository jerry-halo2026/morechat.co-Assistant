# Confirmed synthetic execution plan
Use U001 once, SRC001 1000-6000; DO001, EB001. Preserve original audio, no music.
Explicitly adopt T001. A001 uses source audio 1000-6000 with review_refs=[R001]; the current synthetic audio review covers 0-8000. No creative exception or policy change is used.

Direct 2 snapshot in `timeline.json`:
- planned source range: 1000-6000
- boundary: EB001
- safe-in window: 900-1200
- safe-out window: 5900-6200
- allowed adjustments: none

Execute Step 0 is already completed in this ready fixture: EB001 is supported, R001 covers the selected audio/video range, and the final timeline remains SRC001 1000-6000.

| event | D2 planned | Step 0 verified | delta / reason | within D2 allowance |
|---|---|---|---|---|
| E001 | 1000-6000 | 1000-6000 | 0 / no calibration needed | yes |
