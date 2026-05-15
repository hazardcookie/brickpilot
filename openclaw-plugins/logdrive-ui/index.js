import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const execFileAsync = promisify(execFile);
const PLUGIN_ID = "logdrive-ui";
const ROUTE_NAMESPACE = "logdrive";
// UI state lives on the gateway host, but never in the repo. Route data/DB/analyzers
// belong on the MacBook Pro under BrickpilotDriveDB. Keep these defaults absolute
// so Telegram /logdrive cannot regress to repo-local analysis/... outputs.
const GATEWAY_STATE_ROOT = "/Users/synth/.openclaw/logdrive-ui";
const RUNS_ROOT = path.join(GATEWAY_STATE_ROOT, "runs");
const MACBOOK_HOST = "brick@bricks-macbook-pro.local";
const MACBOOK_REPO_ROOT = "/Users/brick/comma-dev/sunnypilot-src";
const MACBOOK_DATA_ROOT = "/Users/brick/BrickpilotDriveDB";
const MACBOOK_RUNS_ROOT = path.join(MACBOOK_DATA_ROOT, "logdrive_runs");
const RAW_ROOT = path.join(MACBOOK_DATA_ROOT, "imports/raw/from_comma");
const ANALYSIS_ROOT = path.join(MACBOOK_DATA_ROOT, "logdrive_runs");
const LABELER_ROOT = path.join(MACBOOK_DATA_ROOT, "labeler_outputs");
// Prefer the fixed IP first: mDNS on car Wi‑Fi can be painfully slow/flaky.
const COMMA_HOSTS = ["comma@192.168.1.138", "comma@comma-af6497bd.lan"];
const LOG_FILES = new Set(["rlog.bz2", "rlog.zst", "rlog", "qlog.bz2", "qlog.zst", "qlog"]);
const VIDEO_FILES = new Set(["fcamera.hevc", "dcamera.hevc", "ecamera.hevc", "qcamera.ts", "qcamera.hevc"]);

const DRIVE_TYPES = {
  test: { label: "Test drive", value: "test", rideType: "test drive", includeVideo: false },
  validation: { label: "Label validation drive", value: "validation", rideType: "label validation", includeVideo: true },
  normal: { label: "Normal drive", value: "normal", rideType: "normal drive", includeVideo: false },
};

function nowRunId() {
  const d = new Date();
  return d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "unknown size";
  const mib = bytes / 1024 / 1024;
  return mib >= 1024 ? `${(mib / 1024).toFixed(1)} GiB` : `${mib.toFixed(0)} MiB`;
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "unknown duration";
  const mins = Math.max(1, Math.round(seconds / 60));
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h} hr ${m} min` : `${h} hr`;
}

function formatMiles(miles) {
  if (!Number.isFinite(miles) || miles <= 0) return "miles unknown";
  return `${miles < 10 ? miles.toFixed(1) : Math.round(miles).toString()} mi`;
}

const TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

function formatTimeRange(c) {
  const startMs = Number(c.startMs);
  const endMs = Number(c.endMs);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return "time unknown";
  const start = TIME_FORMATTER.format(new Date(startMs));
  const end = TIME_FORMATTER.format(new Date(endMs));
  const endNoZone = end.replace(/\s+[A-Z]{2,4}$/, "");
  return `${start}–${endNoZone}`;
}

function candidateLine(c) {
  const segRange = c.segmentFirst === c.segmentLast ? `${c.segmentFirst}` : `${c.segmentFirst}–${c.segmentLast}`;
  const routeShort = c.routeId;
  return [
    `*${c.number}) ${routeShort}*`,
    `🕒 *Time:* ${formatTimeRange(c)} (${formatDuration(c.durationSec)})`,
    `🛣️ *Drive:* ${formatMiles(c.miles)} • ${c.segmentCount} seg [${segRange}] • ${formatBytes(c.sizeBytes)}`,
    `ℹ️ *Note:* ${c.reason}`,
  ].join("\n");
}

function safeRouteDirName(routeId) {
  return String(routeId).replace(/[^A-Za-z0-9_.=-]+/g, "_").slice(0, 180);
}

function routeLabelFor(candidate, driveType) {
  const compactRun = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  return `logdrive_ui_${compactRun}_${driveType.value}_${safeRouteDirName(candidate.routeId)}`;
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'"'"'`)}'`;
}

