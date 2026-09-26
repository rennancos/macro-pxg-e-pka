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

    def test_revive_without_sync_starts_at_first_slot(self):
        self.assertTrue(self.controller._rotate_pokemon())
        self.assertEqual(self.controller.combo.actions[0].key, "ctrl+1")

    def test_revive_clicks_fainted_portrait_and_returns_pointer(self):
        """Puxa, aponta o retrato com a barra de vida vazia, revive, devolve."""
        from unittest import mock
        from app.services import controller as ctl

        self.controller._make_pokemon_slot_handler(6)()
        self.assertTrue(self.controller._rotate_pokemon())
        acoes = self.controller.combo.actions
        self.assertEqual(
            [a.kind for a in acoes], ["key", "click", "key", "pointer_home"]
        )
        self.assertEqual(acoes[0].key, "ctrl+1")
        self.assertEqual(acoes[0].delay_ms, 300)
        self.assertEqual(acoes[2].key, "q")
        self.assertFalse(acoes[1].restore)
        # O alvo so e lido na hora do clique: o 3o retrato pequeno esta vazio.
        with mock.patch.object(ctl, "find_fainted", lambda retratos: 2):
            self.assertEqual(acoes[1].target(), (1030, 560))  # origem (1000, 500)
        with mock.patch.object(ctl, "find_fainted", lambda retratos: None):
            self.assertIsNone(acoes[1].target())

    def test_pull_is_tracked_and_cancel_keeps_previous_slot(self):
        self.controller._make_pokemon_slot_handler(4)()
        self.controller._rotate_pokemon()
        actions = self.controller.combo.actions
        self.assertEqual(self.controller.combo.name, ROTATION_NAME)
        self.assertEqual(actions[0].key, "ctrl+5")
        self.controller._on_macro_step(f"{actions[0].label} (1/4)")
        self.assertEqual(self.controller._active_pokemon_slot, 5)
        self.controller._on_macro_finish(f"{ROTATION_NAME} concluida")
        self.assertEqual(self.controller._active_pokemon_slot, 5)

        self.controller.combo.running = False
        self.controller._make_pokemon_slot_handler(6)()
        self.controller._rotate_pokemon()
        self.assertEqual(self.controller.combo.actions[0].key, "ctrl+1")
        self.controller._on_macro_finish(f"{ROTATION_NAME} cancelada")
        self.assertEqual(self.controller._active_pokemon_slot, 6)

    def test_runs_without_recorded_team_positions(self):
        """Sem posicoes gravadas: so teclas, sem clique no escuro."""
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
        # O slot acompanhado avanca quando a tecla sai, senao a proxima troca repete.
        acao = self.controller.combo.actions[0]
        self.controller._on_macro_step(f"{acao.label} (1/1)")
        self.controller._on_macro_finish(f"{SWITCH_NAME} concluida")
        self.assertEqual(self.controller._active_pokemon_slot, 3)

    def test_switch_cycles_only_listed_slots(self):
        """Cada giro envia o proximo Ctrl+n da lista; o que nao esta e pulado."""
        self.profile.macros.append(Macro(
            name="trocar", hotkey="wheel_down", switch=True,
            steps=[MacroStep(type="key", key=f"ctrl+{n}") for n in (1, 2, 4)],
        ))
        enviados = []
        for inicio in (1, 2, 4, 6):
            self.controller.combo.running = False
            self.controller._make_pokemon_slot_handler(inicio)()
            self.controller._switch_pokemon()
            enviados.append(self.controller.combo.actions[0].key)
        # 6 nao esta na lista: volta ao primeiro.
        self.assertEqual(enviados, ["ctrl+2", "ctrl+4", "ctrl+1", "ctrl+1"])

    def test_switch_without_sync_calls_first_slot(self):
        self.profile.macros.append(Macro(
            name="trocar", hotkey="wheel_up", switch=True,
            steps=[MacroStep(type="key", key="ctrl+1")],
        ))
        self.assertTrue(self.controller._switch_pokemon())
        self.assertEqual(self.controller.combo.actions[0].key, "ctrl+1")

    def test_switch_tracks_ctrl_n_without_rotation(self):
        self.profile.rotation_enabled = False
        self.profile.macros = [Macro(
            name="trocar", hotkey="wheel_down", switch=True,
            steps=[MacroStep(type="key", key="ctrl+1")],
        )]
        labels = [b.label for b in self.controller.build_bindings()]
        self.assertIn("Acompanhar Pokémon 1", labels)

    def test_refused_concurrent_start_keeps_winner_target(self):
        self.controller._make_pokemon_slot_handler(2)()
        self.assertTrue(self.controller._rotate_pokemon())
        self.controller.combo.running = False  # a checagem passou antes do inicio
        self.controller.combo.start = lambda actions, name: False
        self.assertFalse(self.controller._switch_pokemon())
        self.assertEqual(self.controller._rotation_target, 3)

    def test_manual_pick_during_rotation_survives_finish(self):
        self.controller._make_pokemon_slot_handler(2)()
        self.controller._rotate_pokemon()
        acao = self.controller.combo.actions[0]
        self.controller._on_macro_step(f"{acao.label} (1/2)")
        self.controller._make_pokemon_slot_handler(5)()
        self.controller._on_macro_finish(f"{ROTATION_NAME} concluida")
        self.assertEqual(self.controller._active_pokemon_slot, 5)

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


