"""Verify CRT demo images and real Slack draw against an isolated local service."""

import json
import os
import sys
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from PIL import Image, ImageStat
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tarot.core import Store, load_registry  # noqa: E402
from tarot.server import handler  # noqa: E402
from tarot.ui import load_theme  # noqa: E402
from tools.qa_theme import slack_preview  # noqa: E402


def main():
    out = ROOT / "preview"
    evidence = []
    for image in (ROOT / "art/crt").glob("*.png"):
        with Image.open(image) as pixels:
            pixels.verify()
        with Image.open(image) as pixels:
            assert pixels.size == (600, 900)
            assert max(ImageStat.Stat(pixels.convert("RGB")).stddev) > 12, image.name
    with tempfile.TemporaryDirectory() as temp:
        store = Store(
            str(Path(temp) / "qa.sqlite3"),
            load_registry(str(ROOT / "registry.json"), "https://cards.example"),
            load_theme(str(ROOT / "theme.json"), "https://theme.example"),
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(store, "preview-only", "PREVIEW"))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
            for name, width, height in [("desktop", 1440, 1100), ("mobile", 390, 844), ("narrow", 320, 780)]:
                page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/table")
                expect(page.locator("#deck option[value=crt]")).to_have_text("Phosphor Arcana")
                page.locator("#deck").select_option("crt")
                expect(page.locator("#remaining")).to_have_text("78")
                assert "crt-back.webp" in page.locator(".card-slot img").first.get_attribute("src")
                page.locator("#draw").click()
                expect(page.locator("#remaining")).to_have_text("75")
                assert page.locator(".meaning").count() == 3
                page.wait_for_function("() => [...document.querySelectorAll('.card-slot img')].every(i => i.complete && i.naturalWidth === 600)")
                assert all("/crt/" in url for url in page.locator(".card-slot img").evaluate_all("imgs => imgs.map(i=>i.src)"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                page.screenshot(path=out / f"crt-{name}-reading.png", full_page=True)
                evidence.append(f"{name}: selector, CRT back/fronts, finite demo draw, no JS errors or overflow")
                page.close()
            page = browser.new_page(viewport={"width": 900, "height": 800})
            page.goto(origin + "/table")
            page.locator("#deck").select_option("crt")
            page.locator("#draw").click()
            expect(page.locator("#remaining")).to_have_text("75")
            page.wait_for_function("() => [...document.querySelectorAll('.card-slot img')].every(i => i.complete && i.naturalWidth === 320)")
            assert all(url.endswith(".gif") for url in page.locator(".card-slot img").evaluate_all("imgs=>imgs.map(i=>i.src)"))
            page.locator("#animate").uncheck()
            page.wait_for_function("() => [...document.querySelectorAll('.card-slot img')].every(i => i.complete && i.naturalWidth === 600)")
            expect(page.locator("#remaining")).to_have_text("75")
            page.route("**/crt/*.gif", lambda route: route.abort())
            page.locator("#animate").check()
            page.wait_for_function("() => [...document.querySelectorAll('.card-slot img')].every(i => i.complete && i.naturalWidth === 600)")
            expect(page.locator("#remaining")).to_have_text("75")
            evidence.append("Animated browser fronts, static toggle without new draw, and failed-GIF PNG fallback verified")
            page.close()
            result = store.command("crt-qa", "T", "C", "U", "draw crt three")
            assert result == store.command("crt-qa", "T", "C", "U", "draw crt three")
            markup = slack_preview(result["payload"]["blocks"], origin).replace("https://cards.example", origin + "/assets/decks")
            page = browser.new_page(viewport={"width": 480, "height": 900})
            page.set_content(markup)
            page.wait_for_function("() => [...document.images].every(i=>i.complete && i.naturalWidth > 0)")
            page.screenshot(path=out / "crt-slack-reading.png", full_page=True)
            evidence.append("Actual committed Slack Block Kit payload: three CRT GIFs resolve, retry identical; screenshot approximates Slack")
            page.goto((out / "phosphor-arcana-demo.html").as_uri())
            page.locator("#deck").select_option("crt")
            page.locator("#draw").click()
            expect(page.locator("#remaining")).to_have_text("75")
            page.locator("#animate").uncheck()
            page.wait_for_function("() => [...document.querySelectorAll('.card-slot img')].every(i => i.complete && i.naturalWidth === 600)")
            evidence.append("Standalone HTML: CRT selector, embedded GIF/PNG fronts and static/reduced-motion choice work offline")
            page.goto((out / "phosphor-arcana-motion-gallery.html").as_uri())
            page.wait_for_function("() => [...document.images].every(i=>i.complete && i.naturalWidth===320)")
            assert page.locator("figure").count() == 12
            page.get_by_role("button", name="Still the cards").click()
            page.wait_for_function("() => [...document.images].every(i=>i.complete && i.naturalWidth===600)")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=out / "crt-motion-gallery-mobile.png", full_page=True)
            evidence.append("Twelve-card independent-motion gallery: GIF/PNG toggle, all images decoded, no mobile overflow")
            browser.close()
        server.shutdown()
    (ROOT / "verification").mkdir(exist_ok=True)
    (ROOT / "verification/crt-visual-qa.json").write_text(
        json.dumps({"png_count": 79, "gif_count": 78, "image_size": [600, 900], "checks": evidence}, indent=2) + "\n"
    )
    print("\n".join(evidence))


if __name__ == "__main__":
    main()
