# Drive-Test Analysis Harness

This harness compares local comma/sunnypilot route logs across driving models and settings without modifying any driving or control code. It reads route segments through `openpilot.tools.lib.logreader.LogReader`, stores metrics in SQLite/CSV, writes a Markdown report, and generates PNG plots.

VINs are redacted in generated outputs. `carFw` is not dumped; reports only include high-level firmware counts/markers.

## Route Catalog

Edit `scripts/drive_tests/route_catalog.yaml` to add routes, notes, settings, warmup skip time, and thresholds. The default `warmup_skip_sec` is 90 seconds so each drive can be scored as both all-data and post-calibration warmup.

The North Nevada route is weighted lower by default because it includes an intentionally aggressive low-speed neighborhood turn.

## Commands

Authenticate if needed:

```bash
python3 tools/lib/auth.py
```

Run all analysis:

```bash
cd ~/comma-dev/sunnypilot-src
source .venv/bin/activate
python3 scripts/drive_tests/analyze_routes.py \
  --catalog scripts/drive_tests/route_catalog.yaml \
  --out analysis/drive_tests \
  --max-segments 80
```

Generate report:

```bash
python3 scripts/drive_tests/report.py \
  --db analysis/drive_tests/results.sqlite \
  --out analysis/drive_tests/report.md
```

Generate plots:

```bash
python3 scripts/drive_tests/plots.py \
  --db analysis/drive_tests/results.sqlite \
  --out analysis/drive_tests/plots
```

## Voice Bookmarks

For local, in-drive spoken/manual bookmarks that can be imported into the generated manual labeler drafts, see [`VOICE_BOOKMARKS.md`](VOICE_BOOKMARKS.md):

```bash
python3 scripts/drive_tests/voice_bookmarker.py record --name commute-test
python3 scripts/drive_tests/voice_bookmarker.py import <voice-session-dir> --labeler-dir <manual_drive_labeler-dir>
```

The helper stays local-only and supports manual transcript fallback when STT/audio dependencies are absent.

## Outputs

The analyzer creates:

- `analysis/drive_tests/results.sqlite`
- `analysis/drive_tests/summary.csv`
- `analysis/drive_tests/segment_summary.csv`
- `analysis/drive_tests/lateral_events.csv`
- `analysis/drive_tests/pinned_bursts.csv`
- `analysis/drive_tests/acceleration_events.csv`
- `analysis/drive_tests/stop_go_events.csv`
- `analysis/drive_tests/report.md`
- `analysis/drive_tests/plots/*.png`

## Segment Discovery

For each route, the analyzer tries segment `0..N` until `missing_stop_after` consecutive missing logs are found, or `--max-segments` is reached. It tries rlogs first. By default it uses the LogReader `/a` selector as a qlog fallback when an rlog is missing and records a warning because qlog-derived metrics are lower fidelity.

Disable qlog fallback with:

```bash
python3 scripts/drive_tests/analyze_routes.py --no-qlog-fallback
```

## Metrics

The harness records all-data and post-warmup metrics for each route and segment. It also splits route-level metrics by speed regime:

- `stopped`: below 1 mph
- `low_neighborhood`: 1 to 20 mph
- `neighborhood`: 20 to 35 mph
- `backroad`: 35 to 55 mph
- `highway`: above 55 mph

Turn demand is binned by absolute desired lateral acceleration:

- `straightish`: below 0.25
- `mild_curve`: 0.25 to 0.75
- `medium_curve`: 0.75 to 1.25
- `hard_curve`: above 1.25

Pinned lateral output uses `abs(torqueState.output) >= 0.98`. Pinned bursts are grouped when consecutive pinned samples are separated by no more than 0.20 seconds.

Longitudinal catch-up events start when clean longActive, no-lead-relaxed samples have a set-speed deficit of at least 5 mph while already moving above 3 mph. Stop-go events start below 0.5 mph or at standstill and end above 5 mph.
