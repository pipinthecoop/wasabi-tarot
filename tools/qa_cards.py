"""Check caption flow, reveal, accessible enlargement and unchanged finite state."""
import json
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tarot.preview_server import handler  # noqa: E402


def main():
    out = ROOT / 'preview'
    out.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(ROOT))
    Thread(target=server.serve_forever, daemon=True).start()
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'))
        for width, height in [(320, 780), (390, 844), (1440, 1100)]:
            for reduced in ['reduce', 'no-preference']:
                page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion=reduced)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/table')
                page.locator('#deck').select_option('crt')
                page.locator('#draw').click()
                expect(page.locator('#remaining')).to_have_text('75')
                page.wait_for_timeout(800)
                face = page.locator('.card-slot .card').first
                assert face.evaluate("e => e.classList.contains('is-revealed')")
                assert face.locator('.card-front').evaluate("e => getComputedStyle(e).backfaceVisibility === 'hidden'")
                duration = face.locator('.card-turn').evaluate("e => getComputedStyle(e).transitionDuration")
                assert duration == ('0s' if reduced == 'reduce' else '0.65s'), duration
                page.locator('.card-slot .card-name').first.evaluate("e => e.textContent='Knight of Pentacles'")
                for slot in page.locator('.card-slot').all():
                    assert slot.evaluate("e => e.querySelector('.card-name').offsetTop >= e.querySelector('.card').offsetHeight")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                for _ in range(2):
                    face.click()
                    expect(page.locator('.card-focus')).to_be_visible()
                    page.wait_for_timeout(250)
                    assert page.locator('.card-focus').evaluate('e => {const r=e.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight}')
                    if reduced == 'reduce':
                        page.screenshot(path=out / f'cards-{width}-focus.png')
                    page.locator('.focus-art').click()
                    expect(page.locator('.card-focus')).not_to_be_visible()
                face.focus()
                page.keyboard.press('Enter')
                expect(page.locator('.card-focus')).to_be_visible()
                page.keyboard.press('Escape')
                expect(face).to_be_focused()
                face.click()
                page.mouse.click(2, 2)
                expect(page.locator('.card-focus')).not_to_be_visible()
                page.locator('#animate').set_checked(reduced == 'reduce')
                expect(page.locator('#remaining')).to_have_text('75')
                expect(page.locator('#discard')).to_have_text('3')
                assert page.locator('.meaning').count() == 3
                assert not errors, errors
                page.screenshot(path=out / f'cards-{width}-{reduced}.png', full_page=True)
                results.append(f'{width}px {reduced}: caption, flip, repeated focus, outside/Escape/Enter, viewport and unchanged 75/3 state')
                page.close()
        browser.close()
    server.shutdown()
    (ROOT / 'verification').mkdir(exist_ok=True)
    (ROOT / 'verification/card-interaction-qa.json').write_text(json.dumps(results, indent=2) + '\n')
    print('\n'.join(results))


if __name__ == '__main__':
    main()
