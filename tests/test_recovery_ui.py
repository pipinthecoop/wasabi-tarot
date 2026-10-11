import tempfile
import unittest
from pathlib import Path

from tarot.core import Store, load_registry
from tarot.ui import Parlor


class RecoveryUITests(unittest.TestCase):
    def test_committed_reading_visible_in_modal_and_reopen_without_redraw(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / 'state.db'), load_registry('registry.json', 'https://cards.example'))
            ui = Parlor(store)
            with store.connect() as db:
                sid = ui.create(db, 'T', 'C', 'U', 'draw')
            ui.open(sid, 'T', 'U')
            values = {'deck': {'value': {'selected_option': {'value': 'crt'}}}, 'spread': {'value': {'selected_option': {'value': 'single'}}}}
            result = ui.submit(sid, 'T', 'U', values)
            self.assertEqual(len([block for block in result['view']['blocks'] if block['type'] == 'image']), 1)
            with store.connect() as db:
                db.execute("UPDATE outbox SET status='failed',error='not_in_channel' WHERE id=?", ('ritual:' + sid,))
                before = {table: db.execute('SELECT * FROM ' + table).fetchall() for table in ['shoes', 'requests', 'outbox']}
            for _ in range(2):
                reopened = ui.open(sid, 'T', 'U')
                self.assertIn('not in this channel', reopened['text'])
                self.assertEqual(len([block for block in reopened['view']['blocks'] if block['type'] == 'image']), 1)
            with store.connect() as db:
                self.assertEqual(before, {table: db.execute('SELECT * FROM ' + table).fetchall() for table in before})
            self.assertEqual(result, ui.submit(sid, 'T', 'U', values))

    def test_open_ritual_can_reopen_after_failed_modal_request(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / 'state.db'), load_registry('registry.json'))
            ui = Parlor(store)
            with store.connect() as db:
                sid = ui.create(db, 'T', 'C', 'U', 'draw')
            self.assertIn('view', ui.open(sid, 'T', 'U'))
            self.assertNotIn('view', ui.open(sid, 'T', 'U'))
            ui.failed_open(sid, 'T', 'U')
            self.assertIn('view', ui.open(sid, 'T', 'U'))
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM shoes').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone()[0], 0)