async function runMacBook(command, { timeout = 60000, maxBuffer = 1024 * 1024 * 8 } = {}) {
  return await execFileAsync("ssh", [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    "-o", "ConnectionAttempts=2",
    "-o", "NumberOfPasswordPrompts=0",
    MACBOOK_HOST,
    command,
  ], { timeout, maxBuffer });
}

function segmentFiles(candidate, segment) {
  const entry = (candidate.segmentFiles || []).find((s) => Number(s.segment) === Number(segment));
  return entry?.files || [];
}

function localRouteRoot(candidate) {
  return path.join(RAW_ROOT, safeRouteDirName(candidate.routeId));
}

function localSegmentsDir(candidate) {
  return path.join(localRouteRoot(candidate), "segments");
}

function copyItemsFor(candidate, driveType) {
  const wanted = new Set(driveType.includeVideo ? [...LOG_FILES, ...VIDEO_FILES] : [...LOG_FILES]);
  const items = [];
  for (const segment of candidate.segments || []) {
    for (const file of segmentFiles(candidate, segment)) {
      if (!wanted.has(file.name)) continue;
      const kind = VIDEO_FILES.has(file.name) ? "video" : "logs";
      items.push({
        segment,
        fileName: file.name,
        kind,
        expectedSizeBytes: Number(file.sizeBytes) || 0,
        remotePath: `/data/media/0/realdata/${candidate.routeId}--${segment}/${file.name}`,
        localPath: path.join(localSegmentsDir(candidate), `${candidate.routeId}--${segment}`, file.name),
      });
    }
  }
  return items;
}

async function runSsh(host, command) {
  // The comma is reachable but can have multi-second jitter on home Wi-Fi;
  // keep this probe patient enough for real post-drive use instead of
  // false-failing after a single 2s mDNS/SSH hiccup.
  return await execFileAsync("ssh", [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    "-o", "ConnectionAttempts=2",
    "-o", "NumberOfPasswordPrompts=0",
    "-o", "PreferredAuthentications=publickey",
    "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=2",
    host,
    command,
  ], {
    timeout: 30000,
    maxBuffer: 1024 * 1024 * 8,
  });
}

async function discoverOnComma() {
  const py = String.raw`
import json, os, re, socket, subprocess, time

def cmd(args):
    try:
        return subprocess.check_output(args, cwd='/data/openpilot', stderr=subprocess.DEVNULL, text=True, timeout=1.5).strip()
    except Exception:
        return ''

base='/data/media/0/realdata'
routes={}
for name in os.listdir(base):
    m=re.match(r'([0-9a-f]+--[0-9a-f]+)--(\d+)$', name)
    if not m: continue
    route=m.group(1); seg=int(m.group(2)); p=os.path.join(base,name)
    try: st=os.stat(p)
    except OSError: continue
    size=0; files=[]; segment_files=[]
    for fn in os.listdir(p):
        fp=os.path.join(p,fn)
        if not os.path.isfile(fp): continue
        if fn.startswith(('rlog','qlog')) or fn in ('fcamera.hevc','ecamera.hevc','dcamera.hevc','qcamera.ts','qcamera.hevc'):
            try:
                fsz=os.path.getsize(fp); size += fsz; files.append(fn); segment_files.append({'name': fn, 'sizeBytes': fsz})
            except OSError: pass
    r=routes.setdefault(route, {'segments': [], 'size': 0, 'mtimes': [], 'segment_mtimes': {}, 'segment_files': {}, 'files': set()})
    r['segments'].append(seg); r['size'] += size; r['mtimes'].append(st.st_mtime); r['segment_mtimes'][seg]=st.st_mtime; r['segment_files'][seg]=segment_files; r['files'].update(files)
out=[]
for i,(route,r) in enumerate(sorted(routes.items(), key=lambda kv:max(kv[1]['mtimes']), reverse=True)[:12], start=1):
    segs=sorted(r['segments'])
    start_s = r['segment_mtimes'].get(segs[0], min(r['mtimes']))
    duration_s = max(60, len(segs) * 60)
    out.append({
      'number': i,
      'routeId': route,
      'segmentCount': len(segs),
      'segments': segs,
      'segmentFiles': [{'segment': seg, 'files': r['segment_files'].get(seg, [])} for seg in segs],
      'segmentFirst': segs[0],
      'segmentLast': segs[-1],
      'sizeBytes': r['size'],
      'startMs': int(start_s*1000),
      'endMs': int((start_s + duration_s)*1000),
      'durationSec': duration_s,
      'has': sorted(r['files'])[:10],
      'reason': ('single-segment candidate; may be tail/parking/offroad' if len(segs)==1 else f'{len(segs)} recent segments with logs/video')
    })
print(json.dumps({
  'hostname': socket.gethostname(),
  'branch': cmd(['git', 'branch', '--show-current']),
  'commit': cmd(['git', 'rev-parse', '--short=12', 'HEAD']),
  'candidates': out,
}))
`;
  try {
    return await Promise.any(COMMA_HOSTS.map(async (host) => {
      const { stdout } = await runSsh(host, `python3 - <<'PY'\n${py}\nPY`);
      const parsed = JSON.parse(stdout.trim() || "{}");
      return { host, ...parsed, candidates: parsed.candidates || [] };
    }));
  } catch (err) {
    const reasons = err?.errors?.map((e) => e?.message || String(e)).join("; ");
    throw new Error(reasons || err?.message || "comma not reachable");
  }
}

