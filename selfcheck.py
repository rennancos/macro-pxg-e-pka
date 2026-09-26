"""Checagem rapida da logica que nao depende de GUI nem de teclado.

Rode com:  python selfcheck.py
Nao envia nenhuma tecla; usa um executor falso.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from pathlib import Path

from app.constants import (
    SKILL_COUNT,
    STEP_COMMAND,
    STEP_KEY,
    STEP_SKILL,
    WHEEL_DOWN,
    WHEEL_UP,
)
from app.models.profile import Profile, default_profile
from app.models.settings import Settings
from app.services.combo_manager import ComboManager, MacroAction
from app.services.hotkey_manager import normalize
from app.services.wheel_manager import WheelManager
from app.utils.jsonio import read_json, write_json


class FakeExecutor:
    """Substitui o ActionExecutor: registra o que seria enviado."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self._lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def tap(self, key: str, hold_ms: int) -> bool:
        with self._lock:
            self.sent.append(key)
        return True

    def restore_pointer(self) -> bool:
        return True

    def send_command(self, command: str) -> bool:
        with self._lock:
            self.sent.append(f"chat:{command}")
        return True


def skill_step(number: int, delay_ms: int) -> MacroAction:
    return MacroAction(
        label=f"Skill {number}",
        kind=STEP_KEY,
        key=str(number),
        hold_ms=0,
        delay_ms=delay_ms,
    )


def test_profile_roundtrip() -> None:
    profile = default_profile("Charizard")
    restored = Profile.from_dict(json.loads(json.dumps(profile.to_dict())))
    assert restored.to_dict() == profile.to_dict()
    assert restored.name == "Charizard"
    assert len(restored.skills) == SKILL_COUNT


def test_invalid_values_are_sanitized() -> None:
    profile = Profile.from_dict(
        {
            "name": "  ",
            "skills": "nao e uma lista",
            "revive": {"mode": "telepatia", "hold_ms": -500},
            "macros": [{"name": "M", "steps": [{"skill": 99, "delay_ms": -10}, "lixo"]}],
        }
    )
    assert len(profile.skills) == SKILL_COUNT, "skills invalidas viram os padroes"
    assert profile.revive.mode == "key", "modo desconhecido cai no padrao"
    assert profile.revive.hold_ms == 0, "delay negativo e zerado"
    steps = profile.macros[0].steps
    assert steps[0].skill == SKILL_COUNT, "skill fora do intervalo e limitada"
    assert steps[0].delay_ms == 0, "delay negativo e zerado"
    assert steps[1].skill == 1, "etapa invalida vira uma etapa padrao"


def test_legacy_combo_is_migrated() -> None:
    """Perfis salvos no formato antigo (combo unico) continuam abrindo."""
    profile = Profile.from_dict(
        {
            "name": "Antigo",
            "combo": {
                "hotkey": "f8",
                "cancel_hotkey": "esc",
                "steps": [{"skill": 1, "delay_ms": 150}, {"skill": 2, "delay_ms": 0}],
            },
        }
    )
    assert len(profile.macros) == 1
    macro = profile.macros[0]
    assert macro.hotkey == "f8"
    assert [s.skill for s in macro.steps] == [1, 2]
    assert all(s.type == STEP_SKILL for s in macro.steps)


def test_default_profile_has_wheel_macros() -> None:
    profile = default_profile("Charizard")
    assert len(profile.skills) == 12, "o cliente expoe 12 slots de acao"
    triggers = {macro.hotkey for macro in profile.macros}
    assert WHEEL_UP in triggers and WHEEL_DOWN in triggers

    ofensiva = next(m for m in profile.macros if m.hotkey == WHEEL_UP)
    assert [s.key for s in ofensiva.steps] == ["r", "t"], "R=!offensive, T=!autocombo"

    defensiva = next(m for m in profile.macros if m.hotkey == WHEEL_DOWN)
    assert [s.key for s in defensiva.steps] == ["q", "e"], "Q=revive, E=!defensive"

    # O jogo ja tem esses comandos na barra de acao: o app aperta a tecla e
    # nunca digita no chat. Isso evita o foco do chat vazar para a etapa
    # seguinte, que fazia a tecla do revive virar a letra "q" numa mensagem.
    todas = [s for m in profile.macros for s in m.steps]
    assert all(s.type == STEP_KEY for s in todas), "nenhuma etapa deve usar o chat"
    assert profile.offensive.mode == "key" and profile.offensive.key == "r"
    assert profile.defensive.mode == "key" and profile.defensive.key == "e"
    assert profile.revive.mode == "key" and profile.revive.key == "q"


