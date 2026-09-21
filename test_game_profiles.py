"""Regressoes de migracao e isolamento entre jogos, sem hooks reais."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.profile import Profile, default_profile
from app.services.controller import AppController
from app.utils.jsonio import write_json


class GameProfilesTest(unittest.TestCase):
    def test_legacy_migration_switch_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = root / "profiles"
            profiles.mkdir()
            legacy = default_profile("Meu PKA").to_dict()
            legacy.pop("game")
            legacy["macros"][0]["steps"][0]["key"] = "y"
            write_json(profiles / "pka.json", legacy)
            write_json(root / "settings.json", {
                "active_profile": "Meu PKA", "wheel_debounce_ms": 777,
                "chat_key": "tab",
            })
            with (
                patch("app.services.profile_manager.PROFILES_DIR", profiles),
                patch("app.services.profile_manager.ensure_dirs"),
                patch("app.services.settings_manager.SETTINGS_FILE", root / "settings.json"),
                patch("app.services.settings_manager.ensure_dirs"),
                patch.object(AppController, "setup_emergency", return_value=True),
            ):
                controller = AppController()
                self.assertEqual(controller.profile.game, "PKA")
                self.assertEqual(controller.settings.wheel_debounce_ms, 777)
                self.assertEqual(controller.profile.macros[0].steps[0].key, "y")
                self.assertTrue(controller.windows.decide(r"C:\PokeAlliance_dx.exe", ""))
                controller.set_active_profile("PXG")
                self.assertEqual(controller.profile.macros, [])
                self.assertFalse(any(skill.key for skill in controller.profile.skills))
                self.assertFalse(controller.windows.decide(r"C:\PokeAlliance_dx.exe", "pokealliancev3"))
                controller.settings.client_executable = r"C:\Games\test-pxg.exe"
                controller.settings.wheel_debounce_ms = 123
                controller.settings.chat_key = ""
                self.assertTrue(controller.save_settings())
                self.assertTrue(controller.windows.decide(r"C:\Games\test-pxg.exe", ""))
                controller.set_active_profile("Meu PKA")
                self.assertEqual(controller.settings.wheel_debounce_ms, 777)
                self.assertEqual(controller.settings.chat_key, "tab")
                self.assertFalse(controller.windows.decide(r"C:\Games\test-pxg.exe", ""))
                controller.set_active_profile("PXG")
                self.assertEqual(controller.settings.wheel_debounce_ms, 123)
                self.assertEqual(controller.settings.chat_key, "")
                controller.save_settings()
                restored = AppController()
                self.assertEqual(restored.profile.game, "PXG")
                self.assertEqual(restored.settings.wheel_debounce_ms, 123)
                self.assertEqual(restored.settings.chat_key, "")
                restored.set_active_profile("Meu PKA")
                self.assertEqual(restored.settings.wheel_debounce_ms, 777)
                self.assertEqual(restored.profile.macros[0].steps[0].key, "y")
                copy = restored.profiles.duplicate("PXG", "Outro PXG")
                self.assertEqual(copy.game, "PXG")
                self.assertEqual(Profile.from_dict(copy.to_dict()).game, "PXG")

                from app.gui.main_window import MainWindow
                window = MainWindow(restored)
                window.withdraw()
                try:
                    window._refresh()
                    self.assertEqual(window.game_menu.get(), "PKA")
                    self.assertEqual(list(window.profile_menu.cget("values")), ["Meu PKA"])
                    window._on_game_selected("PXG")
                    window._refresh()
                    self.assertEqual(restored.profile.game, "PXG")
                    self.assertNotIn("Meu PKA", window.profile_menu.cget("values"))
                    for name in window.page_titles:
                        window.show_page(name)
                        window.update_idletasks()
                    window._on_game_selected("PKA")
                    self.assertEqual(restored.settings.wheel_debounce_ms, 777)
                finally:
                    window.destroy()


if __name__ == "__main__":
    unittest.main()