async function writeUiState(runId, state) {
  const dir = path.join(RUNS_ROOT, runId);
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, "telegram_ui_state.json"), JSON.stringify(state, null, 2) + "\n", "utf8");
}

async function readUiState(runId) {
  return JSON.parse(await readFile(path.join(RUNS_ROOT, runId, "telegram_ui_state.json"), "utf8"));
}

function isBenignTelegramEditError(err) {
  const s = String(err?.message || err || "").toLowerCase();
  return s.includes("message is not modified") || s.includes("query is too old") || s.includes("response timeout expired");
}

async function safeTelegramCall(fn) {
  try { return await fn?.(); } catch (err) {
    if (!isBenignTelegramEditError(err)) throw err;
    return null;
  }
}

async function hasAnyFileUnder(dir, depth = 2) {
  if (depth < 0) return false;
  let entries;
  try { entries = await readdir(dir, { withFileTypes: true }); } catch { return false; }
  for (const entry of entries) {
    const child = path.join(dir, entry.name);
    if (entry.isFile()) {
      try { if ((await stat(child)).size > 0) return true; } catch {}
    } else if (entry.isDirectory() && await hasAnyFileUnder(child, depth - 1)) {
      return true;
    }
  }
  return false;
}

async function findAlreadyIngestedRouteIds() {
  // Only hide routes with a successful verification manifest. A partial raw
  // directory from a failed copy must stay selectable so Dan can retry ingest.
  const py = String.raw`
import json
from pathlib import Path
runs=Path(${JSON.stringify(MACBOOK_RUNS_ROOT)})
ids=set()
if runs.exists():
  for mf in runs.glob('*/copy_verify_manifest.json'):
    try:
      data=json.loads(mf.read_text())
      if data.get('ok') and data.get('routeId'):
        ids.add(str(data['routeId']))
    except Exception:
      pass
print(json.dumps(sorted(ids)))
`;
  try {
    const { stdout } = await runMacBook(`python3 - <<'PY'
${py}
PY`, { timeout: 30000 });
    return new Set(JSON.parse(stdout.trim() || "[]"));
  } catch {
    return new Set();
  }
}

function filesForDriveType(candidate, driveType) {
  const wanted = new Set([...LOG_FILES, ...(driveType.includeVideo ? VIDEO_FILES : [])]);
  const items = [];
  for (const segmentEntry of candidate.segmentFiles || []) {
    for (const file of segmentEntry.files || []) {
      const sizeBytes = Number(file.sizeBytes) || 0;
      // openpilot often leaves zero-byte camera/log placeholders on the final
      // segment while files are closing. Do not require or copy placeholders.
      if (!wanted.has(file.name) || sizeBytes <= 0) continue;
      const kind = VIDEO_FILES.has(file.name) ? "video" : "logs";
      items.push({ segment: segmentEntry.segment, name: file.name, sizeBytes, kind });
    }
  }
  return items;
}

