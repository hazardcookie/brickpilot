from pathlib import Path
import json, tempfile
from scripts.drive_tests.brickpilot_db.config import DriveDbConfig
from scripts.drive_tests.brickpilot_db.store import DriveStore
from scripts.drive_tests.brickpilot_db.ingest import inventory, import_root
from scripts.drive_tests.brickpilot_db import queries

def test_store_roundtrip_artifact_route_label(tmp_path: Path):
    cfg = DriveDbConfig(database_url=f"sqlite:///{tmp_path/'drive.sqlite'}", artifact_root=tmp_path/'artifacts')
    st = DriveStore(cfg); st.migrate(); host = st.upsert_host('testhost','tester','macbook')
    src = tmp_path/'0000015a--abc'/'0'; src.mkdir(parents=True); f = src/'qlog.bz2'; f.write_bytes(b'hello')
    route = st.upsert_route('0000015a--abc', source_device='comma-test', segment_count=1)
    seg = st.upsert_segment(route, 0, {'qlog': True})
    art = st.import_artifact(f, host_id=host); st.link_route_artifact(route, art.id, 'qlog', seg); st.commit()
    assert (cfg.artifact_root / art.relative_path).read_bytes() == b'hello'
    assert st.conn.execute('select count(*) from route_artifacts').fetchone()[0] == 1
    inbox = st.create_inbox('unit'); job = st.upsert_review_job(inbox, route, 'legacy-1')
    st.insert_label_event(job, 'create', {'label':'smooth'}); st.commit()
    assert st.conn.execute('select count(*) from label_events').fetchone()[0] == 1

def test_inventory_and_import_idempotent(tmp_path: Path):
    root = tmp_path/'raw'/'from_comma'/'0000015a--abcdef01'/'0'; root.mkdir(parents=True)
    (root/'qlog.bz2').write_bytes(b'qlog'); (root/'rlog.bz2').write_bytes(b'rlog')
    inv = inventory(tmp_path/'raw')
    assert inv['file_count'] == 2
    cfg_path = tmp_path/'cfg.toml'; cfg_path.write_text(f'database_url = "sqlite:///{tmp_path}/db.sqlite"\nartifact_root = "{tmp_path}/artifacts"\n')
    one = import_root(tmp_path/'raw', str(cfg_path), dry_run=False)
    two = import_root(tmp_path/'raw', str(cfg_path), dry_run=False)
    assert one['imported_files'] == two['imported_files'] == 2
    assert len(list((tmp_path/'artifacts').rglob('*'))) > 0

def test_camera_kind_classification_keeps_camera_roles_distinct():
    assert DriveStore.kind_for_path(Path("fcamera.hevc")) == "fcamera"
    assert DriveStore.kind_for_path(Path("ecamera.hevc")) == "ecamera"
    assert DriveStore.kind_for_path(Path("dcamera.hevc")) == "dcamera"
    assert DriveStore.kind_for_path(Path("qcamera.ts")) == "qcamera"
    assert DriveStore.kind_for_path(Path("qcamera.hevc")) == "qcamera"
    assert DriveStore.kind_for_path(Path("camera.hevc")) == "camera"

def test_dynamic_label_validation_includes_raw_video_only_jobs(tmp_path: Path):
    cfg = DriveDbConfig(database_url=f"sqlite:///{tmp_path/'drive.sqlite'}", artifact_root=tmp_path/'artifacts')
    st = DriveStore(cfg); st.migrate(); host = st.upsert_host('testhost','tester','macbook')
    route = st.upsert_route('0000016f--427a57d416', source_device='comma-test', segment_count=1)
    seg = st.upsert_segment(route, 0, {'qlog': True, 'rlog': True, 'qcamera': True})
    files = {
        'qcamera.ts': b'video',
        'qlog.bz2': b'qlog',
        'rlog.bz2': b'rlog',
    }
    artifacts = {}
    src = tmp_path / 'raw'
    src.mkdir()
    for name, body in files.items():
        fp = src / name
        fp.write_bytes(body)
        art = st.import_artifact(fp, host_id=host)
        artifacts[name] = art
        st.link_route_artifact(route, art.id, art.kind, seg)
    st.execute("INSERT INTO video_sync_segments(route_uuid,artifact_id,segment_index,route_start_sec,video_start_sec,duration_sec,confidence) VALUES(?,?,?,?,?,?,?)", (route, artifacts['qcamera.ts'].id, 0, 0, 0, 60, 1.0))
    st.execute("INSERT INTO route_samples(route_uuid,t_sec,speed_mph) VALUES(?,?,?)", (route, 0.0, 15.0))
    inbox = st.create_inbox('logdrive_label_validation')
    st.commit()

    jobs = queries.list_jobs(st, inbox)
    assert [j['route_id'] for j in jobs] == ['0000016f--427a57d416']
    assert jobs[0]['media_status'] == 'raw video only'
    assert jobs[0]['raw_video_artifact_count'] == 1
    assert jobs[0]['playable_video_artifact_count'] == 0
