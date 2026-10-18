"""Browser interactions and independent field checks on a stored fresh run."""
import argparse
import json
import math
from pathlib import Path
import sys
from urllib.parse import quote

import numpy as np
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orbital_workflow.visualization import make_viewer
from orbital_workflow.storage import read_index
from orbital_workflow.artifacts import Artifacts
from orbital_workflow.gravity import GravitySystem

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
run, output = args.run.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
errors, checks = [], []
rows, warnings = read_index(run)
assert rows and not warnings
store = Artifacts(run / 'objects')

def expect(condition, name, **details):
    assert condition, (name, details)
    checks.append({'check':name, **details})

def state(page):
    return page.evaluate('window.orbitalViewer.getState()')

def wait_loaded(page, count=1):
    page.wait_for_function('(n)=>window.orbitalViewer.getState().loadedObservations>=n', arg=count)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/snap/bin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1080})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8767/?run='+quote(str(run)))
    wait_loaded(page)
    page.uncheck('#auto-refresh')
    page.select_option('#playback-mode','individual')
    longest=max(rows,key=lambda row:row['summary']['observed_interval'][1]-row['summary']['observed_interval'][0])
    page.select_option('#primary',longest['id'])
    page.select_option('#preset','single')
    wait_loaded(page)
    page.click('#reset')
    expect(state(page)['observationCount'] == len(rows), 'any fresh run uses its own catalog', count=len(rows))
    expect(state(page)['loadedObservations'] == 1, 'only selected numerical observation loaded initially')
    page.select_option('#speed','0.5')
    page.click('#play')
    page.wait_for_timeout(650)
    page.click('#play')
    slow = state(page)['time']
    page.wait_for_timeout(200)
    expect(state(page)['time'] == slow and slow > .1, 'pause holds playback time', slow_time=slow)
    page.click('#reset')
    page.select_option('#speed','5')
    page.click('#play')
    page.wait_for_timeout(650)
    page.click('#play')
    fast = state(page)['time']
    expect(fast > slow*3, 'speed control changes playback', slow_time=slow, fast_time=fast)
    page.click('#reset')
    expect(state(page)['time'] == state(page)['minimum'] and not state(page)['playing'], 'reset returns to observed start')
    # Scrub using the actual range input event.
    page.locator('#time').evaluate('(e)=>{e.value=Number(e.max)*.41;e.dispatchEvent(new Event("input"));}')
    selected_time = state(page)['time']
    expect(math.isclose(selected_time, state(page)['maximum']*.41), 'slider scrubs absolute time')
    prior = state(page)
    page.click('#refresh')
    page.wait_for_function('!window.orbitalViewer.getState().refreshBusy')
    expect(state(page)['primary']==prior['primary'] and state(page)['time']==selected_time, 'manual refresh preserves primary and time')
    page.click('#play')
    page.click('#refresh')
    page.wait_for_function('!window.orbitalViewer.getState().refreshBusy')
    expect(state(page)['playing'] and page.input_value('#speed')=='5', 'refresh preserves active playback and speed')
    page.click('#play')
    # Load an explicit comparison and then drop it, confirming on-demand ejection.
    primary = state(page)['primary']
    comparison = next(row['id'] for row in rows if row['id'] != primary)
    page.locator('.observation[data-id="'+comparison+'"] input').check()
    wait_loaded(page,2)
    expect(state(page)['loadedObservations'] == 2, 'explicit comparison loaded from disk')
    page.locator('.observation[data-id="'+comparison+'"] input').uncheck()
    expect(state(page)['loadedObservations'] == 1, 'deselected numerical data ejected')
    # Each available observation's field is independently evaluated from its
    # original saved forcing and declared physics, including arbitrary times.
    for row in rows:
        page.select_option('#primary',row['id'])
        page.select_option('#preset','single')
        wait_loaded(page)
        forcing=store.arrays(row['forcing_id'])
        r=row['request']
        t=(row['summary']['observed_interval'][0]+row['summary']['observed_interval'][1])*.5
        page.evaluate('(t)=>window.orbitalViewer.seek(t)', t)
        if r['terms']['forcing']:
            page.wait_for_function('()=>{const v=window.orbitalViewer;const s=v.data.simulations.find(x=>x.id===v.getState().primary);return v.forcingAt(s,v.getState().time)!==null;}')
        actual=page.evaluate('()=>{const v=window.orbitalViewer;const s=v.data.simulations.find(x=>x.id===v.getState().primary);return v.accelerationAt(s,v.getState().time,1.1,-.3);}')
        x,y=1.1,-.3
        expected=np.zeros(2)
        if r['terms']['central']:
            strength=1+(r['a']*math.sin(.7*t) if r['terms']['modulation'] else 0)
            gravity=GravitySystem.from_record(r.get('gravity',{}))
            sources=gravity.sources(t)
            active=r.get('active_bodies')
            sources=[body for body in sources if active is None or body['id'] in active]
            if r.get('gravity_mode')=='monopole':sources=[{'mass':sum(body['mass'] for body in sources),'position':[0,0]}]
            for body in sources:
                delta=np.array([x,y])-body['position']
                expected-=strength*body['mass']*delta/np.linalg.norm(delta)**3
        if r['terms']['rotating']:
            c,d=math.cos(.4*t),math.sin(.4*t)
            expected+=.02*np.array([c*x+d*y,d*x-c*y])
        if r['terms']['forcing']:
            expected+=r['sigma']*np.array([np.interp(t,forcing['times'],forcing['eta'][:,j]) for j in (0,1)])
        np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-14)
        boundary=page.evaluate('()=>{const v=window.orbitalViewer;const s=v.data.simulations.find(x=>x.id===v.getState().primary),end=s.times.at(-1);return {before:v.sampleAt(s,s.times[0]-1),after:v.sampleAt(s,end+1),last:v.sampleAt(s,end),terminal:s.summary.terminal_state,zero:v.recurrenceAt(s,s.times[0]),final:v.recurrenceAt(s,end),score:s.summary.persistence_measurement.effective_duration};}')
        expect(boundary['before'] is None and boundary['after'] is None, 'no motion extrapolated outside observation', id=row['id'])
        np.testing.assert_array_equal(boundary['last'],boundary['terminal'])
        expect(boundary['zero']==0 and math.isclose(boundary['final'],boundary['score'],abs_tol=1e-14,rel_tol=1e-12), 'recurrence uses measured cycle endpoints', id=row['id'])
    expect(True,'all declared field terms match original forcing and physics', observations=len(rows))
    # Render representative times with comparisons, including early endpoints.
    page.select_option('#preset','velocity')
    page.wait_for_timeout(500)
    for fraction in (0,.5,1):
        page.evaluate('(f)=>window.orbitalViewer.seek(window.orbitalViewer.getState().maximum*f)',fraction)
        page.wait_for_timeout(100)
        page.screenshot(path=str(output / ('time-'+str(fraction)+'.png')), full_page=True)
    page.check('#loop')
    page.click('#play')
    page.wait_for_timeout(250)
    expect(state(page)['time']<state(page)['maximum'], 'play at end restarts and loop remains available')
    page.click('#play')
    page.uncheck('#loop')
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(250)
    width=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    expect(width['document']<=width['viewport'], 'mobile layout has no horizontal overflow', **width)
    page.screenshot(path=str(output / 'mobile.png'),full_page=True)
    # Offline export contains a chosen comparison, with complete forcing.
    offline=make_viewer(run,output / 'offline.html',observation_ids=[row['id'] for row in rows[:2]])
    offline_page=browser.new_page(viewport={'width':1440,'height':1080})
    offline_page.on('pageerror',lambda error:errors.append(str(error)))
    offline_page.goto(Path(offline['viewer']).as_uri())
    wait_loaded(offline_page)
    offline_page.select_option('#playback-mode','individual')
    offline_page.locator('.observation input:not(:disabled)').first.check()
    wait_loaded(offline_page,2)
    offline_page.evaluate('window.orbitalViewer.seek(window.orbitalViewer.getState().maximum)')
    expect(offline_page.locator('#live-controls').is_hidden(), 'offline snapshot runs without server fetches')
    offline_page.screenshot(path=str(output/'offline.png'),full_page=True)
    expect(not errors,'browser execution has no errors', errors=errors)
    browser.close()
(output/'checks.json').write_text(json.dumps({'source_run':str(run),'checks':checks,'browser_errors':errors},indent=2))
print(json.dumps({'checks':len(checks),'browser_errors':errors,'evidence':str(output)},indent=2))