async function copyAndVerifyRoute(state, candidate, driveType) {
  const destRoot = path.join(RAW_ROOT, safeRouteDirName(candidate.routeId));
  const items = filesForDriveType(candidate, driveType);
  const results = [];
  await runMacBook(`mkdir -p ${shellQuote(destRoot)} ${shellQuote(path.join(MACBOOK_RUNS_ROOT, state.runId))}`, { timeout: 30000 });
  for (const item of items) {
    const segDirName = safeRouteDirName(`${candidate.routeId}--${item.segment}`);
    const localDir = path.join(destRoot, "segments", segDirName);
    const remotePath = `/data/media/0/realdata/${candidate.routeId}--${item.segment}/${item.name}`;
    const localPath = path.join(localDir, item.name);
    let ok = false;
    let actualSize = 0;
    let error = "";
    try {
      await runMacBook(`mkdir -p ${shellQuote(localDir)}`, { timeout: 30000 });
      // Copy through the gateway as a stream so bytes land on the MacBook Pro
      // even if the MacBook cannot directly SSH to the comma on a given Wi-Fi hop.
      const remoteWrite = `cat > ${shellQuote(localPath)}`;
      const copyCommand = [
        "set -o pipefail",
        `ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=2 -o NumberOfPasswordPrompts=0 ${shellQuote(state.host)} cat ${shellQuote(remotePath)} | ssh -o BatchMode=yes -o ConnectTimeout=8 -o ConnectionAttempts=2 -o NumberOfPasswordPrompts=0 ${shellQuote(MACBOOK_HOST)} ${shellQuote(remoteWrite)}`,
      ].join("\n");
      await execFileAsync("bash", ["-lc", copyCommand], { timeout: 300000, maxBuffer: 1024 * 1024 });
      const statScript = [
        `python3 - <<'PY'`,
        `import os, json`,
        `p=${JSON.stringify(localPath)}`,
        `print(json.dumps({"size": os.path.getsize(p) if os.path.exists(p) else 0}))`,
        `PY`,
      ].join("\n");
      const { stdout } = await runMacBook(statScript, { timeout: 30000, maxBuffer: 1024 * 1024 });
      const parsed = JSON.parse((stdout.trim().split("\n").pop()) || "{}");
      actualSize = Number(parsed.size) || 0;
      ok = actualSize > 0 && (!Number.isFinite(item.sizeBytes) || actualSize === item.sizeBytes);
      if (!ok) error = `size mismatch expected ${item.sizeBytes || "nonzero"}, got ${actualSize}`;
    } catch (err) {
      error = err?.message || String(err);
    }
    results.push({ ...item, remotePath, localPath, actualSize, ok, error });
  }
  const logCount = results.filter((r) => r.kind === "logs" && r.ok).length;
  const videoCount = results.filter((r) => r.kind === "video" && r.ok).length;
  const failedFiles = results.filter((r) => !r.ok);
  const missingKinds = [];
  if (logCount === 0) missingKinds.push("logs");
  if (driveType.includeVideo && videoCount === 0) missingKinds.push("video");
  const ok = results.length > 0 && failedFiles.length === 0 && missingKinds.length === 0;
  const manifest = {
    runId: state.runId,
    routeId: candidate.routeId,
    driveType: driveType.value,
    rideType: driveType.rideType,
    includeVideo: driveType.includeVideo,
    copyHost: MACBOOK_HOST,
    destinationRoot: destRoot,
    copiedAt: new Date().toISOString(),
    ok,
    missingKinds,
    counts: { files: results.length, logs: logCount, video: videoCount, failed: failedFiles.length },
    failedFiles: failedFiles.map((r) => ({ segment: r.segment, name: r.name, kind: r.kind, expectedSize: r.sizeBytes, actualSize: r.actualSize, error: r.error, localPath: r.localPath })),
    files: results,
  };
  const manifestPath = path.join(MACBOOK_RUNS_ROOT, state.runId, "copy_verify_manifest.json");
  const localManifestPath = path.join(RUNS_ROOT, state.runId, "copy_verify_manifest.json");
  await writeFile(localManifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");
  await runMacBook(`cat > ${shellQuote(manifestPath)} <<'JSON'\n${JSON.stringify(manifest, null, 2)}\nJSON`, { timeout: 30000 });
  return { ...manifest, manifestPath, localManifestPath };
}

async function importDriveDbValidation(state, candidate, driveType, copyResult) {
  if (!driveType.includeVideo) return { skipped: true, reason: "not label-validation" };
  const script = String.raw`
import json
from pathlib import Path
from scripts.drive_tests.brickpilot_db.config import load_config
from scripts.drive_tests.brickpilot_db.ingest import import_root
from scripts.drive_tests.brickpilot_db.store import DriveStore
route_id = ${JSON.stringify(candidate.routeId)}
run_id = ${JSON.stringify(state.runId)}
dest = Path(${JSON.stringify(copyResult.destinationRoot)})
payload = import_root(dest, None, dry_run=False)
cfg = load_config(None)
store = DriveStore(cfg); store.migrate()
segments = sorted({int(p.name.rsplit('--', 1)[-1]) for p in (dest / 'segments').glob(route_id + '--*') if p.is_dir()})
route_uuid = store.upsert_route(route_id, source_device=cfg.source_host_role, drive_type='label-validation', route_label=route_id, segment_count=len(segments), metadata={'logdrive_run_id': run_id, 'review_auto_created': True, 'source': 'telegram_logdrive_ui'})
inbox_id = store.create_inbox('logdrive_label_validation', 'verified /logdrive label-validation drives awaiting human review')
job_id = store.upsert_review_job(inbox_id, route_uuid, None, status='pending', selected=True, ride_type='label validation', route_label=route_id)
store.commit()
payload['review_job'] = {'created': True, 'inbox_id': inbox_id, 'review_job_id': job_id, 'route_uuid': route_uuid, 'route_id': route_id, 'segments': segments}
print(json.dumps(payload, indent=2, sort_keys=True, default=str))
`;
  const outPath = path.join(MACBOOK_RUNS_ROOT, state.runId, "drive_db_import.json");
  const { stdout } = await runMacBook(`cd ${shellQuote(MACBOOK_REPO_ROOT)} && .venv/bin/python - <<'PY' > ${shellQuote(outPath)}\n${script}\nPY\ncat ${shellQuote(outPath)}`, { timeout: 300000, maxBuffer: 4 * 1024 * 1024 });
  return JSON.parse(stdout.trim() || "{}");
}

async function startAnalyzer(state, candidate, driveType, copyResult) {
  const analysisName = routeLabelFor(candidate, driveType);
  const outDir = path.join(ANALYSIS_ROOT, analysisName);
  const catalogPath = path.join(MACBOOK_RUNS_ROOT, state.runId, "analyzer_catalog.yaml");
  const logPath = path.join(MACBOOK_RUNS_ROOT, state.runId, "analyzer.log");
  const labelerOutDir = path.join(LABELER_ROOT, `manual_drive_labeler_${analysisName}`);
  const labelerLogPath = path.join(MACBOOK_RUNS_ROOT, state.runId, "manual_labeler.log");
  const yaml = [
    "defaults:",
    "  warmup_skip_sec: 0",
    "  missing_stop_after: 5",
    "  thresholds: {}",
    "routes:",
    `  - label: ${analysisName}`,
    `    model: ${state.branch || "unknown"}`,
    `    route_id: ${candidate.routeId}`,
    `    local_segments_dir: ${path.join(copyResult.destinationRoot, "segments")}`,
    `    notes: ${driveType.rideType} imported by Telegram /logdrive UI`,
    "",
  ].join("\n");
  const backgroundScript = [
    "set -e",
    `export BRICKPILOT_DRIVE_DATA_ROOT=${shellQuote(MACBOOK_DATA_ROOT)}`,
    `export BRICKPILOT_LOGDRIVE_RAW_ROOT=${shellQuote(RAW_ROOT)}`,
    `export BRICKPILOT_LOGDRIVE_ANALYSIS_ROOT=${shellQuote(ANALYSIS_ROOT)}`,
    `export BRICKPILOT_LABELER_OUT_BASE=${shellQuote(LABELER_ROOT)}`,
    `.venv/bin/python scripts/drive_tests/analyze_routes.py --catalog ${shellQuote(catalogPath)} --out ${shellQuote(outDir)} > ${shellQuote(logPath)} 2>&1`,
    driveType.includeVideo ? `.venv/bin/python scripts/drive_tests/manual_drive_labeler.py --route ${JSON.stringify(candidate.routeId)} --ride-type 'label validation' --out-dir ${shellQuote(labelerOutDir)} > ${shellQuote(labelerLogPath)} 2>&1` : "true",
  ].join("\n");
  const command = [
    `cd ${shellQuote(MACBOOK_REPO_ROOT)}`,
    `mkdir -p ${shellQuote(outDir)} ${shellQuote(path.dirname(catalogPath))} ${shellQuote(LABELER_ROOT)}`,
    `cat > ${shellQuote(catalogPath)} <<'YAML'`,
    yaml,
    `YAML`,
    `cp ${shellQuote(catalogPath)} ${shellQuote(path.join(outDir, "catalog.yaml"))}`,
    `nohup bash -lc ${shellQuote(backgroundScript)} >/dev/null 2>&1 &`,
  ].join("\n");
  await runMacBook(command, { timeout: 30000 });
  const status = { analysisName, outDir, catalogPath, logPath, labelerOutDir, labelerLogPath, startedAt: new Date().toISOString(), commandHost: MACBOOK_HOST };
  await writeFile(path.join(RUNS_ROOT, state.runId, "analyzer_started.json"), JSON.stringify(status, null, 2) + "\n", "utf8");
  return status;
}

function buildButtons(state) {
  const buttons = state.candidates.map((c) => ({
    label: `${c.number}: ${formatMiles(c.miles)} • ${formatDuration(c.durationSec).replace(" min", "m")}`,
    value: `${ROUTE_NAMESPACE}:${state.runId}:select:${c.number}`,
    style: "primary",
  }));
  buttons.push({ label: "Cancel", value: `${ROUTE_NAMESPACE}:${state.runId}:cancel`, style: "danger" });
  return buttons;
}

function buildDriveTypeRows(runId, number) {
  return [
    [
      { text: "Test drive", callback_data: `${ROUTE_NAMESPACE}:${runId}:type:${number}:test` },
      { text: "Label validation", callback_data: `${ROUTE_NAMESPACE}:${runId}:type:${number}:validation` },
    ],
    [
      { text: "Normal drive", callback_data: `${ROUTE_NAMESPACE}:${runId}:type:${number}:normal` },
      { text: "Cancel", callback_data: `${ROUTE_NAMESPACE}:${runId}:cancel`, style: "danger" },
    ],
  ];
}

function buildTelegramButtonRows(buttons) {
  const rows = [];
  for (let i = 0; i < buttons.length; i += 2) {
    rows.push(buttons.slice(i, i + 2).map((button) => ({
      text: button.label,
      callback_data: button.value,
      style: button.style,
    })));
  }
  return rows;
}

function summarizeCopyFailure(copyResult) {
  const failed = copyResult.failedFiles || (copyResult.files || []).filter((r) => !r.ok);
  const lines = [];
  if ((copyResult.missingKinds || []).length) lines.push(`Missing required kind(s): ${copyResult.missingKinds.join(", ")}`);
  if (failed.length) {
    lines.push(`Failed file(s): ${failed.length}`);
    for (const f of failed.slice(0, 4)) {
      const fallback = `size mismatch expected ${f.expectedSize || f.sizeBytes || "nonzero"}, got ${f.actualSize || 0}`;
      const errLines = String(f.error || fallback).split("\n").map((x) => x.trim()).filter(Boolean);
      const useful = errLines.find((x) => /No space left|Permission denied|No such file|timed out|size mismatch|Connection|Host key|rsync/i.test(x));
      const err = useful || errLines[0] || "copy failed";
      lines.push(`- seg ${f.segment} ${f.name}: ${err}`);
    }
    if (failed.length > 4) lines.push(`- ...and ${failed.length - 4} more; see manifest`);
  }
  return lines.length ? lines.join("\n") : "Verification failed; see manifest for details.";
}


function buildPresentation(state) {
  const buttons = buildButtons(state);
  return {
    title: "Choose logdrive route",
    tone: "info",
    blocks: [
      { type: "text", text: "🚗 Recent comma routes\nTap a route to select it, or Cancel to stop without copying anything." },
      ...(state.duplicateCount ? [{ type: "context", text: `Skipped ${state.duplicateCount} already-ingested route(s).` }] : []),
      { type: "text", text: state.candidates.map(candidateLine).join("\n\n") || "No candidates found." },
      { type: "context", text: `Device ${state.hostname || state.host}; ${state.branch || "unknown branch"} @ ${state.commit || "unknown commit"}` },
      { type: "buttons", buttons },
    ],
  };
}

function buildRouteSelectionText(state) {
  return [
    "🚗 Recent comma routes",
    "Tap a route button, or Cancel to stop without copying anything.",
    state.duplicateCount ? `Skipped ${state.duplicateCount} already-ingested route(s).` : "",
    "",
    state.candidates.map(candidateLine).join("\n\n") || "No new route candidates found. Already-ingested rides are hidden to avoid duplicate imports.",
    "",
    "Cancel is safe: it does not copy or analyze anything.",
  ].filter((line) => line !== "").join("\n");
}

async function sendCommandProgress(ctx, text, presentation = null) {
  const target = ctx.from || ctx.senderId || ctx.to;
  if (ctx.channel !== "telegram" || !target) return;
  const token = ctx.config?.channels?.telegram?.botToken;
  if (!token) throw new Error("Telegram bot token unavailable for progress message");
  const buttons = presentation?.blocks?.find((block) => block?.type === "buttons")?.buttons;
  const replyMarkup = buttons?.length ? {
    inline_keyboard: buttons.reduce((rows, button, index) => {
      if (index % 2 === 0) rows.push([]);
      rows[rows.length - 1].push({ text: button.label, callback_data: button.value });
      return rows;
    }, []),
  } : undefined;
  const body = {
    chat_id: target,
    text,
    ...(ctx.messageThreadId != null ? { message_thread_id: ctx.messageThreadId } : {}),
    ...(replyMarkup ? { reply_markup: replyMarkup } : {}),
  };
  const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Telegram sendMessage failed ${response.status}: ${detail.slice(0, 500)}`);
  }
}

async function runLogdriveDiscovery(ctx, runId) {
  let discovered;
  try {
    discovered = await discoverOnComma();
  } catch (err) {
    await sendCommandProgress(ctx, `I couldn't reach the comma over Wi‑Fi for /logdrive: ${err?.message || String(err)}`);
    return;
  }
  await sendCommandProgress(ctx, [
    `Connected to ${discovered.hostname || discovered.host}.`,
    "Searching recent comma routes and checking what has already been ingested…",
    "This can take a minute on spotty Wi‑Fi.",
  ].join("\n"));
  // Keep route discovery lightweight. Do not copy qlogs or compute mileage before
  // the user chooses a route; that can take minutes on spotty car Wi‑Fi and makes
  // the UI look broken. Mileage can be computed after ingest from copied logs.
  const alreadyIngested = await findAlreadyIngestedRouteIds();
  const originalCount = discovered.candidates?.length || 0;
  discovered.candidates = (discovered.candidates || []).filter((c) => !alreadyIngested.has(c.routeId));
  discovered.duplicateCount = originalCount - discovered.candidates.length;
  const state = { runId, createdAt: Date.now(), sessionKey: ctx.sessionKey, senderId: ctx.senderId, ...discovered };
  await writeUiState(runId, state);
  await sendCommandProgress(ctx, buildRouteSelectionText(state), buildPresentation(state));
}

