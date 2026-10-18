"""Exercise the complete tour, term overlays, and live arrival behavior in Chromium."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
from urllib.parse import quote
import numpy as np
from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbital_workflow.visualization import load_catalog,render_document
from orbital_workflow.artifacts import Artifacts

parser=argparse.ArgumentParser()
parser.add_argument('run',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();run=args.run.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
errors,checks=[],[]
def record(name,**details):
 checks.append({'check':name,**details})
 (output/'checks.json').write_text(json.dumps({'run':str(run),'checks':checks,'browser_errors':errors},indent=2))
 print(name,flush=True)
def state(page):return page.evaluate('window.orbitalViewer.getState()')
def loaded(page):page.wait_for_function('window.orbitalViewer.getState().loadedObservations>0')
def evaluate_terms(page,x=1.1,y=-.3):
 return page.evaluate('([x,y])=>{const v=window.orbitalViewer,s=v.data.simulations.find(s=>s.id===v.getState().primary);return v.accelerationTermsAt(s,v.getState().time,x,y);}',[x,y])

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/snap/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1100});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8767/?run='+quote(str(run)));loaded(page)
 initial=state(page)
 assert initial['mode']=='progress' and initial['playing'] and initial['tourIndex']==0
 timeline=page.evaluate('window.orbitalViewer.data.timeline')
 assert initial['primary']==timeline[0]['observation_id']
 record('default opens the entire chronological tour',appearances=len(timeline),distinct_observations=initial['observationCount'])
 page.select_option('#tour-pace','2')
 seen=[];maximum_resident=0;began=time.monotonic()
 while True:
  current=state(page);index=current['tourIndex']
  if not seen or seen[-1]!=index:
   assert current['primary']==timeline[index]['observation_id']
   seen.append(index)
   print('observation',index+1,flush=True)
   if index==min(6,len(timeline)-1):page.screenshot(path=str(output/'mid-tour.png'),full_page=True)
  maximum_resident=max(maximum_resident,current['loadedObservations'])
  assert current['loadedBytes']<=16*1024*1024
  if not current['playing']:break
  assert time.monotonic()-began<90,'Browser tour did not finish'
  page.wait_for_timeout(80)
 assert seen==list(range(len(timeline))),seen
 assert current['time']==current['maximum'] and current['tourIndex']==len(timeline)-1
 assert maximum_resident<=4
 record('automatic playback visits every acquisition appearance and stops',sequence=seen,maximum_decoded_observations=maximum_resident)
 page.click('#previous-observation');loaded(page)
 assert state(page)['tourIndex']==len(timeline)-2 and not state(page)['playing']
 page.click('#next-observation');loaded(page)
 assert state(page)['tourIndex']==len(timeline)-1
 page.click('#reset');loaded(page)
 assert state(page)['tourIndex']==0 and state(page)['time']==state(page)['minimum']
 page.locator('#iteration').evaluate('(e)=>{e.value=Math.min(4,Number(e.max));e.dispatchEvent(new Event("input"));}')
 loaded(page);assert state(page)['tourIndex']==min(3,len(timeline)-1)
 prior=state(page);page.click('#refresh');page.wait_for_function('!window.orbitalViewer.getState().refreshBusy')
 assert state(page)['tourIndex']==prior['tourIndex'] and state(page)['time']==prior['time']
 record('previous next reset history scrub and refresh preserve intentional inspection')
 # Verify decomposition against original saved forcing independently of JavaScript.
 page.select_option('#playback-mode','individual');page.select_option('#primary',timeline[0]['observation_id']);page.select_option('#preset','single');loaded(page)
 page.evaluate('window.orbitalViewer.seek(1.234)')
 selected=page.evaluate('window.orbitalViewer.data.simulations.find(s=>s.id===window.orbitalViewer.getState().primary)')
 r=selected['request'];forcing=Artifacts(run/'objects').arrays(r['forcing_id']);t=state(page)['time'];x,y=1.1,-.3
 actual=evaluate_terms(page,x,y);rad=math.hypot(x,y)
 central=-np.array([x,y])/rad**3 if r['terms']['central'] else np.zeros(2)
 modulation=central*r['a']*math.sin(.7*t) if r['terms']['modulation'] else np.zeros(2)
 c,d=math.cos(.4*t),math.sin(.4*t)
 rotating=.02*np.array([c*x+d*y,d*x-c*y]) if r['terms']['rotating'] else np.zeros(2)
 push=r['sigma']*np.array([np.interp(t,forcing['times'],forcing['eta'][:,i]) for i in (0,1)]) if r['terms']['forcing'] else np.zeros(2)
 for name,value in [('central',central),('modulation',modulation),('rotating',rotating),('forcing',push),('total',central+modulation+rotating+push)]:np.testing.assert_allclose(actual[name],value,atol=1e-14,rtol=1e-13)
 elsewhere=evaluate_terms(page,-.8,.9)
 np.testing.assert_array_equal(actual['forcing'],elsewhere['forcing'])
 if r['terms']['rotating']:assert actual['rotating']!=elsewhere['rotating']
 assert abs(x*actual['modulation'][1]-y*actual['modulation'][0])<1e-14
 record('colored terms independently match saved physics',components=actual,forcing_spatially_uniform=True)
 for name in ('modulation','rotating','forcing'):
  before=page.locator('#orbit').evaluate('(e)=>e.toDataURL()');page.uncheck('#show-'+name)
  after=page.locator('#orbit').evaluate('(e)=>e.toDataURL()')
  if np.linalg.norm(actual[name])>0:assert before!=after,name
  np.testing.assert_array_equal(evaluate_terms(page)['total'],actual['total'])
  page.check('#show-'+name)
 page.select_option('#term-gain','30');np.testing.assert_array_equal(evaluate_terms(page)['total'],actual['total'])
 page.screenshot(path=str(output/'forcing-terms.png'),full_page=True)
 page.select_option('#term-gain','10')
 record('overlay toggles and magnification change rendering without changing physical values')
 page.select_option('#playback-mode','progress');page.click('#reset');page.check('#loop')
 page.locator('#iteration').evaluate('(e)=>{e.value=e.max;e.dispatchEvent(new Event("input"));}')
 loaded(page);page.evaluate('window.orbitalViewer.seek(window.orbitalViewer.getState().maximum-.01)')
 page.click('#play');page.wait_for_function('window.orbitalViewer.getState().tourIndex===0')
 record('complete run loop returns to first acquisition')
 page.click('#play');page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path=str(output/'mobile.png'),full_page=True)
 record('new history and forcing controls fit mobile width')
 # Software fixture: expose a prefix of real saved data, then publish later entries.
 # Numerical API calls still read the original run. This is not a new science run.
 catalog=load_catalog(run)
 catalog['live']={'endpoint':'/api/snapshot','data_endpoint':'/api/observation','forcing_endpoint':'/api/forcing','interval_ms':200,'browser_cache_bytes':16*1024*1024}
 count={'value':1}
 def prefix():
  data={**catalog,'timeline':catalog['timeline'][:count['value']],'run_state':'awaiting_completed_observations'}
  ids={e['observation_id'] for e in data['timeline']};data['simulations']=[r for r in catalog['simulations'] if r['id'] in ids]
  data['default_primary']=data['simulations'][-1]['id'];return data
 live=browser.new_page(viewport={'width':1200,'height':1000});live.on('pageerror',lambda e:errors.append(str(e)))
 live.route('**/api/snapshot?*',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(prefix())))
 live.route('http://127.0.0.1:8767/?live-prefix-fixture',lambda route:route.fulfill(status=200,content_type='text/html',body=render_document(prefix())))
 live.goto('http://127.0.0.1:8767/?live-prefix-fixture');loaded(live);live.select_option('#tour-pace','2')
 live.wait_for_function('window.orbitalViewer.getState().tourWaiting',timeout=10000)
 assert state(live)['playing'] and state(live)['tourIndex']==0
 count['value']=2
 live.wait_for_function('window.orbitalViewer.getState().tourIndex===1',timeout=10000)
 assert state(live)['playing']
 record('active-run prefix fixture waits at tail then continues on new publication')
 offline=browser.new_page(viewport={'width':1440,'height':1100});offline.on('pageerror',lambda e:errors.append(str(e)))
 offline.goto((run/'visualizations/playback.html').as_uri());loaded(offline)
 assert state(offline)['mode']=='progress' and state(offline)['timelineCount']==len(timeline)
 offline.click('#play');offline.locator('#iteration').evaluate('(e)=>{e.value=e.max;e.dispatchEvent(new Event("input"));}');loaded(offline)
 assert state(offline)['primary']==timeline[-1]['observation_id']
 assert state(offline)['loadedObservations']<=4
 record('offline default includes the entire run and decodes selections on demand')
 assert not errors,errors
 browser.close()
(output/'checks.json').write_text(json.dumps({'run':str(run),'checks':checks,'browser_errors':errors},indent=2))
print(json.dumps({'checks':len(checks),'browser_errors':errors,'evidence':str(output)},indent=2))