class ComboKeyTests(unittest.TestCase):
    def test_modifier_goes_down_first_and_up_last(self):
        from unittest import mock
        from app.services import action_executor as ae

        eventos = []
        teclado = SimpleNamespace(
            press=lambda k: eventos.append(("down", k)),
            release=lambda k: eventos.append(("up", k)),
        )
        with mock.patch.object(ae, "keyboard_module", lambda: teclado), \
                mock.patch.object(ae.time, "sleep", lambda s: eventos.append(("wait", s))):
            executor = ae.ActionExecutor(settings=None)
            self.assertTrue(executor.tap("ctrl+1", 30))
            self.assertTrue(executor.tap("q", 30))
        folga = ae.MODIFIER_LEAD_MS / 1000.0
        self.assertEqual(eventos, [
            ("down", "ctrl"), ("wait", folga), ("down", "1"), ("wait", 0.03),
            ("up", "1"), ("wait", folga), ("up", "ctrl"),
            ("down", "q"), ("wait", 0.03), ("up", "q"),
        ])


    def test_failed_release_never_leaves_ctrl_stuck(self):
        from unittest import mock
        from app.services import action_executor as ae

        soltas = []

        def press(k):
            if k == "1":
                raise OSError("falhou")

        def release(k):
            soltas.append(k)
            if k == "1":
                raise OSError("falhou de novo")

        teclado = SimpleNamespace(press=press, release=release)
        with mock.patch.object(ae, "keyboard_module", lambda: teclado),                 mock.patch.object(ae.time, "sleep", lambda s: None):
            self.assertFalse(ae.ActionExecutor(settings=None).tap("ctrl+1", 30))
        self.assertEqual(soltas, ["1", "ctrl"])

    def test_pointer_returns_even_when_revive_key_fails(self):
        from app.services.combo_manager import ComboManager, MacroAction

        class Executor:
            pos, pendente = (800, 900), None

            def click(self, x, y, restore):
                self.pendente, self.pos = self.pos, (x, y)
                return True

            def tap(self, key, hold_ms):
                return key != "q"  # o revive falha

            def restore_pointer(self):
                if self.pendente:
                    self.pos, self.pendente = self.pendente, None
                return True

        executor, fim = Executor(), threading.Event()
        combo = ComboManager(executor, on_finish=lambda status: fim.set())
        combo.start([
            MacroAction("puxar", "key", key="ctrl+1"),
            MacroAction("apontar", "click", x=1048, y=563, restore=False),
            MacroAction("revive", "key", key="q"),
            MacroAction("voltar", "pointer_home"),
        ], "t")
        self.assertTrue(fim.wait(2))
        self.assertEqual(executor.pos, (800, 900))


class TeamBarTests(unittest.TestCase):
    """Deteccao do desmaiado pela barra de vida, com pixels sinteticos."""

    VERDE, AZUL, FUNDO = (45, 81, 48), (129, 88, 39), (19, 19, 18)  # BGR

    def grab_com(self, vazios):
        from app.services import team_bar as tb

        def grab(x, y, w, h):
            retrato = (x - tb.HP_DX, y - tb.HP_DY)
            cor = self.FUNDO if retrato in vazios else self.VERDE
            linhas = [bytes(cor + (255,)) * w if i in (8, 9) else
                      bytes((self.AZUL if i in (17, 18) else self.FUNDO) + (255,)) * w
                      for i in range(h)]
            return b"".join(linhas)
        return grab

    def test_finds_only_the_empty_bar(self):
        from app.services.team_bar import find_fainted
        retratos = [(29, 133), (24, 177), (28, 220), (31, 269), (26, 316)]
        self.assertIsNone(find_fainted(retratos, self.grab_com(set())))
        for i, r in enumerate(retratos):
            self.assertEqual(find_fainted(retratos, self.grab_com({r})), i)
        # Tudo escuro (janela coberta): nao arrisca clique.
        self.assertIsNone(find_fainted(retratos, self.grab_com(set(retratos))))

if __name__ == "__main__":
    unittest.main()
