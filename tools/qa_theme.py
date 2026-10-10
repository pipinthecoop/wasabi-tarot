"""Capture real web UI at desktop/mobile sizes; native Block Kit approximation."""

import json
import os
import sys
import tempfile
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer
from html import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tarot.core import Store, load_registry  # noqa: E402
from tarot.server import handler  # noqa: E402
from tarot.ui import Parlor, load_theme  # noqa: E402


def slack_preview(blocks, origin):
    content = []
    for block in blocks:
        kind = block["type"]
        if kind in ("header", "section"):
            content.append(
                "<h2>" + escape(block["text"]["text"]) + "</h2>" if kind == "header" else "<p>" + escape(block["text"]["text"]).replace("\n", "<br>") + "</p>"
            )
        elif kind == "image":
            source = block["image_url"].replace("https://theme.example", origin + "/assets/theme")
            content.append('<img class="hero" alt="' + escape(block["alt_text"], quote=True) + '" src="' + source + '">')
        elif kind == "actions":
            content.append('<div class="actions">' + "".join("<button>" + escape(e["text"]["text"]) + "</button>" for e in block["elements"]) + "</div>")
        elif kind == "input":
            element = block["element"]
            selected = (
                element.get("initial_option", {})
                .get("text", {})
                .get("text", element.get("initial_value", element.get("initial_time", element.get("placeholder", {}).get("text", ""))))
            )
            content.append("<label>" + escape(block["label"]["text"]) + '<div class="input">' + escape(selected) + "</div></label>")
        elif kind == "context":
            content.append("<small>" + escape(" ".join(e.get("text", "") for e in block["elements"])) + "</small>")
        elif kind == "divider":
            content.append("<hr>")
    return """<!doctype html><meta name="viewport" content="width=device-width"><style>
    *{box-sizing:border-box}body{margin:0;background:#1a1d21;color:#e7e7e8;font:14px Arial,sans-serif;padding:22px 16px}.note{font-size:11px;color:#abb0b7;margin-bottom:24px}
    h2{font-size:18px;margin:18px 0 12px}p{line-height:1.6;font-size:14px}small{display:block;color:#aeb0b4;line-height:1.5;margin:14px 0}.hero{width:100%;border-radius:8px;display:block}
    .actions{display:flex;gap:8px;flex-wrap:wrap}button{min-height:44px;padding:10px 12px;border:1px solid #626467;border-radius:4px;background:#222529;color:white;font-weight:600}
    button:first-child{background:#007a5a;border-color:#007a5a}label{display:block;font-weight:600;margin:18px 0}.input{margin-top:8px;padding:13px;border:1px solid #6a6d72;border-radius:4px;font-weight:400;min-height:44px;color:#c4c6ca}hr{border:0;border-top:1px solid #444}
    </style><p class="note">Slack native surface approximation · actual rendering belongs to Slack</p><b>☾ Wasabi Tarot</b>""" + "".join(content)


def main():
    from playwright.sync_api import sync_playwright, expect

    out = ROOT / "preview"
    out.mkdir(exist_ok=True)
    evidence = []
    with tempfile.TemporaryDirectory() as temp:
        store = Store(
            str(Path(temp) / "preview.sqlite3"), load_registry(str(ROOT / "registry.json")), load_theme(str(ROOT / "theme.json"), "https://theme.example")
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(store, "preview-only", "PREVIEW"))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        with sync_playwright() as playwright:
            executable = os.environ.get("CHROMIUM_PATH")
            browser = playwright.chromium.launch(executable_path=executable, headless=True)
            for name, size in [
                ("desktop", {"width": 1440, "height": 1100}),
                ("mobile", {"width": 390, "height": 844}),
                ("narrow", {"width": 320, "height": 780}),
            ]:
                context = browser.new_context(viewport=size, reduced_motion="reduce")
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/table")
                page.locator(".card-slot").first.wait_for()
                assert page.locator(".card-slot").count() == 3
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name + " overflows"
                page.screenshot(path=out / f"{name}-table.png", full_page=True)
                before = page.locator("#remaining").inner_text()
                page.locator("#shuffle").click()
                page.get_by_role("button", name="Leave it as it is").click()
                assert page.locator("#remaining").inner_text() == before
                page.locator("#draw").click()
                expect(page.locator("#remaining")).to_have_text("75")
                assert page.locator(".meaning").count() == 3
                page.screenshot(path=out / f"{name}-reading.png", full_page=True)
                page.locator("#shuffle").click()
                page.get_by_role("button", name="Shuffle all cards", exact=True).click()
                expect(page.locator("#remaining")).to_have_text("78")
                expect(page.locator("#cycle")).to_contain_text("Cycle 2")
                page.locator("#spread").select_option("custom")
                page.locator("#custom").fill("Situation|Release|Next step|Invitation")
                assert page.locator(".card-slot").count() == 4
                page.locator("#draw").click()
                expect(page.locator("#remaining")).to_have_text("74")
                assert not errors, errors
                result = page.request.post(origin + "/api/ritual", data={"ritual": "untrusted", "values": {}})
                assert result.status == 403
                page.locator("#connect").click()
                page.screenshot(path=out / f"{name}-login.png", full_page=True)
                evidence.append(
                    {
                        "viewport": name,
                        "width": size["width"],
                        "checks": "no overflow; cancel; explicit shuffle; reveal; custom 4-card spread; unauthorized mutation blocked; reduced motion; no JS errors",
                    }
                )
                context.close()
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.goto(origin + "/embed/table")
            page.locator(".card-slot").first.wait_for()
            assert page.locator("#draw").is_disabled()
            assert page.locator("#shuffle").is_disabled()
            assert "Read-only" in page.locator("#mode").inner_text()
            page.screenshot(path=out / "embedded-preview.png", full_page=True)
            ui = Parlor(store)
            panel = ui.panel("preview-panel", "PREVIEW", "CHANNEL", "READER")
            page.set_content(slack_preview(panel["blocks"], origin))
            page.wait_for_load_state("networkidle")
            page.screenshot(path=out / "slack-mobile-parlor.png", full_page=True)
            with store.connect() as db:
                sid = ui.create(db, "PREVIEW", "CHANNEL", "READER", "draw")
            modal = ui.modal(sid, "draw")
            page.set_content(slack_preview(modal["blocks"], origin))
            page.wait_for_load_state("networkidle")
            page.screenshot(path=out / "slack-mobile-modal.png", full_page=True)
            with store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM shoes").fetchone()[0] == 0
            browser.close()
        server.shutdown()
    (out / "qa-results.json").write_text(
        json.dumps(
            {
                "results": evidence,
                "embed": "read-only; no channel data or mutations",
                "native_slack": "approximation, not live Slack testing",
                "production_shoes_created": 0,
            },
            indent=2,
        )
        + "\n"
    )
    print("Browser QA passed: 1440px, 390px, 320px; native Slack approximation and embedded preview captured.")


if __name__ == "__main__":
    main()
