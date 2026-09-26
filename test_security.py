"""Controles de seguranca com entradas falsas; nao instala hooks nem envia teclas."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.constants import STEP_KEY
from app.models.settings import Settings
from app.services.action_executor import ActionExecutor
from app.services.combo_manager import ComboManager, MacroAction
from app.services.profile_manager import slugify
from app.services.window_manager import WindowManager
from app.utils.jsonio import read_json, write_json


class SecurityTests(unittest.TestCase):
    def test_safe_defaults(self):
        settings = Settings()
        self.assertTrue(settings.require_game_focus)
        self.assertFalse(settings.autostart_hotkeys)

    def test_profile_names_cannot_escape_directory(self):
        for name in ('../../outside', r'C:\Windows\outside', '../a/../../b', '..', ''):
            with self.subTest(name=name):
                slug = slugify(name)
                self.assertRegex(slug, r'^[a-z0-9_-]+$')

    def test_launcher_and_other_apps_are_rejected(self):
        windows = WindowManager(frozenset({'pxg.exe'}), frozenset())
        self.assertTrue(windows.decide(r'C:\Games\pxg.exe', ''))
        for executable in ('launcher.exe', 'notepad.exe', ''):
            self.assertFalse(windows.decide(executable, ''))

    def test_invalid_json_is_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            path.write_text('{invalid', encoding='utf-8')
            self.assertIsNone(read_json(path))
            self.assertTrue(path.with_suffix('.json.bak').exists())
            self.assertTrue(write_json(path, {'name': 'safe'}))
            self.assertEqual(read_json(path), {'name': 'safe'})

    def test_send_failure_releases_keys(self):
        keyboard = Mock()
        keyboard.press.side_effect = RuntimeError('simulated failure')
        with patch('app.services.action_executor.keyboard_module', return_value=keyboard):
            self.assertFalse(ActionExecutor(Settings()).tap('ctrl+1', 0))
        self.assertTrue(keyboard.release.called)

    def test_cancel_stops_next_step_and_restores_pointer(self):
        executor = Mock()
        manager = ComboManager(executor)
        executor.tap.side_effect = lambda *args: manager._cancel.set() or True
        manager._run([MacroAction('first', STEP_KEY, key='1'),
                      MacroAction('second', STEP_KEY, key='2')], 'cancel test')
        executor.tap.assert_called_once_with('1', 0)
        executor.restore_pointer.assert_called_once()

    def test_failure_stops_next_step_and_restores_pointer(self):
        executor = Mock()
        executor.tap.return_value = False
        manager = ComboManager(executor)
        manager._run([MacroAction('first', STEP_KEY, key='1'),
                      MacroAction('second', STEP_KEY, key='2')], 'failure test')
        self.assertEqual(executor.tap.call_count, 1)
        executor.restore_pointer.assert_called_once()

    @unittest.expectedFailure
    def test_known_gap_focus_loss_must_block_next_step(self):
        """Reproducao SEC-001: ainda nao existe guarda de foco entre etapas."""
        focused = [True]
        sent = []
        executor = Mock()

        def tap(key, hold):
            sent.append((key, focused[0]))
            focused[0] = False  # Alt+Tab depois da primeira acao.
            return True

        executor.tap.side_effect = tap
        manager = ComboManager(executor)
        manager._run([MacroAction('first', STEP_KEY, key='1'),
                      MacroAction('second', STEP_KEY, key='2')], 'focus test')
        self.assertEqual(sent, [('1', True)])


if __name__ == '__main__':
    unittest.main()