def test_macro_roundtrip_keeps_mixed_steps() -> None:
    profile = default_profile("Teste")
    restored = Profile.from_dict(json.loads(json.dumps(profile.to_dict())))
    assert restored.to_dict() == profile.to_dict()


def test_corrupted_json_is_quarantined() -> None:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "broken.json"
        path.write_text("{ isso nao e json", encoding="utf-8")
        assert read_json(path) is None
        assert path.with_suffix(".json.bak").exists(), "arquivo quebrado vai para .bak"

        good = Path(folder) / "ok.json"
        assert write_json(good, {"a": 1})
        assert read_json(good) == {"a": 1}
        assert not list(Path(folder).glob("*.tmp")), "escrita atomica nao deixa lixo"


def test_settings_defaults() -> None:
    settings = Settings.from_dict({"type_delay_ms": "abc", "appearance": "roxo"})
    assert settings.type_delay_ms > 0
    assert settings.appearance == "dark"
    assert Settings.from_dict(None).emergency_hotkey == "pause", "F12 e a move 12"
    assert Settings.from_dict(None).require_game_focus is True
    assert Settings.from_dict({"wheel_debounce_ms": -5}).wheel_debounce_ms == 0


def test_hotkey_normalization() -> None:
    assert normalize("") is None
    assert normalize("  F1 ") == normalize("f1")
    assert normalize("f1") != normalize("f2")


def test_combo_runs_in_order() -> None:
    executor = FakeExecutor()
    combo = ComboManager(executor)
    actions = [skill_step(i, 10) for i in range(1, 5)]
    assert combo.start(actions)
    assert not combo.start(actions), "nao pode haver dois combos simultaneos"
    combo.wait(5)
    assert executor.sent == ["1", "2", "3", "4"], executor.sent


def test_combo_cancel_is_immediate() -> None:
    executor = FakeExecutor()
    combo = ComboManager(executor)
    actions = [skill_step(i, 3000) for i in range(1, 5)]
    started = time.monotonic()
    assert combo.start(actions)
    time.sleep(0.1)
    assert combo.cancel()
    combo.wait(5)
    elapsed = time.monotonic() - started
    assert elapsed < 1.5, f"cancelamento demorou {elapsed:.2f}s"
    assert executor.sent == ["1"], executor.sent
    assert not combo.running


def test_empty_combo_is_rejected() -> None:
    assert not ComboManager(FakeExecutor()).start([])


def test_command_closes_chat_afterwards() -> None:
    """Depois de enviar, o chat volta ao estado travado.

    Sem isso, a etapa seguinte da macro digita dentro do chat: a tecla `q` do
    revive vira a letra "q" e o Enter seguinte publica isso como mensagem.
    """
    from app.services import action_executor as mod

    enviados: list[str] = []

    class TecladoFalso:
        def send(self, key): enviados.append(f"send:{key}")
        def write(self, text, delay=0): enviados.append(f"write:{text}")
        def press(self, key): enviados.append(f"press:{key}")
        def release(self, key): enviados.append(f"release:{key}")

    original = mod.keyboard_module
    mod.keyboard_module = lambda: TecladoFalso()
    try:
        settings = Settings.from_dict(
            {"chat_open_pause_ms": 0, "chat_send_pause_ms": 0, "chat_close_pause_ms": 0}
        )
        executor = mod.ActionExecutor(settings)
        assert executor.send_command("!offensive")
    finally:
        mod.keyboard_module = original

    assert enviados == [
        "send:enter",
        "write:!offensive",
        "send:enter",
        "send:ctrl+e",
    ], enviados
    assert enviados[-1] == "send:ctrl+e", "o chat precisa ser fechado no fim"


