"""Continuous capture for the 90-second NeuroAI harness presentation.

    DB_NAME=second_shift .venv/bin/python -m scripts.video.record_demo_v6

No mocked events, image sequences, time scaling, or caption overlays. The raw
video, wall-clock marks, event log, packets and recovery proof are retained.
"""
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from playwright.async_api import async_playwright, expect

from api.main import clean
from harness import eeg, store
from harness.db import get_db
from harness.worker import OBJECTIVE

BASE = os.environ.get('DEMO_API', 'http://localhost:8001')
OUT = Path(os.environ.get('VIDEO_CAPTURE_DIR', 'run/video-v6/take-1'))
MIN_CRASH_TIME = float(os.environ.get('VIDEO_MIN_CRASH_TIME', '65'))
CURSOR = """document.addEventListener('DOMContentLoaded',()=>{
 const cursor=document.createElement('div');cursor.id='recording-pointer';
 cursor.style.cssText='position:fixed;left:-50px;top:-50px;width:22px;height:26px;pointer-events:none;z-index:200';
 cursor.innerHTML='<svg width="22" height="26" viewBox="0 0 22 26"><path d="M2 1L3 22L8 16L12 24L16 22L12 15L20 14Z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>';
 document.body.append(cursor);document.addEventListener('mousemove',e=>{cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px'});
})"""


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'marks.json').exists():
        raise RuntimeError('Preserve the existing raw recording; choose a new VIDEO_CAPTURE_DIR.')
    db = get_db()
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as client:
        async def api(path):
            response = await client.get(path)
            response.raise_for_status()
            return response.json()
        assert not (await api('/api/worker/status'))['running'], 'Worker already running'
        # Protocol creation loads existing recorded EEG, exactly as the normal CLI does.
        protocol, _ = await asyncio.to_thread(eeg.load_protocol, 'demo')
        cid = await asyncio.to_thread(store.create_campaign, db, protocol=protocol, objective=OBJECTIVE,
                                      max_channels=64, max_experiments=14)
        (OUT / 'campaign-id.txt').write_text(cid)
        print('Fresh campaign:', cid, flush=True)
        marks, observations, errors = {}, [], []
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080},
                                                device_scale_factor=1,
                                                record_video_dir=str(OUT / 'raw'),
                                                record_video_size={'width': 1920, 'height': 1080})
            await context.add_init_script(CURSOR)
            t0, epoch0 = time.monotonic(), time.time()
            page = await context.new_page()
            video = page.video
            page.on('pageerror', lambda error: errors.append(str(error)))

            def mark(name, **detail):
                value = {'time': round(time.monotonic()-t0, 3), 'utc': datetime.now(timezone.utc).isoformat(), **detail}
                marks[name] = value
                print(name, json.dumps(value), flush=True)
                (OUT / 'marks.json').write_text(json.dumps({'campaign_id': cid, 'epoch0': epoch0, 'marks': marks}, indent=2))

            async def wait_for(predicate, timeout=300):
                end = time.monotonic()+timeout
                while time.monotonic()<end:
                    value = await asyncio.to_thread(predicate)
                    if value:
                        return value
                    await asyncio.sleep(.06)
                raise TimeoutError('Expected backend condition did not occur')

            async def move(selector):
                box = await page.locator(selector).bounding_box()
                await page.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2, steps=16)

            async def click(selector, hold=.12):
                await move(selector)
                await asyncio.sleep(hold)
                await page.mouse.click(*(await page.locator(selector).evaluate('(e)=>{const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}')))

            async def park():
                await page.mouse.move(1800, 940, steps=18)

            stop_watch = asyncio.Event()
            async def watch():
                seen = set()
                while not stop_watch.is_set():
                    rows = await asyncio.to_thread(lambda:list(db.events.find({'campaign_id':cid}).sort('ts',1)))
                    for ev in rows:
                        if str(ev['_id']) not in seen:
                            seen.add(str(ev['_id']))
                            observations.append({'observed':round(time.monotonic()-t0,3), **clean(ev)})
                    await asyncio.sleep(.25)

            watcher = asyncio.create_task(watch())
            try:
                await page.goto(BASE+f'/?campaign={cid}')
                await expect(page.locator('#campaign-id')).to_have_text(cid)
                await page.evaluate('document.fonts.ready')
                await park()
                await asyncio.sleep(2)
                mark('intro')
                await asyncio.sleep(3)
                mark('start')
                await click('#btn-start')
                await park()
                await wait_for(lambda:db.experiments.count_documents({'campaign_id':cid,'status':'done'})>=2)
                mark('two_results')
                # Record a longer uninterrupted EEG search for the 90-second narration.
                await asyncio.sleep(max(0, MIN_CRASH_TIME-(time.monotonic()-t0)))
                before = await asyncio.to_thread(lambda:list(db.experiments.find({'campaign_id':cid,'status':'done'})))
                await move('#btn-kill')
                # Cursor is already over the real control. A real claimed job must exist.
                interrupted = await wait_for(lambda:db.experiments.find_one({'campaign_id':cid,'status':'running'}))
                mark('kill', experiment_id=interrupted['_id'], attempt=interrupted['attempt'])
                await page.mouse.down()
                await page.mouse.up()
                await expect(page.locator('body')).to_have_attribute('data-phase','stopped',timeout=15000)
                after_kill = await asyncio.to_thread(lambda:db.experiments.find_one({'_id':interrupted['_id']}))
                assert after_kill['status']=='running', 'Stop missed the experiment; do not claim recovery'
                assert 'result' not in after_kill or after_kill['result'] is None
                mark('stopped')
                await park()
                await asyncio.sleep(4)
                await page.screenshot(path=str(OUT/'stopped.png'))
                mark('restart')
                await click('#btn-start')
                await park()
                retried = await wait_for(lambda:db.experiments.find_one({'_id':interrupted['_id'],'status':'done','attempt':2}))
                mark('retry_committed', experiment_id=retried['_id'], value=retried['result']['val_balanced_accuracy'])
                for old in before:
                    current = await asyncio.to_thread(db.experiments.find_one, {'_id':old['_id']})
                    assert current['result']==old['result'] and current['attempt']==old['attempt']
                proof = {'interrupted_id':interrupted['_id'],'interrupted_attempt':interrupted['attempt'],
                         'retried_attempt':retried['attempt'],'retry_result':retried['result'],
                         'preserved_results':[{'id':e['_id'],'attempt':e['attempt'],'result':e['result']} for e in before]}
                (OUT/'recovery-proof.json').write_text(json.dumps(clean(proof),indent=2))
                await asyncio.sleep(2)
                await page.screenshot(path=str(OUT/'recovered.png'))
                await wait_for(lambda:db.experiments.count_documents({'campaign_id':cid,'status':'done'})>=4)
                mark('clear_context')
                await click('#btn-reset')
                await asyncio.sleep(1.5)
                mark('goal_change')
                await click('#limit-seg button[data-v="9"]')
                await expect(page.locator('#electrode-count')).to_have_text('9')
                await park()
                mark('nine_visible')
                await asyncio.sleep(3)
                await page.screenshot(path=str(OUT/'nine-electrodes.png'))
                new_packet = await wait_for(lambda:db.packets.find_one({'campaign_id':cid,'goal.goal_version':2,'context_epoch':1}))
                mark('new_goal_packet', packet_id=new_packet['_id'])
                new_job = await wait_for(lambda:db.experiments.find_one({'campaign_id':cid,'proposed_by.packet_id':new_packet['_id'],'status':'done'}))
                assert new_job['config']['channels']=='central9'
                mark('adapted_result', experiment_id=new_job['_id'], value=new_job['result']['val_balanced_accuracy'])
                await asyncio.sleep(3)
                mark('code')
                await click('[data-view="code"]')
                await click('[data-source="rehydrate"]')
                await expect(page.locator('#source-path')).to_contain_text('rehydrate')
                await park()
                mark('code_visible')
                await asyncio.sleep(5)
                mark('return')
                await click('[data-view="live"]')
                await park()
                await wait_for(lambda:db.campaigns.find_one({'_id':cid,'state':'DONE'}))
                mark('done')
                await asyncio.sleep(6)
                await page.screenshot(path=str(OUT/'completed.png'))
                mark('end')
                assert not errors, errors
            finally:
                stop_watch.set()
                await watcher
                (OUT/'event-observations.json').write_text(json.dumps(observations,indent=2))
                for name,collection in [('events',db.events),('experiments',db.experiments),('packets',db.packets)]:
                    rows = await asyncio.to_thread(lambda:list(collection.find({'campaign_id':cid})))
                    (OUT/f'{name}.json').write_text(json.dumps(clean(rows),indent=2))
                (OUT/'browser-errors.json').write_text(json.dumps(errors))
                await context.close()
                await video.save_as(str(OUT/'raw-continuous.webm'))
                await browser.close()
                print('Raw capture:', OUT/'raw-continuous.webm', flush=True)


if __name__=='__main__':
    asyncio.run(main())
