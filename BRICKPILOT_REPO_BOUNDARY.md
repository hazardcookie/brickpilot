# Brickpilot Repo Boundary

This repository is the core Brickpilot driving software repo. It should contain
the code that runs on the comma, plus normal build/runtime support needed by
the openpilot/sunnypilot fork.

Split-out local operations live in sibling repositories:

- `../brickpilot-web-ui`: local React/Node operations UI and Telegram bot.
- `../brickpilot-tools`: log ingest, manual labeler, ML/research, recovery, and
  data reconciliation tooling.

Drive data, logs, videos, audio, databases, generated labeler output, and
analysis artifacts must stay outside this repo under:

- `/Users/brick/BrickpilotDriveDB`

The `main` branch was created as a full 0.3.16.0 source snapshot from
`/Users/brick/comma-dev/sunnypilot-src` staging commit
`5936f534bd67d2f5860387e4bbaa519eed97a849`.

The `staging` branch is the cleaned Brickpilot-core branch. It intentionally
does not carry the old web UI, OpenClaw plugin, drive-test/manual-labeler/ML
scripts, or general desktop analysis tools.