def test_chat_close_key_must_not_be_the_cancel_key() -> None:
    """Se fechar o chat usasse a tecla de cancelar, a macro se cancelaria."""
    from app.models.settings import Settings as S

    padrao = S.from_dict(None)
    assert padrao.chat_close_key != padrao.cancel_hotkey
    assert padrao.chat_close_key != padrao.emergency_hotkey


def test_window_detection_survives_elevated_game() -> None:
    """Se o jogo roda elevado, OpenProcess falha e so resta a classe da janela."""
    from app.services.window_manager import WindowManager

    w = WindowManager()

    # Caso normal: o app enxerga o executavel.
    assert w.decide(r"X:\PokeAlliance\PokeAlliance_dx.exe", "PokeAllianceV3")
    assert w.decide(r"X:\PokeAlliance\PokeAlliance_gl.exe", "PokeAllianceV3")
    assert not w.decide(r"X:\PokeAlliance\PokeAlliance_Launcher.exe", "wailsWindow")
    assert not w.decide(r"C:\Windows\explorer.exe", "CabinetWClass")

    # Jogo elevado + app comum: caminho vazio, decide pela classe.
    assert w.decide("", "PokeAllianceV3"), "fallback por classe falhou"
    assert w.decide("", "pokealliancev3"), "a comparacao deve ignorar caixa"
    assert not w.decide("", "Chrome_WidgetWin_1")
    assert not w.decide("", ""), "sem dado nenhum nao e o jogo"


def test_macro_mixes_keys_and_commands() -> None:
    executor = FakeExecutor()
    combo = ComboManager(executor)
    actions = [
        MacroAction(label="!offensive", kind=STEP_COMMAND, command="!offensive", delay_ms=10),
        MacroAction(label="tecla q", kind=STEP_KEY, key="q", delay_ms=0),
    ]
    assert combo.start(actions, "Ofensiva")
    combo.wait(5)
    assert executor.sent == ["chat:!offensive", "q"], executor.sent


def test_wheel_debounce_swallows_the_same_flick() -> None:
    """Um giro da roda gera varios eventos; so o primeiro pode disparar."""
    import mouse

    disparos: list[str] = []
    wheel = WheelManager(lambda: 400)
    wheel._callbacks = {
        WHEEL_UP: lambda: disparos.append("cima"),
        WHEEL_DOWN: lambda: disparos.append("baixo"),
    }

    for _ in range(5):  # um giro fisico para cima
        wheel._on_event(mouse.WheelEvent(delta=1, time=0))
    assert disparos == ["cima"], f"debounce falhou: {disparos}"

    for _ in range(5):  # giro para baixo: direcao diferente, dispara
        wheel._on_event(mouse.WheelEvent(delta=-1, time=0))
    assert disparos == ["cima", "baixo"], disparos

    wheel._on_event(mouse.ButtonEvent(event_type="down", button="left", time=0))
    assert disparos == ["cima", "baixo"], "clique nao e roda"


def test_botoes_laterais_do_mouse_disparam() -> None:
    """Botao do meio, X1 e X2 sao gatilhos; esquerdo e direito nunca sao."""
    import mouse
    from app.constants import MOUSE_MIDDLE, MOUSE_X1, MOUSE_X2

    disparos: list[str] = []
    wheel = WheelManager(lambda: 0)
    wheel._callbacks = {
        MOUSE_MIDDLE: lambda: disparos.append("meio"),
        MOUSE_X1: lambda: disparos.append("x1"),
        MOUSE_X2: lambda: disparos.append("x2"),
    }

    def click(button: str, event_type: str = "down") -> None:
        wheel._on_event(mouse.ButtonEvent(event_type=event_type, button=button, time=0))

    click("middle"); click("x"); click("x2")
    assert disparos == ["meio", "x1", "x2"], disparos

    # A subida do clique nao pode disparar de novo.
    click("x", "up")
    assert disparos == ["meio", "x1", "x2"], disparos

    # A lib renomeia o segundo clique rapido para "double": tem de valer.
    click("x", "double")
    assert disparos == ["meio", "x1", "x2", "x1"], disparos

    # Esquerdo e direito ficam de fora de proposito.
    click("left"); click("right")
    assert disparos == ["meio", "x1", "x2", "x1"], disparos