async function handleLogdriveCommand(ctx) {
  const args = (ctx.args || "").trim().toLowerCase();
  if (args === "cancel") {
    return { text: "Cancelled — no route copy or analysis started." };
  }
  const runId = nowRunId();
  const started = Date.now();
  let discovered;
  try {
    discovered = await discoverOnComma();
  } catch (err) {
    return { text: `I couldn't reach the comma over Wi‑Fi for /logdrive: ${err?.message || String(err)}`, isError: true };
  }
  const alreadyIngested = await findAlreadyIngestedRouteIds();
  const originalCount = discovered.candidates?.length || 0;
  discovered.candidates = (discovered.candidates || []).filter((c) => !alreadyIngested.has(c.routeId));
  discovered.duplicateCount = originalCount - discovered.candidates.length;
  discovered.discoverySeconds = (Date.now() - started) / 1000;
  const state = { runId, createdAt: Date.now(), sessionKey: ctx.sessionKey, senderId: ctx.senderId, ...discovered };
  await writeUiState(runId, state);
  const presentation = buildPresentation(state);
  const buttons = buildButtons(state);
  return {
    text: `${buildRouteSelectionText(state)}\n\nConnected to ${state.hostname || state.host}; scan finished in ${state.discoverySeconds.toFixed(1)}s.`,
    presentation,
    channelData: { telegram: { buttons: buildTelegramButtonRows(buttons) } },
  };
}

