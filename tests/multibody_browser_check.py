"""Compare moving-source and reduced-field rendering with saved numerical inputs.

The second directory contains real finite simparts observations, not an adaptive
search. This check does not create or alter scientific credit.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import quote

import numpy as np
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orbital_workflow.gravity import GravitySystem

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('parts', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--url', default='http://127.0.0.1:8767/')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
checks, errors = [], []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/snap/bin/chromium', headless=True,
                                        args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440, 'height':1100})
    page.on('pageerror', lambda error: errors.append(str(error)))
    for run in (args.run.resolve(), args.parts.resolve()):
        page.goto(args.url + '?run=' + quote(str(run)))
        page.wait_for_function('window.orbitalViewer.getState().loadedObservations>0')
        page.select_option('#playback-mode', 'individual')
        page.select_option('#preset', 'single')
        simulations = page.evaluate('window.orbitalViewer.data.simulations')
        for simulation in simulations:
            page.select_option('#primary', simulation['id'])
            page.wait_for_function('id=>{const v=window.orbitalViewer;return v.getState().primary===id && v.getState().loadedObservations>0;}', arg=simulation['id'])
            request = simulation['request']
            gravity = GravitySystem.from_record(request['gravity'])
            last = simulation['summary']['observed_interval'][1]
            for time in (request['start'], request['start'] + .37*(last-request['start']), last):
                page.evaluate('t=>window.orbitalViewer.seek(t)', time)
                actual = page.evaluate('''()=>{const v=window.orbitalViewer,s=v.data.simulations.find(s=>s.id===v.getState().primary),t=v.getState().time;
                    return {time:t,bodies:v.bodiesAt(s,t),terms:v.accelerationTermsAt(s,t,1.1,-.3)};}''')
                np.testing.assert_allclose(actual['time'], time, atol=1e-14)
                sources = gravity.sources(time)
                for expected, body in zip(sources, actual['bodies']):
                    assert body['id'] == expected['id'] and body['mass'] == expected['mass']
                    for key in ('position', 'velocity'):
                        np.testing.assert_allclose(body[key], expected[key], atol=1e-14, rtol=1e-13)
                active = request['active_bodies']
                retained = [body for body in sources if active is None or body['id'] in active]
                if request['gravity_mode'] == 'monopole':
                    retained = [{'id':'monopole', 'mass':sum(b['mass'] for b in retained), 'position':[0, 0]}]
                if not request['terms']['central']:
                    retained = []
                contributions = actual['terms']['attractors']
                assert [b['id'] for b in contributions] == [b['id'] for b in retained]
                total = np.zeros(2)
                for body, contribution in zip(retained, contributions):
                    delta = np.array([1.1, -.3])-body['position']
                    expected = -body['mass']*delta/np.linalg.norm(delta)**3
                    np.testing.assert_allclose(contribution['acceleration'], expected, atol=1e-14, rtol=1e-13)
                    total += expected
                np.testing.assert_allclose(actual['terms']['central'], total, atol=1e-14, rtol=1e-13)
            label = page.locator('#primary option:checked').inner_text()
            reduced = (not all(request['terms'].values()) or request['gravity_mode'] == 'monopole'
                       or active is not None and len(active) < len(gravity.masses))
            assert ('reduced' if reduced else 'complete') in label
            checks.append({'run':str(run), 'observation':simulation['id'], 'gravity_mode':request['gravity_mode'],
                           'active_bodies':active, 'times_checked':3, 'source_states_and_individual_vectors_match':True,
                           'classification_matches':True})
            print('source fields match', request['gravity_mode'], active, flush=True)
        before = page.locator('#orbit').evaluate('(e)=>e.toDataURL()')
        page.select_option('#framing', 'domain')
        assert page.locator('#orbit').evaluate('(e)=>e.toDataURL()') != before
        page.select_option('#framing', 'fit')
        before = page.locator('#orbit').evaluate('(e)=>e.toDataURL()')
        page.uncheck('#show-attractors')
        assert page.locator('#orbit').evaluate('(e)=>e.toDataURL()') != before
        page.check('#show-attractors')
        page.screenshot(path=str(args.output / (run.name+'.png')), full_page=True)
    # Opening a finite diagnostic does not change the latest adaptive scenario.
    page.select_option('#scenario', 'scenario_01')
    page.wait_for_function('window.orbitalViewer.getState().bodies.length===1')
    page.select_option('#scenario', 'scenario_02')
    page.wait_for_function('window.orbitalViewer.getState().bodies.length===2')
    assert page.evaluate('window.orbitalViewer.getState().runPath') == str(args.run.resolve())
    assert not errors, errors
    browser.close()

(args.output/'checks.json').write_text(json.dumps({'checks':checks, 'browser_errors':errors,
    'camera_and_source_overlays_change_rendering':True, 'scenario_picker_restores_latest_adaptive_run':True}, indent=2))
print(json.dumps({'observations_checked':len(checks), 'browser_errors':errors}, indent=2))
