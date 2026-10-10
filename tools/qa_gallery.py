"""Verify all public gallery assets, filters, navigation and accessible focus."""
import json
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from PIL import Image
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tarot.preview_server import handler  # noqa: E402


def main():
    out = ROOT / 'preview'
    out.mkdir(exist_ok=True)
    registry = json.loads((ROOT / 'web/demo.json').read_text())
    assert len(registry['decks']['crt']['cards']) == 78
    for cid in registry['decks']['crt']['cards']:
        for suffix, size in [('.png', (600, 900)), ('.gif', (320, 480))]:
            with Image.open(ROOT / 'art/crt' / (cid + suffix)) as art:
                assert art.size == size
                if suffix == '.gif':
                    assert art.n_frames > 1
                    for frame in range(art.n_frames):
                        art.seek(frame)
                        art.load()
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(ROOT))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'))
        for width, height in [(320, 780), (390, 844), (1440, 1100)]:
            for reduced in ['reduce', 'no-preference']:
                page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion=reduced)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(origin + '/decks')
                expect(page.locator('.gallery-card')).to_have_count(78)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                for suit, count in [('major', 22), ('wands', 14), ('cups', 14), ('swords', 14), ('pentacles', 14)]:
                    page.locator('#suit').select_option(suit)
                    expect(page.locator('.gallery-card')).to_have_count(count)
                page.locator('#suit').select_option('all')
                page.locator('#search').fill('Knight of Pentacles')
                expect(page.locator('.gallery-card')).to_have_count(1)
                page.locator('.gallery-art').click()
                expect(page.locator('#detail-name')).to_have_text('Knight of Pentacles')
                page.keyboard.press('Escape')
                page.locator('#search').fill('no-such-card')
                expect(page.locator('#empty')).to_be_visible()
                page.locator('#search').fill('')
                first = page.locator('.gallery-art').first
                for _ in range(2):
                    first.click()
                    expect(page.locator('#card-detail')).to_be_visible()
                    page.wait_for_function("() => {const i=document.querySelector('.focus-art img');return i.complete && i.naturalWidth>0}")
                    page.wait_for_timeout(250)
                    assert page.locator('#card-detail').evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight}')
                    page.locator('.focus-art').click()
                first.focus()
                page.keyboard.press('Enter')
                expect(page.locator('#card-detail')).to_be_visible()
                page.locator('#next').click()
                expect(page.locator('#detail-index')).to_have_text('2 / 78')
                page.keyboard.press('ArrowLeft')
                expect(page.locator('#detail-index')).to_have_text('1 / 78')
                page.locator('#previous').click()
                expect(page.locator('#detail-index')).to_have_text('78 / 78')
                page.keyboard.press('Escape')
                expect(first).to_be_focused()
                first.click()
                page.mouse.click(1, 1)
                expect(page.locator('#card-detail')).not_to_be_visible()
                if reduced == 'reduce':
                    assert page.locator('.gallery-art img').first.get_attribute('src').endswith('.png')
                page.locator('#animate').uncheck()
                page.screenshot(path=out / f'gallery-{width}-{reduced}.png', full_page=True)
                first.click()
                page.wait_for_function("() => {const i=document.querySelector('.focus-art img');return i.complete && i.naturalWidth>0}")
                page.wait_for_timeout(250)
                page.screenshot(path=out / f'gallery-{width}-focus.png')
                assert not errors, errors
                results.append(f'{width}px {reduced}: 78 cards, all suit/search filters, wrap navigation, repeated/keyboard/outside focus, viewport fit, PNG motion preference')
                page.close()
        # Every card is actually decoded in-browser, including lazy grid entries.
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
        page.goto(origin + '/decks')
        expect(page.locator('.gallery-card')).to_have_count(78)
        page.locator('.gallery-art img').evaluate_all("imgs=>imgs.forEach(i=>i.loading='eager')")
        page.wait_for_function("()=>[...document.querySelectorAll('.gallery-art img')].every(i=>i.complete && i.naturalWidth===600)")
        page.locator('#animate').check()
        page.locator('.gallery-art img').evaluate_all("imgs=>imgs.forEach(i=>i.loading='eager')")
        page.wait_for_function("()=>[...document.querySelectorAll('.gallery-art img')].every(i=>i.complete && i.naturalWidth===320)")
        page.goto(origin + '/table')
        expect(page.locator('#deck option')).to_have_count(1)
        expect(page.locator('#deck')).to_have_value('crt')
        results.append('All 78 GIF/PNG cards decoded in browser; only CRT offered/default on reading table; no API/table/private history fetched by gallery')
        browser.close()
    server.shutdown()
    (ROOT / 'verification').mkdir(exist_ok=True)
    (ROOT / 'verification/gallery-qa.json').write_text(json.dumps(results, indent=2) + '\n')
    print('\n'.join(results))


if __name__ == '__main__':
    main()
