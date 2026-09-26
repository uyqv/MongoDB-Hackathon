"""Browser regression checks with isolated HTTP fixtures; no campaign writes.

    .venv/bin/python scripts/video/check_dashboard.py
"""
import asyncio
import json
import os
from collections import Counter
from pathlib import Path

from playwright.async_api import async_playwright, expect

BASE = os.environ.get('DEMO_API', 'http://localhost:8001')
OUT = Path('run/video-v3/checks')


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    campaign = {'_id': 'qa-a', 'state': 'PLAN', 'context_epoch': 0, 'goal_version': 1,
                'constraints': {'max_channels': 64}, 'budget': {'max_experiments': 10},
                'incumbent': None, 'running': []}
    worker = {'running': True, 'campaign_id': 'qa-a', 'pid': 100}
    events = [{'_id': 'old', 'type': 'packet_built', 'ts': '2026-09-26T12:00:00Z', 'payload': {'packet_id': 'p-old'}}]
    packet = {'packet_id': 'p-old', 'context_epoch': 0, 'token_estimate': 420, 'budget_tokens': 4000,
              'goal_version': 1, 'retrieved': [], 'leaders': []}
    failed = False
    latency = .8
    active, maximum = Counter(), Counter()
    reads = []
    checks = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        async def handle(route):
            nonlocal failed
            path = route.request.url.split('/api', 1)[1].split('?', 1)[0]
            if path.startswith('/eeg') or path.startswith('/source') or path == '/proof':
                await route.continue_()
                return
            reads.append(path)
            active[path] += 1
            maximum[path] = max(maximum[path], active[path])
            try:
                if latency:
                    await asyncio.sleep(latency)
                if failed:
                    await route.abort('failed')
                    return
                if path == '/campaigns':
                    value = [campaign, {**campaign, '_id': 'qa-b', 'state': 'DONE'}]
                elif path == '/worker/status':
                    value = worker
                elif path.endswith('/experiments'):
                    value = []
                elif path.endswith('/events'):
                    value = events
                elif '/packets/' in path:
                    value = packet
                else:
                    value = {**campaign, '_id': 'qa-b', 'state': 'DONE'} if path.endswith('qa-b') else campaign
                await route.fulfill(json=value)
            finally:
                active[path] -= 1

        await page.route('**/api/**', handle)
        await page.goto(BASE + '/?campaign=qa-a')
        await page.locator('#btn-history').click()
        await expect(page.locator('[data-event="old"]')).to_be_visible()
        await page.locator('#close-inspector').click()
        latency = 0
        await expect(page.locator('#state-label')).to_have_text('Choosing the next step')
        await expect(page.locator('#saved-count')).to_have_text('0')
        assert await page.locator('#travel-signals circle').count() == 0
        assert await page.locator('#btn-kill').is_enabled()
        assert not await page.locator('#btn-start').is_enabled()
        assert await page.evaluate('document.documentElement.scrollHeight <= innerHeight')
        checks.append('Empty campaign, initial history is quiet, early-opened history populates, controls reflect worker ownership, 1080p fits')
        await page.evaluate("window.added=0; new MutationObserver(ms=>{for(const m of ms) window.added+=m.addedNodes.length}).observe(document.querySelector('#travel-signals'),{childList:true})")
        events.append({'_id': 'new', 'type': 'packet_built', 'ts': '2026-09-26T12:01:00Z', 'payload': {'packet_id': 'p-new'}})
        packet['packet_id'] = 'p-new'
        await page.wait_for_timeout(2300)
        assert await page.evaluate('window.added') == 6
        await page.wait_for_timeout(1000)
        assert await page.evaluate('window.added') == 6
        checks.append('New packet animates once; repeated event IDs do not animate again')
        await page.locator('#btn-follow').click()
        await expect(page.locator('#camera')).to_have_attribute('data-focus', 'overview')
        await page.locator('#btn-inspect').click()
        await expect(page.locator('#inspector')).to_be_visible()
        await expect(page.locator('#inspector-body')).to_contain_text('No prior numerical evidence')
        await page.locator('#close-inspector').click()
        await page.locator('#btn-history').click()
        await page.locator('[data-event="old"]').click()
        assert '/campaigns/qa-a/packets/p-old' in reads
        await page.locator('#close-inspector').click()
        checks.append('Overview toggle, evidence inspector, campaign-scoped historical packet request')
        campaign['state'] = 'WAITING'
        await expect(page.locator('body')).to_have_attribute('data-phase', 'waiting')
        await page.screenshot(path=str(OUT / 'waiting.png'))
        campaign['state'] = 'FAILED'
        await expect(page.locator('body')).to_have_attribute('data-phase', 'failed')
        await expect(page.locator('#btn-start')).to_be_disabled()
        checks.append('Waiting and failed states render without claiming active execution')
        campaign['state'] = 'PLAN'
        failed = True
        await expect(page.locator('body')).to_have_attribute('data-connected', 'false')
        assert await page.locator('#travel-signals circle').count() == 0
        assert await page.locator('.orbit').evaluate("e=>getComputedStyle(e).animationPlayState") == 'paused'
        await expect(page.locator('#btn-kill')).to_be_disabled()
        failed = False
        await expect(page.locator('body')).to_have_attribute('data-connected', 'true')
        assert await page.evaluate('window.added') == 6
        checks.append('Connection loss stops motion and controls; reconnection does not replay history')
        latency = .8
        await page.wait_for_timeout(2600)
        assert all(n == 1 for n in maximum.values()), maximum
        checks.append('800 ms responses do not overlap a subsequent 500 ms polling cycle')
        await page.select_option('#campaign-select', 'qa-b')
        await expect(page.locator('#campaign-id')).to_have_text('qa-b')
        await expect(page.locator('body')).to_have_attribute('data-phase', 'done')
        await expect(page.locator('#btn-kill')).to_be_disabled()
        checks.append('Campaign switch discards stale requests and cannot stop another campaign worker')
        latency = 0
        await page.select_option('#campaign-select', 'qa-a')
        await page.emulate_media(reduced_motion='reduce')
        await expect(page.locator('#camera')).to_have_attribute('data-focus', 'overview')
        assert await page.locator('.orbit').evaluate("e=>getComputedStyle(e).animationName") == 'none'
        campaign['context_epoch'] = 1
        await expect(page.locator('#packet-tokens')).to_have_text('Awaiting fresh evidence')
        campaign['constraints']['max_channels'] = 9
        await expect(page.locator('#electrode-count')).to_have_text('9')
        assert await page.locator('.electrode:not(.off)').count() == 9
        await expect(page.locator('#best-detail')).to_have_text('No eligible result yet')
        checks.append('Reduced motion, cleared context, nine-electrode count, honest empty eligibility')
        await page.screenshot(path=str(OUT / 'empty-nine.png'))
        assert not errors, errors
        checks.append('No browser JavaScript errors')
        await browser.close()
    (OUT / 'browser-checks.json').write_text(json.dumps({'passed': checks, 'max_concurrent_per_endpoint': dict(maximum)}, indent=2))
    print(json.dumps({'checks_passed': len(checks), 'checks': checks}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
