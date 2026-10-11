import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from tarot.boards import render_board
from tarot.ui import reading


class Boards(unittest.TestCase):
    def test_layouts_and_retry(self):
        root = Path(__file__).resolve().parents[1]
        registry = json.loads((root / 'registry.json').read_text())
        ids = registry['decks']['crt']['cards']
        with tempfile.TemporaryDirectory() as tmp:
            for count in (1, 2, 3, 5, 10):
                spec = {'token': f'{count:032x}', 'deck': 'crt', 'cards': ids[:count], 'positions': [f'Position {i}' for i in range(count)], 'spread': 'Fixture spread'}
                target = render_board(spec, registry, Path(tmp), root / 'art')
                original = target.read_bytes()
                self.assertEqual(render_board(spec, registry, Path(tmp), root / 'art').read_bytes(), original)
                with Image.open(target) as image:
                    self.assertEqual(image.width, min(3, count)*570+120)
                    self.assertGreater(image.height, 1000)
            spec['token'] = '../escape'
            with self.assertRaises(ValueError):
                render_board(spec, registry, Path(tmp), root / 'art')

    def test_single_board_and_accessible_spread_text(self):
        registry = json.loads(Path('registry.json').read_text())
        ids = registry['decks']['crt']['cards'][:3]
        payload = reading({'reading_layout': 'board', 'public_url': 'https://example.com'}, registry, 'C', 'crt', registry['spreads']['three'], ids, 1, 75)
        self.assertEqual(sum(block['type'] == 'image' for block in payload['blocks']), 1)
        self.assertEqual(payload['_board']['cards'], ids)
        self.assertIn('Past · Present · Possible path', payload['text'])
        for cid in ids:
            self.assertIn(next(c['name'] for c in registry['cards'] if c['id'] == cid), payload['text'])
