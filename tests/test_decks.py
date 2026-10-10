import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tarot.core import Store, load_registry
from tarot.decks import available_decks, default_deck
from tarot.ui import Parlor


class DeckChoiceTests(unittest.TestCase):
    def test_only_crt_selected_but_historical_shoe_untouched(self):
        registry = load_registry('registry.json')
        self.assertEqual(list(available_decks(registry)), ['crt'])
        self.assertEqual(default_deck(registry), 'crt')
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / 'state.db'), registry)
            store.command('old', 'T', 'C', 'U', 'draw midnight')
            with store.connect() as db:
                before = db.execute('SELECT * FROM shoes').fetchall()
            modal = Parlor(store).modal('test', 'draw')
            selector = next(block for block in modal['blocks'] if block.get('block_id') == 'deck')['element']
            self.assertEqual([option['value'] for option in selector['options']], ['crt'])
            self.assertEqual(selector['initial_option']['value'], 'crt')
            self.assertEqual(store.command('decks', 'T', 'C', 'U', 'decks')['text'], 'crt')
            result = store.command('default', 'T', 'C', 'U', 'draw')
            self.assertEqual(result['deck'], 'crt')
            with store.connect() as db:
                self.assertIn(before[0], db.execute('SELECT * FROM shoes').fetchall())
            # Registry compatibility retains old card membership and artwork.
            self.assertEqual(len(registry['decks']['midnight']['cards']), 78)

    def test_default_schedule_catches_up_today_once_without_backfill(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / 'state.db'), load_registry('registry.json'))
            store.command('schedule', 'T', 'C', 'U', 'schedule 09:00 America/Chicago')
            now = datetime(2026, 10, 10, 16, tzinfo=timezone.utc)
            store.tick(now)
            with store.connect() as db:
                before = db.execute('SELECT * FROM shoes').fetchall()
                sid, raw = db.execute('SELECT id,spec FROM schedules').fetchone()
                self.assertEqual(json.loads(raw)['deck'], 'crt')
                keys = [row[0] for row in db.execute('SELECT id FROM requests')]
                self.assertIn(f'daily:{sid}:2026-10-10', keys)
                self.assertFalse(any('2026-10-09' in key for key in keys))
            store.tick(now)
            with store.connect() as db:
                self.assertEqual(before, db.execute('SELECT * FROM shoes').fetchall())
                db.execute('UPDATE schedules SET enabled=0')
            store.tick(datetime(2026, 10, 11, 16, tzinfo=timezone.utc))
            with store.connect() as db:
                self.assertEqual(before, db.execute('SELECT * FROM shoes').fetchall())

    def test_extensible_custom_default_and_invalid_default(self):
        data = json.loads(Path('registry.json').read_text())
        data['decks']['custom'] = {'cards': ['major-0'], 'name': 'Custom'}
        data['default_deck'] = 'custom'
        self.assertEqual(default_deck(data), 'custom')
        self.assertEqual(list(available_decks(data)), ['crt', 'custom'])
        data['default_deck'] = 'midnight'
        with self.assertRaisesRegex(ValueError, 'selectable'):
            default_deck(data)