async function handleTelegramCallback(ctx) {
  const parts = String(ctx.callback?.payload || "").split(":");
  const [runId, action, rawNumber, rawDriveType] = parts;
  if (!runId || !action) return { handled: false };
  let state = null;
  try { state = await readUiState(runId); } catch {}
  if (state?.senderId && ctx.senderId && String(ctx.senderId) !== String(state.senderId)) {
    await ctx.respond?.reply?.({ text: "That /logdrive selection belongs to another Telegram user, so I ignored it." });
    return { handled: true };
  }
  if (action === "cancel") {
    await safeTelegramCall(() => ctx.respond?.clearButtons?.());
    await safeTelegramCall(() => ctx.respond?.reply?.({ text: "Cancelled — no route copy or analysis started." }));
    return { handled: true };
  }
  if (action === "select") {
    const n = Number.parseInt(rawNumber || "", 10);
    const candidate = state?.candidates?.find((c) => c.number === n);
    if (!state || !candidate) {
      await ctx.respond?.reply?.({ text: "I couldn't recover that /logdrive selection. Please run /logdrive again." });
      return { handled: true };
    }
    const summary = candidate ? candidateLine(candidate) : `route #${rawNumber}`;
    await safeTelegramCall(() => ctx.respond?.clearButtons?.());
    await safeTelegramCall(() => ctx.respond?.reply?.({
      text: `Selected route ${n}\n\n${summary}\n\nWhat kind of drive is this?\n\n1) Test drive — copies logs only\n2) Label validation drive — copies logs + video\n3) Normal drive — copies logs only\n\nIngest starts immediately after this choice; no extra confirmation needed.`,
      buttons: buildDriveTypeRows(runId, n),
    }));
    return { handled: true };
  }
  if (action === "type") {
    const n = Number.parseInt(rawNumber || "", 10);
    const candidate = state?.candidates?.find((c) => c.number === n);
    const driveType = DRIVE_TYPES[rawDriveType];
    if (!state || !candidate || !driveType) {
      await ctx.respond?.reply?.({ text: "I couldn't recover that /logdrive selection. Please run /logdrive again." });
      return { handled: true };
    }
    await safeTelegramCall(() => ctx.respond?.editMessage?.({
      text: `Starting ingest for *${driveType.label}*\n\n${candidateLine(candidate)}\n\nCopying and verifying ${driveType.includeVideo ? "logs + video" : "logs only"} now…`,
      buttons: [],
    }));
    let copyResult;
    try {
      copyResult = await copyAndVerifyRoute(state, candidate, driveType);
    } catch (err) {
      await ctx.respond?.reply?.({ text: `Copy failed before verification finished: ${err?.message || String(err)}\n\nDo not turn off the car yet if you still need this route copied.` });
      return { handled: true };
    }
    if (!copyResult.ok) {
      await ctx.respond?.reply?.({
        text: [
          `Copy verification failed for route ${candidate.routeId}.`,
          `Drive type: ${driveType.label}`,
          summarizeCopyFailure(copyResult),
          `Manifest: ${copyResult.manifestPath}`,
          "Do not turn off the car yet if this route still needs to be copied.",
        ].join("\n"),
      });
      return { handled: true };
    }
    let dbImport = null;
    if (driveType.includeVideo) {
      try { dbImport = await importDriveDbValidation(state, candidate, driveType, copyResult); } catch (err) {
        dbImport = { error: err?.message || String(err) };
      }
    }
    let analyzer = null;
    try { analyzer = await startAnalyzer(state, candidate, driveType, copyResult); } catch (err) {
      analyzer = { error: err?.message || String(err) };
    }
    await ctx.respond?.reply?.({
      text: [
        "✅ Copy complete and verified — safe to turn off the car.",
        `Route: ${candidate.routeId}`,
        `Type: ${driveType.label}`,
        `Verified: ${copyResult.counts.logs} log file(s)${driveType.includeVideo ? ` + ${copyResult.counts.video} video file(s)` : ""}`,
        `Destination: ${copyResult.destinationRoot} on ${copyResult.copyHost || MACBOOK_HOST}`,
        `Manifest: ${copyResult.manifestPath}`,
        dbImport?.error ? `DB inbox warning: ${dbImport.error}` : (dbImport?.review_job ? `DB inbox: logdrive_label_validation review job ${dbImport.review_job.review_job_id}` : ""),
        analyzer?.error ? `Analyzer start warning: ${analyzer.error}` : `Analyzer started: ${analyzer.outDir}`,
        analyzer?.labelerOutDir ? `Manual labeler output: ${analyzer.labelerOutDir}` : "",
        "I’ll continue analysis without waiting for another confirmation.",
      ].join("\n"),
    });
    return { handled: true };
  }
  return { handled: false };
}

export default definePluginEntry({
  id: PLUGIN_ID,
  name: "Logdrive Telegram UI",
  description: "Button UI for /logdrive route selection.",
  register(api) {
    api.registerCommand({
      name: "logdrive",
      description: "Discover recent comma routes with Telegram route buttons and Cancel.",
      acceptsArgs: true,
      requireAuth: true,
      nativeProgressMessages: { default: "Checking comma routes…" },
      handler: handleLogdriveCommand,
    });
    api.registerInteractiveHandler({
      channel: "telegram",
      namespace: ROUTE_NAMESPACE,
      handler: handleTelegramCallback,
    });
  },
});
