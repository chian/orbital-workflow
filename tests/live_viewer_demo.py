"""Explicit live demonstration on a new adaptive run, including durable resume.

Run from the project directory. Evidence is saved separately from scientific input.
This script invokes the live scientific workflow; it is not part of unittest discovery.
"""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--run', type=Path, default=ROOT / '.artifacts/adaptive-storage-first')
parser.add_argument('--output', type=Path, default=ROOT / '.artifacts/visualization-verification-first')
args = parser.parse_args()
RUN = args.run.resolve()
EVIDENCE = args.output.resolve()
EVIDENCE.mkdir(exist_ok=True)
assert not RUN.exists(), 'Use a new run directory for the empty-to-live demonstration'
errors, checkpoints = [], []

def publish():
    (EVIDENCE / 'live-checkpoints.json').write_text(json.dumps({
        'run': str(RUN), 'checkpoints': checkpoints, 'browser_errors': errors}, indent=2))

def checkpoint(event, page, **extra):
    row = {'event': event, 'wall_time': time.time(),
           'viewer': page.evaluate('window.orbitalViewer.getState()'), **extra}
    checkpoints.append(row)
    publish()
    print(json.dumps({'event':event, 'observations': row['viewer']['observationCount'], **extra}), flush=True)

def hashes():
    paths = [p for folder in ('objects', 'tool-cache', 'model-cache', 'episodes')
             for p in (RUN / folder).rglob('*') if p.is_file() and p.suffix in ('.json', '.npz')]
    return {str(p.relative_to(RUN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/snap/bin/chromium', headless=True,
        args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440, 'height':1080})
    page.on('pageerror', lambda error: errors.append(str(error)))
    from urllib.parse import quote
    page.goto('http://127.0.0.1:8767/?run='+quote(str(RUN)))
    assert page.evaluate('window.orbitalViewer.getState().observationCount') == 0
    assert not RUN.exists(), 'Viewer created a scientific run directory'
    page.screenshot(path=str(EVIDENCE / 'waiting.png'), full_page=True)
    checkpoint('empty_view_before_run', page)
    streams = []
    def start(command, name):
        stream = (EVIDENCE / name).open('w')
        streams.append(stream)
        process = subprocess.Popen([str(ROOT / '.venv/bin/python'), '-m', 'orbital_workflow', *command],
            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        print(json.dumps({'process':process.pid,'command':command}), flush=True)
        return process
    process = start(['run', '--output', str(RUN)], 'initial-execution.log')
    initial_selection = None
    previous_count, saved_prefix, interrupted = 0, {}, False
    saw_preservation, followed = False, False
    while True:
        page.wait_for_timeout(500)
        state = page.evaluate('window.orbitalViewer.getState()')
        count = state['observationCount']
        if count and state['loadedObservations'] and initial_selection is None:
            page.select_option('#playback-mode', 'individual')
            page.evaluate('window.orbitalViewer.seek(window.orbitalViewer.getState().maximum*.37)')
            initial_selection = page.evaluate('window.orbitalViewer.getState()')
            checkpoint('first_live_observation', page)
            page.screenshot(path=str(EVIDENCE / 'first-observation.png'), full_page=True)
        if count > previous_count:
            checkpoint('catalog_grew', page, active_process=process.poll() is None)
            if initial_selection and count > initial_selection['observationCount'] and not saw_preservation:
                assert state['primary'] == initial_selection['primary']
                assert state['time'] == initial_selection['time']
                assert not state['playing']
                saw_preservation = True
                checkpoint('selection_and_time_preserved_during_growth', page)
                page.check('#follow-latest')
            elif saw_preservation and count > previous_count and not followed:
                assert state['primary'] == page.evaluate('window.orbitalViewer.data.default_primary')
                followed = True
                checkpoint('explicit_follow_latest', page)
                page.uncheck('#follow-latest')
            previous_count = count
        closed = list((RUN / 'episode-store/episodes').glob('*/parent-report.json'))
        if closed and not interrupted and process.poll() is None:
            saved_prefix = hashes()
            checkpoint('interrupt_after_closed_child', page, immutable_prefix_files=len(saved_prefix))
            process.send_signal(signal.SIGINT)
            process.wait(timeout=20)
            for path, digest in saved_prefix.items():
                assert hashlib.sha256((RUN/path).read_bytes()).hexdigest() == digest
            (EVIDENCE / 'immutable-prefix.json').write_text(json.dumps(saved_prefix, indent=2))
            process = start(['resume', str(RUN)], 'resumed-execution.log')
            interrupted = True
            checkpoint('resumed_same_fresh_run', page)
        status = process.poll()
        if status is not None:
            assert status == 0, f'Workflow exited {status}; inspect execution logs'
            break
    # Allow the last atomic index and completion summary to refresh.
    page.wait_for_timeout(2500)
    assert (RUN / 'summary.json').is_file()
    for path, digest in saved_prefix.items():
        assert hashlib.sha256((RUN/path).read_bytes()).hexdigest() == digest
    assert not errors, errors
    checkpoint('completed_live_run', page, interrupted_and_resumed=interrupted,
        prefix_files_unchanged=len(saved_prefix), selection_preserved=saw_preservation,
        follow_latest_exercised=followed)
    page.screenshot(path=str(EVIDENCE / 'completed-live.png'), full_page=True)
    browser.close()
    for stream in streams:
        stream.close()
