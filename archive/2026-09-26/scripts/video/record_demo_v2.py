"""Record the demo on the redesigned dashboard, driving only its own buttons.

    python scripts/video/record_demo_v2.py <fresh_campaign_id>

Start worker, Kill worker (timed to land while an experiment runs when it
can), Start worker again, Reset context, electrode limit 9, then the Results
and Code tabs. A visible cursor shows every click. Writes timestamped frames,
frames.json and marks.json to run/video/.
"""
import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

API = "http://localhost:8000"
OUT = Path("run/video")
FRAMES = OUT / "frames"
W, H, SCALE = 1600, 900, 1.2

CURSOR_JS = """
window.addEventListener('DOMContentLoaded', () => {
  const s = document.createElement('style');
  s.textContent = `#fx-cursor{position:fixed;z-index:99999;width:22px;height:22px;margin:-3px 0 0 -3px;pointer-events:none;
    transition:transform .08s;filter:drop-shadow(0 2px 4px rgba(0,0,0,.6))}
    .fx-ripple{position:fixed;z-index:99998;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;pointer-events:none;
    border:3px solid #00ed64;animation:fxr .6s ease-out forwards}
    @keyframes fxr{to{transform:scale(4);opacity:0}}`;
  document.head.appendChild(s);
  const c = document.createElement('div'); c.id = 'fx-cursor';
  c.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="#fff" stroke="#000" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  c.style.left = '-50px'; c.style.top = '-50px';
  document.body.appendChild(c);
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });
  document.addEventListener('mousedown', e => {
    c.style.transform = 'scale(.85)';
    const r = document.createElement('div'); r.className = 'fx-ripple'; r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
    document.body.appendChild(r); setTimeout(() => r.remove(), 700);
  });
  document.addEventListener('mouseup', () => { c.style.transform = ''; });
});
"""

t0 = 0.0
marks: dict[str, float] = {}


def mark(name: str) -> None:
    marks[name] = round(time.monotonic() - t0, 3)
    print(f"{marks[name]:7.1f}s  {name}", flush=True)


def api(path: str):
    return httpx.get(API + path, timeout=10).json()


def exps(cid):
    return api(f"/api/campaigns/{cid}/experiments")


def n_done(cid) -> int:
    return sum(e["status"] == "done" for e in exps(cid))


async def wait_until(pred, timeout=300, poll=0.5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        await asyncio.sleep(poll)
    raise TimeoutError("condition not met")


async def capture(page, stop):
    index, i = [], 0
    while not stop.is_set():
        t = time.monotonic() - t0
        path = FRAMES / f"f{i:05d}.jpg"
        try:
            await page.screenshot(path=str(path), type="jpeg", quality=92)
            index.append([round(t, 3), path.name])
            i += 1
        except Exception:
            pass
        await asyncio.sleep(0.12)
    return index


async def click(page, selector, pause=0.6):
    box = await page.locator(selector).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    await page.mouse.move(x, y, steps=18)
    await asyncio.sleep(0.35)
    await page.mouse.down()
    await asyncio.sleep(0.08)
    await page.mouse.up()
    await asyncio.sleep(pause)


async def main(cid: str) -> None:
    global t0
    assert api(f"/api/campaigns/{cid}")["used"] == 0, "campaign must be fresh"
    assert not api("/api/worker/status")["running"], "a dashboard worker is already running"
    shutil.rmtree(FRAMES, ignore_errors=True)
    FRAMES.mkdir(parents=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        await page.add_init_script(CURSOR_JS)
        await page.goto(f"{API}/?campaign={cid}")
        await page.wait_for_timeout(3500)
        await page.mouse.move(W * 0.55, H * 0.55)
        t0 = time.monotonic()
        stop = asyncio.Event()
        cap = asyncio.create_task(capture(page, stop))

        mark("intro")
        await asyncio.sleep(4.0)

        mark("start")
        await click(page, "#btn-start")
        await page.mouse.move(W * 0.62, H * 0.5, steps=25)
        # let three experiments land, then kill while the fourth is executing if we can catch it
        await wait_until(lambda: n_done(cid) >= 3, 240)
        caught = False
        end = time.monotonic() + 25
        while time.monotonic() < end:
            if api(f"/api/campaigns/{cid}")["state"] in ("EXECUTE",):
                caught = True
                break
            await asyncio.sleep(0.08)
        mark("kill")
        await click(page, "#btn-kill", pause=0.2)
        print(f"         kill landed during EXECUTE: {caught}", flush=True)
        await page.mouse.move(W * 0.62, H * 0.5, steps=20)
        await asyncio.sleep(4.0)

        mark("restart")
        await click(page, "#btn-start")
        await page.mouse.move(W * 0.62, H * 0.5, steps=20)
        await wait_until(lambda: n_done(cid) >= 6, 240)
        await asyncio.sleep(1.0)

        mark("goal")
        await click(page, "#btn-reset", pause=1.4)
        await click(page, '#limit-seg button[data-v="9"]', pause=0.4)
        await page.mouse.move(W * 0.62, H * 0.5, steps=20)
        await wait_until(lambda: api(f"/api/campaigns/{cid}")["state"] == "DONE", 300)
        await asyncio.sleep(3.0)
        mark("done")
        await asyncio.sleep(2.0)

        mark("results")
        await click(page, '.tabs button[data-view="results"]', pause=5.0)
        mark("code")
        await click(page, '.tabs button[data-view="code"]', pause=5.0)
        await page.mouse.move(W - 20, H - 20, steps=10)
        mark("end")

        stop.set()
        index = await cap
        await browser.close()

    (OUT / "frames.json").write_text(json.dumps(index))
    (OUT / "marks.json").write_text(json.dumps({"campaign_id": cid, "kill_during_execute": caught, "marks": marks}, indent=1))
    print(f"{len(index)} frames, {marks['end']:.1f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
