# Task: make.fun ai-happy-01 entry

Build a program (main.py, Python 3.13) in this repo root that:
1. Writes one image to /output/entry.png (PNG or JPEG, max 1 MiB, max 1024x1024 px)
2. Is fully deterministic (two runs must write byte-identical files)
3. Uses NO network at runtime
4. Goal: make an AI image-judge HAPPY. Style/subject is free - aim for something charming, warm, delightful.

Rules:
- main.py must be at repo root, stdlib only (no pip installs at runtime)
- Repo needs an OSI-approved LICENSE (MIT, full text with "Copyright (c) 2026 kamensr")
- IMPORTANT: develop by writing main.py with a tool call, then REVISE/EDIT it in at least one later assistant message (min 2 file-writing turns on the same file)
- Test with MAKEFUN_OUTPUT env var to redirect output dir
- Commit at the end, do NOT push
