"""Rotação PXG sem hooks ou envio real de teclas."""

import threading
import unittest
from types import SimpleNamespace

from app.models.profile import Macro, MacroStep, Profile
from app.services.controller import AppController, ROTATION_NAME, SWITCH_NAME


class FakeCombo:
    running = False

    def __init__(self):
        self.actions = []
        self.name = ""

    def start(self, actions, name):
        self.actions = actions
        self.name = name
        self.running = True
        return True


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(name="PXG", game="PXG", rotation_enabled=True)
        self.profile.revive.key = "q"
        self.profile.rotation_delay_ms = 300
        self.profile.macros = [Macro(
            name="revive", hotkey="mouse_x1", rotation=True,
            steps=[MacroStep(type="key", key="q", delay_ms=300)],
        )]
        self.controller = AppController.__new__(AppController)
        self.gravacoes = []
        self.controller.profiles = SimpleNamespace(
            active=self.profile,
            save=lambda name="": self.gravacoes.append(name) or True,
        )
        self.controller.settings = SimpleNamespace(
            require_game_focus=True, suppress_hotkeys=True, cancel_hotkey="esc"
        )
        # (1000, 500) e o canto da area util do jogo na tela; as posicoes
        # gravadas no perfil sao relativas a ele.
        self.controller.windows = SimpleNamespace(
            is_game_focused=lambda: True,
            game_client_origin=lambda: (1000, 500),
            invalidate=lambda: None,
        )
        self.profile.team_slots = [(10 * n, 20 * n) for n in range(1, 7)]
        self.controller.combo = FakeCombo()
        self.controller._enabled = True
        self.controller._suspended = False
        self.controller._state_lock = threading.Lock()
        self.controller._active_pokemon_slot = None
        self.controller._rotation_target = None
        self.controller._set_last_action = lambda text: None

    def test_requires_manual_sync_and_revives_after_switch(self):
        self.controller._rotate_pokemon()
        self.assertEqual(self.controller.combo.actions, [])

        self.controller._make_pokemon_slot_handler(4)()
        self.controller._rotate_pokemon()
        actions = self.controller.combo.actions
        self.assertEqual(self.controller.combo.name, ROTATION_NAME)
        # Puxa o proximo e revive ESSE mesmo: duas teclas, sem clique.
        self.assertEqual([action.key for action in actions], ["ctrl+5", "q"])
        self.assertEqual(actions[0].delay_ms, 300)
        self.assertEqual(actions[1].label, "Revive Pokémon 5")
        self.controller._on_macro_step(f"{actions[0].label} (1/2)")
        self.assertEqual(self.controller._active_pokemon_slot, 5)
        self.controller._on_macro_finish(f"{ROTATION_NAME} concluida")
        self.assertEqual(self.controller._active_pokemon_slot, 5)

    def test_wraps_six_to_one_and_cancel_keeps_previous_slot(self):
        self.controller._make_pokemon_slot_handler(6)()
        self.controller._rotate_pokemon()
        self.assertEqual(
            [action.key for action in self.controller.combo.actions],
            ["ctrl+1", "q"],
        )
        self.controller._on_macro_finish(f"{ROTATION_NAME} cancelada")
        self.assertEqual(self.controller._active_pokemon_slot, 6)

    def test_runs_without_recorded_team_positions(self):
        """Puxar + reviver nao depende de clique, logo nao depende das posicoes."""
        self.profile.team_slots = [None] * 6
        self.controller._make_pokemon_slot_handler(4)()
        self.assertTrue(self.controller._rotate_pokemon())
        self.assertEqual(
            [action.key for action in self.controller.combo.actions],
            ["ctrl+5", "q"],
        )

    def test_capture_stores_position_relative_to_game_window(self):
        """Mover a janela do jogo nao pode invalidar a posicao gravada."""
        self.controller._notify = lambda: None
        self.controller.refresh_bindings = lambda: None
        self.assertTrue(self.controller.capture_team_slot(2, 1234, 640))
        self.assertEqual(self.profile.team_slots[1], (234, 140))
        # Gravada em disco na hora, senao some ao fechar o app.
        self.assertEqual(len(self.gravacoes), 1)

        # Mesma posicao relativa, janela deslocada -> outro ponto na tela.
        self.controller.windows.game_client_origin = lambda: (1100, 700)
        self.assertEqual(self.controller._team_slot_on_screen(2), (1334, 840))

    def test_capture_waits_for_the_game_to_take_focus(self):
        """O hook dispara antes de o Windows ativar a janela clicada.

        No instante do clique a janela em foco ainda e a do proprio app, entao
        a origem so aparece depois de algumas tentativas. Desistir na primeira
        era o que fazia toda gravacao falhar.
        """
        self.controller._notify = lambda: None
        self.controller.refresh_bindings = lambda: None
        tentativas = []

        def origem_atrasada():
            tentativas.append(1)
            return (1000, 500) if len(tentativas) >= 4 else None

        self.controller.windows.game_client_origin = origem_atrasada
        self.assertTrue(self.controller.capture_team_slot(3, 1050, 560))
        self.assertEqual(self.profile.team_slots[2], (50, 60))
        self.assertGreaterEqual(len(tentativas), 4)

    def test_capture_gives_up_when_the_game_never_focuses(self):
        """Clique fora do jogo nao pode gravar uma posicao sem sentido."""
        self.controller._notify = lambda: None
        self.controller.windows.game_client_origin = lambda: None
        self.assertIsNone(self.controller._wait_for_game_origin(timeout=0.1))

        # E a gravacao nao pode escrever nada quando a espera termina em nada.
        self.controller._wait_for_game_origin = lambda timeout=2.0: None
        antes = list(self.profile.team_slots)
        self.assertFalse(self.controller.capture_team_slot(1, 1234, 640))
        self.assertEqual(self.profile.team_slots, antes)

    def test_switch_macro_only_advances(self):
        """A macro de troca avanca o Pokemon e nao manda revive nenhum."""
        self.profile.macros.append(Macro(
            name="trocar", hotkey="wheel_down", switch=True,
            steps=[MacroStep(type="key", key="ctrl+1")],
        ))
        self.controller._make_pokemon_slot_handler(2)()
        self.assertTrue(self.controller._switch_pokemon())
        self.assertEqual(self.controller.combo.name, SWITCH_NAME)
        self.assertEqual(
            [action.key for action in self.controller.combo.actions], ["ctrl+3"]
        )
        # E o slot acompanhado avanca ao terminar, senao a proxima troca repete.
        self.controller._on_macro_finish(f"{SWITCH_NAME} concluida")
        self.assertEqual(self.controller._active_pokemon_slot, 3)

    def test_switch_macro_is_routed_by_its_own_trigger(self):
        self.profile.macros.append(Macro(
            name="trocar", hotkey="wheel_down", switch=True,
            steps=[MacroStep(type="key", key="ctrl+1")],
        ))
        ligacoes = self.controller.wheel_bindings()
        self.assertEqual(ligacoes["wheel_down"], self.controller._switch_pokemon)
        self.assertEqual(ligacoes["mouse_x1"], self.controller._rotate_pokemon)

    def test_profile_roundtrip_keeps_rotation(self):
        restored = Profile.from_dict(self.profile.to_dict())
        self.assertTrue(restored.rotation_enabled)
        self.assertEqual(restored.rotation_delay_ms, 300)
        self.assertTrue(restored.macros[0].rotation)
        self.assertEqual(restored.team_slots, self.profile.team_slots)

    def test_manual_switches_reach_game_and_wheel_down_rotates(self):
        bindings = self.controller.build_bindings()
        trackers = [binding for binding in bindings if binding.label.startswith("Acompanhar Pokémon")]
        self.assertEqual([binding.hotkey for binding in trackers], [f"ctrl+{n}" for n in range(1, 7)])
        self.assertTrue(all(not binding.suppress for binding in trackers))
        self.assertEqual(self.controller.wheel_bindings()["mouse_x1"], self.controller._rotate_pokemon)


if __name__ == "__main__":
    unittest.main()
