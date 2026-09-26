"""Record a real demo run of the dashboard as timestamped frames.

    python scripts/video/record_demo.py <campaign_id>

Needs the API running on :8000 against DB second_shift and a fresh campaign
(created with `harness.worker --new --create-only`). Drives the real run: a
worker with fault injection, the dashboard's own Start worker / Reset context /
channel budget controls, then the README and code on GitHub. Writes frames plus
marks.json (the time of each beat) to run/video/.
"""
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

API = "http://localhost:8000"
OUT = Path("run/video")
FRAMES = OUT / "frames"
W, H, SCALE = 1600, 900, 1.2          # frames come out at 1920x1080
REPO = "https://github.com/uyqv/MongoDB-Hackathon"

t0 = 0.0
marks: dict[str, float] = {}


def mark(name: str) -> None:
    marks[name] = round(time.monotonic() - t0, 3)
    print(f"{marks[name]:7.1f}s  {name}", flush=True)


def api(path: str):
    return httpx.get(API + path, timeout=10).json()


def experiments(cid: str) -> list[dict]:
    return api(f"/api/campaigns/{cid}/experiments")


async def wait_until(pred, timeout: float = 300, poll: float = 1.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return
        await asyncio.sleep(poll)
    raise TimeoutError("condition not met")


async def capture(page, stop: asyncio.Event) -> list:
    index, i = [], 0
    while not stop.is_set():
        t = time.monotonic() - t0
        path = FRAMES / f"f{i:05d}.jpg"
        try:
            await page.screenshot(path=str(path), type="jpeg", quality=90)
            index.append([round(t, 3), path.name])
            i += 1
        except Exception:
            pass  # mid-navigation; the next frame will land
        await asyncio.sleep(0.15)
    return index


async def scroll_to(page, selector: str, block: str = "start", pause: float = 1.2) -> None:
    await page.evaluate(f"document.querySelector('{selector}').scrollIntoView({{behavior: 'smooth', block: '{block}'}})")
    await asyncio.sleep(pause)


async def scroll_by(page, dy: int, pause: float = 1.0) -> None:
    await page.evaluate(f"window.scrollBy({{top: {dy}, behavior: 'smooth'}})")
    await asyncio.sleep(pause)


async def scroll_top(page, pause: float = 1.0) -> None:
    await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
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
        await page.goto(f"{API}/?campaign={cid}")
        await page.wait_for_timeout(3000)
        t0 = time.monotonic()
        stop = asyncio.Event()
        cap = asyncio.create_task(capture(page, stop))

        # intro: the goal and the real EEG input
        mark("intro")
        await asyncio.sleep(2.5)
        await scroll_to(page, "#panel-eeg", "center", pause=3.5)
        await scroll_top(page)

        # run: a real worker, with fault injection on its 4th job
        mark("run")
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "harness.worker", "--campaign", cid, "--crash-after-claim", "4",
            env={**os.environ, "DB_NAME": "second_shift"},
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.sleep(14)
        await scroll_to(page, "#panel-experiments", "start")
        rc = await proc.wait()

        # crash, then restart through the dashboard's own button
        mark("crash")
        print(f"         worker exit code {rc}", flush=True)
        await asyncio.sleep(2.5)
        await scroll_to(page, "#panel-timeline", "center", pause=3.0)
        await scroll_top(page, pause=0.8)
        mark("restart")
        await page.click("#btn-start")
        await wait_until(lambda: any(e["attempt"] >= 2 and e["status"] == "done" for e in experiments(cid)), 120)
        await scroll_to(page, "#panel-timeline", "center", pause=3.0)
        await scroll_to(page, "#panel-experiments", "start")
        await wait_until(lambda: sum(e["status"] == "done" for e in experiments(cid)) >= 6, 180)

        # goal change: wipe context, 64 -> 9 channels
        await scroll_top(page, pause=0.8)
        mark("goal")
        await page.click("#btn-reset")
        await asyncio.sleep(1.2)
        await page.select_option("#sel-channels", "9")
        await page.click("#constraint-reason")
        await page.type("#constraint-reason", "new headset has 9 electrodes", delay=35)
        await page.click("#btn-constraint")
        await asyncio.sleep(3)
        await scroll_to(page, "#panel-experiments", "start")
        await wait_until(lambda: api(f"/api/campaigns/{cid}")["state"] == "DONE", 300)
        await scroll_top(page, pause=3.0)

        # packet: what the model saw, with Jev routed notes from Vector Search
        mark("packet")
        await scroll_to(page, "#panel-packet", "start", pause=2.5)
        await scroll_by(page, 350, pause=3.0)

        # numbers: measured results in the README, then the code
        mark("numbers")
        await page.goto(f"{REPO}#measured-today", wait_until="domcontentloaded")
        await asyncio.sleep(3.0)
        await scroll_by(page, 500, pause=2.0)
        await scroll_by(page, 500, pause=2.0)
        await page.goto(f"{REPO}/blob/main/harness/worker.py", wait_until="domcontentloaded")
        await asyncio.sleep(2.5)
        await scroll_by(page, 1400, pause=2.5)

        # outro: back to the finished campaign
        mark("outro")
        await page.goto(f"{API}/?campaign={cid}")
        await asyncio.sleep(5.0)
        mark("end")

        stop.set()
        index = await cap
        await browser.close()

    (OUT / "frames.json").write_text(json.dumps(index))
    (OUT / "marks.json").write_text(json.dumps({"campaign_id": cid, "marks": marks}, indent=1))
    print(f"{len(index)} frames, {marks['end']:.1f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