def test_ponteiro_so_volta_depois_da_tecla() -> None:
    """O revive age sob o cursor: devolver o ponteiro antes zera o efeito."""
    from unittest.mock import patch
    from app.models.settings import Settings
    from app.services.action_executor import ActionExecutor

    eventos: list[tuple] = []

    class FakeMouse:
        @staticmethod
        def get_position():
            return (900, 700)

        @staticmethod
        def move(x, y):
            eventos.append(("move", x, y))

        @staticmethod
        def click():
            eventos.append(("click",))

    executor = ActionExecutor(Settings())
    with patch("app.services.action_executor.mouse_module", lambda: FakeMouse):
        assert executor.click(30, 290, restore=False)
        assert eventos == [("move", 30, 290), ("click",)], eventos

        # A tecla do revive acontece aqui, com o cursor ainda no retrato.
        assert executor.restore_pointer()
        assert eventos[-1] == ("move", 900, 700), eventos

        # Chamar de novo nao mexe o mouse: nao ha para onde voltar.
        antes = len(eventos)
        assert executor.restore_pointer()
        assert len(eventos) == antes

        # Com restore=True o ponteiro volta sozinho, sem etapa extra.
        eventos.clear()
        assert executor.click(10, 20)
        assert eventos == [("move", 10, 20), ("click",), ("move", 900, 700)], eventos


def test_gatilho_de_rotacao_invalido_volta_ao_padrao() -> None:
    from app.constants import MOUSE_X1, WHEEL_DOWN
    from app.models.profile import Profile

    assert Profile.from_dict({"name": "a"}).rotation_trigger == WHEEL_DOWN
    assert Profile.from_dict({"name": "a", "rotation_trigger": "lixo"}).rotation_trigger == WHEEL_DOWN
    perfil = Profile.from_dict({"name": "a", "rotation_trigger": MOUSE_X1})
    assert perfil.rotation_trigger == MOUSE_X1
    assert Profile.from_dict(perfil.to_dict()).rotation_trigger == MOUSE_X1


def test_wheel_debounce_zero_allows_every_event() -> None:
    import mouse

    disparos: list[int] = []
    wheel = WheelManager(lambda: 0)
    wheel._callbacks = {WHEEL_UP: lambda: disparos.append(1)}
    for _ in range(3):
        wheel._on_event(mouse.WheelEvent(delta=1, time=0))
    assert len(disparos) == 3, disparos


def test_virtual_screen_cobre_segundo_monitor() -> None:
    """A area valida precisa abranger todos os monitores, nao so o primario."""
    from app.gui.main_window import _virtual_screen

    left, top, right, bottom = _virtual_screen()
    assert right > left and bottom > top, (left, top, right, bottom)


def test_hotkey_igual_a_tecla_enviada_e_recusada() -> None:
    """Skill com hotkey == key trava o golpe: tem de ser recusada."""
    from app.models.profile import Profile
    from app.services.controller import _is_self_trigger, _macro_keys

    assert _is_self_trigger("1", ["1"])
    assert not _is_self_trigger("ctrl+alt+2", ["2"])
    assert not _is_self_trigger("", ["1"])
    assert not _is_self_trigger("wheel_up", ["1"])

    profile = Profile.from_dict({
        "name": "t",
        "skills": [{"name": "Ataque 1", "key": "1", "hotkey": "1"}],
        "macros": [{
            "name": "m",
            "hotkey": "x",
            "enabled": True,
            "steps": [{"type": "key", "key": "x"}],
        }],
    })
    assert _macro_keys(profile, profile.macros[0]) == ["x"]
    assert _is_self_trigger(profile.macros[0].hotkey,
                            _macro_keys(profile, profile.macros[0]))


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"FALHOU  {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"ERRO    {test.__name__}: {exc!r}")
        else:
            print(f"ok      {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} checagens passaram")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
