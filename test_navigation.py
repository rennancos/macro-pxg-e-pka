"""Exercita navegacao real com configuracao temporaria, sem registrar hotkeys."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.gui.main_window import MainWindow
from app.services.controller import AppController
from app.models.profile import Macro, MacroStep


class NavigationTest(unittest.TestCase):
    def test_rotation_macro_can_be_selected_and_synced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = root / "profiles"
            profiles.mkdir()
            with (
                patch("app.services.profile_manager.PROFILES_DIR", profiles),
                patch("app.services.profile_manager.ensure_dirs"),
                patch("app.services.settings_manager.SETTINGS_FILE", root / "settings.json"),
                patch("app.services.settings_manager.ensure_dirs"),
                patch.object(AppController, "setup_emergency", return_value=True),
            ):
                controller = AppController()
                controller.set_active_profile("PXG")
                controller.profile.rotation_enabled = True
                controller.profile.macros = [
                    Macro(name="ataques", hotkey="wheel_up", steps=[MacroStep(type="key", key="1")]),
                    Macro(name="revive", hotkey="wheel_down", rotation=True,
                          steps=[MacroStep(type="key", key="q", delay_ms=300)]),
                ]
                window = MainWindow(controller)
                try:
                    window.show_page("Combo")
                    combo = window.pages["Combo"]
                    combo._select(1)
                    window.update()
                    self.assertTrue(combo.rotation_panel.winfo_ismapped())
                    combo.rotation_slot.set("3")
                    combo._sync_rotation_slot()
                    self.assertEqual(controller.active_pokemon_slot, 3)
                finally:
                    window.destroy()

    def test_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = root / "profiles"
            profiles.mkdir()
            with (
                patch("app.services.profile_manager.PROFILES_DIR", profiles),
                patch("app.services.profile_manager.ensure_dirs"),
                patch("app.services.settings_manager.SETTINGS_FILE", root / "settings.json"),
                patch("app.services.settings_manager.ensure_dirs"),
                patch.object(AppController, "setup_emergency", return_value=True),
            ):
                controller = AppController()
                started = time.perf_counter()
                window = MainWindow(controller)
                window.update()
                print(f"Initial window: {(time.perf_counter() - started) * 1000:.0f} ms")
                try:
                    for cycle in range(2):
                        for name in window.page_titles:
                            started = time.perf_counter()
                            window.show_page(name)
                            window.update()
                            elapsed = (time.perf_counter() - started) * 1000
                            mapped = [title for title, page in window.pages.items() if page.winfo_ismapped()]
                            print(f"Cycle {cycle} {name}: {elapsed:.0f} ms; mapped={mapped}")
                            self.assertEqual(mapped, [name])
                    window.show_page("Combo")
                    combo = window.pages["Combo"]
                    combo.name_entry.delete(0, "end")
                    combo.name_entry.insert(0, "Rascunho")
                    delay = combo._step_widgets[0]["delay"]
                    delay.delete(0, "end")
                    delay.insert(0, "9999")
                    window.show_page("Skills")
                    skills = window.pages["Skills"]
                    skills.name_entry.delete(0, "end")
                    skills.name_entry.insert(0, "Skill editada")
                    window.show_page("Combo")
                    self.assertEqual(combo.name_entry.get(), "Rascunho")
                    self.assertIs(combo._step_widgets[0]["delay"], delay)
                    self.assertEqual(delay.get(), "9999")
                    window.show_page("Skills")
                    self.assertEqual(skills.name_entry.get(), "Skill editada")
                    skills.table.selection_set("1")
                    skills._select()
                    skills.table.selection_set("0")
                    skills._select()
                    self.assertEqual(skills.name_entry.get(), "Skill editada")
                    skills.save()
                    self.assertEqual(controller.profile.skills[0].name, "Skill editada")
                    combo.discard()
                    self.assertNotEqual(combo.name_entry.get(), "Rascunho")
                    self.assertNotEqual(combo._step_widgets[0]["delay"].get(), "9999")
                    window._on_game_selected("PXG")
                    self.assertEqual(skills.key.get_value(), "")
                    window.show_page("Combo")
                    self.assertEqual(combo._current.steps, [])
                    window.geometry("900x600")
                    window.update()
                    self.assertEqual([p for p in window.pages.values() if p.winfo_ismapped()], [combo])
                finally:
                    window.destroy()


if __name__ == "__main__":
    unittest.main()
