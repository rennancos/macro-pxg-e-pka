"""Controlador da aplicacao: une configuracao, gatilhos e execucao.

A GUI conversa somente com esta classe. Nenhuma pagina da interface conhece
a biblioteca de teclado, de mouse ou a API do Windows.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Iterable

from app.constants import (
    DEFAULT_HOLD_MS,
    MODE_DEFENSIVE,
    MODE_NONE,
    MODE_OFFENSIVE,
    STEP_COMMAND,
    STEP_KEY,
    STEP_SKILL,
    MOUSE_LABELS,
    MOUSE_TRIGGERS,
    WHEEL_DOWN,
)
from app.models.profile import ActionConfig, Macro, Profile
from app.models.settings import Settings
from app.services.action_executor import ActionExecutor
from app.services.combo_manager import ComboManager, MacroAction
from app.services.hotkey_manager import Binding, BindResult, HotkeyManager, normalize
from app.services.profile_manager import ProfileManager
from app.services.settings_manager import SettingsManager
from app.services.wheel_manager import WheelManager
from app.services.window_manager import WindowManager, CLIENT_EXECUTABLES, CLIENT_WINDOW_CLASSES

log = logging.getLogger(__name__)

Listener = Callable[[], None]
ROTATION_NAME = "Rotação Pokémon"
SWITCH_NAME = "Troca de Pokémon"
# Rotulo da etapa que troca de Pokemon. Constante porque o acompanhamento do
# slot casa por ele: quando o texto e o casamento moram em lugares diferentes,
# renomear um deixa o outro para tras em silencio.
PULL_STEP = "Puxar Pokémon"


def _is_self_trigger(hotkey: str, sent_keys: Iterable[str]) -> bool:
    """A hotkey e a propria tecla que a acao envia?

    Suprimir `1` e logo depois injetar `1` poe o app dentro do proprio hook:
    o jogo perde a tecla original e recebe uma rajada de repeticoes enquanto
    a tecla fica pressionada — o golpe trava. Sem o gatilho, o jogo recebe a
    tecla direto, que e exatamente o que o usuario queria.
    """
    trigger = normalize(hotkey)
    if trigger is None:
        return False
    return any(key and normalize(key) == trigger for key in sent_keys)


def _macro_keys(profile: Profile, macro: Macro) -> list[str]:
    """Teclas que a macro envia (etapas de comando nao enviam tecla)."""
    keys: list[str] = []
    for step in macro.steps:
        if step.type == STEP_SKILL:
            skill = profile.skill(step.skill)
            if skill is not None:
                keys.append(skill.key)
        elif step.type == STEP_KEY:
            keys.append(step.key)
    return keys

GAME_SETTINGS = (
    "emergency_hotkey", "cancel_hotkey", "wheel_debounce_ms", "require_game_focus",
    "chat_key", "chat_confirm_key", "chat_close_key", "chat_close_pause_ms",
    "type_delay_ms", "chat_open_pause_ms", "chat_send_pause_ms", "suppress_hotkeys",
    "autostart_hotkeys", "client_executable",
)


class AppController:
    def __init__(self) -> None:
        self._settings_manager = SettingsManager()
        self.settings: Settings = self._settings_manager.load()
        self.profiles = ProfileManager()
        self.profiles.load_all(self.settings.active_profile)
        self.settings.active_profile = self.profiles.active_name
        if not self.settings.game_settings:
            self._store_game_settings("PKA")
        self._load_game_settings(self.profile.game)

        self.executor = ActionExecutor(self.settings)
        self.combo = ComboManager(
            self.executor,
            on_step=self._on_macro_step,
            on_finish=self._on_macro_finish,
        )
        self.hotkeys = HotkeyManager()
        self.wheel = WheelManager(lambda: self.settings.wheel_debounce_ms)
        self.windows = WindowManager()
        self._configure_game_window()

        self._enabled = False
        self._suspended = False
        self._mode = MODE_NONE
        self._last_action = "---"
        self._skipped_bindings: list[str] = []
        self._listeners: list[Listener] = []
        self._state_lock = threading.Lock()
        self._active_pokemon_slot: int | None = None
        self._rotation_target: int | None = None

        log.info("Perfil %s carregado", self.profile.name)

    # ------------------------------------------------------------------ estado

    @property
    def profile(self) -> Profile:
        return self.profiles.active

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def suspended(self) -> bool:
        return self._suspended

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def last_action(self) -> str:
        return self._last_action

    @property
    def status_text(self) -> str:
        if self._enabled:
            return "PAUSADO (editando)" if self._suspended else "ATIVO"
        return "DESATIVADO"

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:  # noqa: BLE001 - GUI nunca derruba o controller
                log.exception("Falha ao atualizar a interface")

    def _set_last_action(self, text: str) -> None:
        self._last_action = text
        self._notify()

    # ------------------------------------------------------------- gatilhos

    def build_bindings(self) -> list[Binding]:
        """Hotkeys de teclado do perfil ativo (a roda vai em wheel_bindings)."""
        profile = self.profile
        suppress = self.settings.suppress_hotkeys
        bindings: list[Binding] = []
        skipped: list[str] = []
        self._skipped_bindings = skipped

        for index, skill in enumerate(profile.skills, start=1):
            if skill.enabled and skill.hotkey and skill.key:
                label = skill.name or f"Skill {index}"
                if _is_self_trigger(skill.hotkey, [skill.key]):
                    skipped.append(
                        f"{label}: {skill.hotkey} dispara a propria tecla "
                        "(o jogo ja recebe essa tecla direto)"
                    )
                    continue
                bindings.append(
                    Binding(
                        label=label,
                        hotkey=skill.hotkey,
                        callback=self._make_skill_handler(index),
                        suppress=suppress,
                    )
                )

        for action in (profile.revive, profile.offensive, profile.defensive):
            if action.enabled and action.hotkey and action.is_runnable():
                if _is_self_trigger(action.hotkey, [action.key]):
                    skipped.append(
                        f"{action.label}: {action.hotkey} dispara a propria tecla "
                        "(o jogo ja recebe essa tecla direto)"
                    )
                    continue
                bindings.append(
                    Binding(
                        label=action.label,
                        hotkey=action.hotkey,
                        callback=self._make_action_handler(action.label),
                        suppress=suppress,
                    )
                )

        for macro in profile.macros:
            if macro.enabled and macro.steps and self._is_keyboard_trigger(macro.hotkey):
                if _is_self_trigger(macro.hotkey, _macro_keys(profile, macro)):
                    skipped.append(
                        f"{macro.name}: {macro.hotkey} e uma das teclas que a "
                        "propria macro envia"
                    )
                    continue
                bindings.append(
                    Binding(
                        label=macro.name,
                        hotkey=macro.hotkey,
                        callback=self._macro_callback(macro),
                        suppress=suppress,
                    )
                )

        if profile.game == "PXG" and profile.rotation_enabled:
            for slot in range(1, 7):
                bindings.append(Binding(
                    label=f"Acompanhar Pokémon {slot}",
                    hotkey=f"ctrl+{slot}",
                    callback=self._make_pokemon_slot_handler(slot),
                    suppress=False,
                ))

        if self.settings.cancel_hotkey:
            # Cancelar nunca e suprimido: e tecla de seguranca e nao pode
            # deixar de chegar ao jogo (ESC, por exemplo).
            bindings.append(
                Binding(
                    label="Cancelar",
                    hotkey=self.settings.cancel_hotkey,
                    callback=self._on_cancel_hotkey,
                    suppress=False,
                )
            )
        return bindings

    def _macro_callback(self, macro: Macro) -> Callable[[], None]:
        """Escolhe o que a macro faz: revive, troca, ou a sequencia montada."""
        if macro.rotation:
            return self._rotate_pokemon
        if macro.switch:
            return self._switch_pokemon
        return self._make_macro_handler(macro.name)

    def wheel_bindings(self) -> dict[str, Callable[[], None]]:
        """Macros e rotacao presas a roda ou aos botoes do mouse."""
        result: dict[str, Callable[[], None]] = {}
        for macro in self.profile.macros:
            if macro.enabled and macro.steps and macro.hotkey in MOUSE_TRIGGERS:
                result.setdefault(macro.hotkey, self._macro_callback(macro))
        return result

    @property
    def active_pokemon_slot(self) -> int | None:
        with self._state_lock:
            return self._active_pokemon_slot

    def set_pokemon_slot(self, slot: int) -> None:
        """Sincroniza a rotação com uma troca manual ou pela interface."""
        if not 1 <= slot <= 6:
            raise ValueError("O slot do Pokémon deve estar entre 1 e 6")
        with self._state_lock:
            self._active_pokemon_slot = slot
        log.info("Pokémon ativo sincronizado: %d", slot)
        self._set_last_action(f"Pokémon {slot} ativo")

    def _make_pokemon_slot_handler(self, slot: int) -> Callable[[], None]:
        def handler() -> None:
            if not self._enabled or self._suspended:
                return
            if self.settings.require_game_focus and not self.windows.is_game_focused():
                return
            with self._state_lock:
                if self.combo.running and slot == self._rotation_target:
                    return  # Ctrl+n enviado pela própria rotação.
            self.set_pokemon_slot(slot)

        return handler

    def _switch_pokemon(self) -> bool:
        """Avanca para o proximo Pokemon, sem reviver nada.

        Mesma contagem da rotacao: o slot acompanhado vem do ultimo Ctrl+n
        visto (ou do botao Sincronizar), e o handler de Ctrl+n ignora a tecla
        que esta macro envia para nao contar duas vezes.
        """
        if not self._enabled or self._suspended or self.combo.running:
            return False
        if self.settings.require_game_focus and not self.windows.is_game_focused():
            return False
        with self._state_lock:
            current = self._active_pokemon_slot
        if current is None:
            log.warning("Troca ignorada: pressione Ctrl+1 a Ctrl+6 para sincronizar")
            self._set_last_action("Sincronize com Ctrl+1 a Ctrl+6")
            return False

        next_slot = current % 6 + 1
        actions = [MacroAction(
            label=f"{PULL_STEP} {next_slot}", kind=STEP_KEY,
            key=f"ctrl+{next_slot}", hold_ms=DEFAULT_HOLD_MS,
        )]
        with self._state_lock:
            self._rotation_target = next_slot
        if not self.combo.start(actions, SWITCH_NAME):
            with self._state_lock:
                self._rotation_target = None
            return False
        log.info("Troca iniciada: Ctrl+%d", next_slot)
        self._set_last_action(f"Pokémon {next_slot}")
        return True

    def _rotate_pokemon(self) -> bool:
        if not self._enabled or self._suspended or self.combo.running:
            return False
        if self.settings.require_game_focus and not self.windows.is_game_focused():
            return False
        macro = next((m for m in self.profile.macros if m.rotation and m.enabled), None)
        if macro is None or not macro.steps or macro.steps[0].type != STEP_KEY:
            log.warning("Rotação ignorada: macro de revive sem etapa de tecla")
            return False
        with self._state_lock:
            current = self._active_pokemon_slot
        if current is None:
            log.warning("Rotação ignorada: pressione Ctrl+1 a Ctrl+6 para sincronizar")
            self._set_last_action("Sincronize com Ctrl+1 a Ctrl+6")
            return False
        revive_step = macro.steps[0]
        if not revive_step.key:
            log.warning("Rotação ignorada: tecla do revive não configurada")
            return False
        # Puxa o Pokemon e revive ESSE mesmo. O revive age em quem acabou de
        # ser puxado, entao nao ha alvo a escolher: duas teclas resolvem.
        #
        # ponytail: o caminho "reviver o que SAIU" precisava clicar no retrato
        # dele na barra do time — o executor sabe clicar (click /
        # restore_pointer) e o perfil guarda as posicoes (team_slots), tudo
        # com teste. Esta desligado aqui, nao apagado: e para onde voltar
        # quando o rodizio entre os seis for retomado.
        next_slot = current % 6 + 1
        actions = [
            MacroAction(
                label=f"{PULL_STEP} {next_slot}", kind=STEP_KEY,
                key=f"ctrl+{next_slot}", hold_ms=DEFAULT_HOLD_MS,
                delay_ms=revive_step.delay_ms,
            ),
            MacroAction(
                label=f"Revive Pokémon {next_slot}", kind=STEP_KEY,
                key=revive_step.key, hold_ms=self.profile.revive.hold_ms,
            ),
        ]
        with self._state_lock:
            self._rotation_target = next_slot
        if not self.combo.start(actions, ROTATION_NAME):
            with self._state_lock:
                self._rotation_target = None
            return False
        log.info(
            "Rotação iniciada: puxar Pokémon %d (Ctrl+%d), depois revive nele",
            next_slot, next_slot,
        )
        self._set_last_action(f"Puxar {next_slot} → revive {next_slot}")
        return True

    def _team_slot_on_screen(self, slot: int) -> tuple[int, int] | None:
        """Posicao gravada do retrato, convertida para coordenadas de tela.

        O perfil guarda a posicao relativa ao canto da area util do jogo, para
        a janela poder ser movida. A conversao so e possivel com o jogo em
        primeiro plano — que e justamente quando a rotacao roda.
        """
        slots = self.profile.team_slots
        if not 1 <= slot <= len(slots):
            return None
        relative = slots[slot - 1]
        if relative is None:
            return None
        origin = self.windows.game_client_origin()
        if origin is None:
            log.warning("Não foi possível localizar a janela do jogo para clicar")
            return None
        return origin[0] + relative[0], origin[1] + relative[1]

    def _wait_for_game_origin(self, timeout: float = 2.0) -> tuple[int, int] | None:
        """Espera o jogo virar a janela ativa e devolve a origem da area util.

        O hook do mouse dispara na DESCIDA do botao, antes de o Windows ativar
        a janela clicada. Como o usuario vem de clicar num botao do proprio
        app, no instante do clique a janela em foco ainda e a nossa — ler o
        foco ali dava sempre "o jogo nao estava em foco". Esperar o foco
        assentar e o que torna a gravacao possivel.
        """
        deadline = time.monotonic() + timeout
        while True:
            self.windows.invalidate()
            origin = self.windows.game_client_origin()
            if origin is not None:
                return origin
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.05)

    def capture_team_slot(self, slot: int, screen_x: int, screen_y: int) -> bool:
        """Grava a posicao de um retrato a partir de um clique do usuario."""
        if not 1 <= slot <= 6:
            raise ValueError("O slot do Pokémon deve estar entre 1 e 6")
        origin = self._wait_for_game_origin()
        if origin is None:
            log.warning(
                "Posição não gravada: o clique precisa ser dentro da janela do "
                "jogo (ela não ficou em primeiro plano)"
            )
            return False
        self.profile.team_slots[slot - 1] = (
            screen_x - origin[0], screen_y - origin[1]
        )
        log.info(
            "Posição do Pokémon %d gravada em %s (relativa à janela do jogo)",
            slot, self.profile.team_slots[slot - 1],
        )
        # Grava na hora: uma posicao que some ao fechar o app nao serve.
        self.save_profile()
        self._notify()
        return True

    @staticmethod
    def _is_keyboard_trigger(hotkey: str) -> bool:
        return bool(hotkey) and hotkey not in MOUSE_TRIGGERS

    def preview_conflicts(self) -> list[str]:
        """Lista hotkeys repetidas/invalidas sem registrar nada."""
        problems: list[str] = []
        if self.profile.game == "PXG" and not self.settings.client_executable:
            problems.append("PXG: selecione o executavel do cliente em Configuracoes.")
        seen: dict[tuple, str] = {}
        emergency = normalize(self.settings.emergency_hotkey)
        if emergency is not None:
            seen[emergency] = "Emergencia"
        elif self.settings.emergency_hotkey:
            problems.append(f"Emergencia: {self.settings.emergency_hotkey} (invalida)")

        for binding in self.build_bindings():
            canonical = normalize(binding.hotkey)
            if canonical is None:
                problems.append(f"{binding.label}: {binding.hotkey} (invalida)")
                continue
            owner = seen.get(canonical)
            if owner is not None:
                problems.append(
                    f"{binding.label}: {binding.hotkey} (duplicada, ja usada por {owner})"
                )
                continue
            seen[canonical] = binding.label

        # A tecla que fecha o chat e enviada POR NOS entre as etapas. Se ela
        # for igual a de cancelar, a macro cancela a si mesma no meio.
        close_key = normalize(self.settings.chat_close_key)
        if close_key is not None:
            cancel = normalize(self.settings.cancel_hotkey)
            if cancel is not None and close_key == cancel:
                problems.append(
                    f"Fechar chat ({self.settings.chat_close_key}) e igual a "
                    "Cancelar macro: a sequencia cancelaria a si mesma"
                )
            emergency_key = normalize(self.settings.emergency_hotkey)
            if emergency_key is not None and close_key == emergency_key:
                problems.append(
                    f"Fechar chat ({self.settings.chat_close_key}) e igual a "
                    "Parada de emergencia: a macro se desligaria sozinha"
                )

        wheel_owners: dict[str, str] = {}
        for macro in self.profile.macros:
            if macro.hotkey in MOUSE_TRIGGERS and macro.enabled and macro.steps:
                owner = wheel_owners.get(macro.hotkey)
                if owner is not None:
                    problems.append(
                        f"{macro.name}: {MOUSE_LABELS[macro.hotkey]} "
                        f"(duplicada, ja usada por {owner})"
                    )
                else:
                    wheel_owners[macro.hotkey] = macro.name
        if self.profile.game == "PXG" and self.profile.rotation_enabled:
            if not any(m.rotation and m.enabled and m.steps for m in self.profile.macros):
                problems.append("Rotação Pokémon: crie e ative a macro de revive")
        if wheel_owners and not self.wheel.available:
            problems.append(self.wheel.unavailable_reason)
        return problems

    def enable_hotkeys(self) -> BindResult:
        result = self.hotkeys.bind(self.build_bindings())
        result.duplicates.extend(self._skipped_bindings)
        self.wheel.bind(self.wheel_bindings())
        self._enabled = True
        self._suspended = False
        log.info("Hotkeys ativadas (%d registradas)", len(result.registered))
        for problem in result.duplicates + result.invalid:
            log.warning("Hotkey ignorada -> %s", problem)
        self._notify()
        return result

    def disable_hotkeys(self, reason: str = "") -> None:
        self.hotkeys.unbind_all()
        self.wheel.unbind_all()
        self._enabled = False
        self.combo.cancel()
        with self._state_lock:
            self._active_pokemon_slot = None
            self._rotation_target = None
        log.info("Hotkeys desativadas%s", f" ({reason})" if reason else "")
        self._notify()

    def toggle_hotkeys(self) -> None:
        if self._enabled:
            self.disable_hotkeys()
        else:
            self.enable_hotkeys()

    def refresh_bindings(self) -> BindResult | None:
        """Reaplica os gatilhos apos uma alteracao de configuracao."""
        if not self._enabled:
            return None
        return self.enable_hotkeys()

    def setup_emergency(self) -> bool:
        return self.hotkeys.bind_emergency(
            self.settings.emergency_hotkey, self._on_emergency
        )

    def _on_emergency(self) -> None:
        self.combo.cancel()
        self.hotkeys.unbind_all()
        self.wheel.unbind_all()
        self._enabled = False
        self._mode = MODE_NONE
        log.warning("PARADA DE EMERGENCIA acionada (%s)", self.settings.emergency_hotkey)
        self._set_last_action("Parada de emergencia")

    # --------------------------------------------------------------- disparos

    def game_focused(self) -> bool:
        return self.windows.is_game_focused()

    def _store_game_settings(self, game: str) -> None:
        self.settings.game_settings[game] = {
            key: getattr(self.settings, key) for key in GAME_SETTINGS
        }

    def _load_game_settings(self, game: str) -> None:
        data = self.settings.game_settings.get(game, {})
        restored = Settings.from_dict(data)
        for key in GAME_SETTINGS:
            value = getattr(restored, key)
            if isinstance(value, str) and data.get(key) == "":
                value = ""
            setattr(self.settings, key, value)

    def _configure_game_window(self) -> None:
        executable = self.settings.client_executable.replace("/", "\\").rsplit("\\", 1)[-1].lower()
        executables = frozenset({executable}) if executable else (
            CLIENT_EXECUTABLES if self.profile.game == "PKA" else frozenset()
        )
        classes = CLIENT_WINDOW_CLASSES if self.profile.game == "PKA" and not executable else frozenset()
        self.windows = WindowManager(executables, classes)

    def _can_run(self) -> bool:
        """Guardas antes de qualquer envio de tecla."""
        if not self._enabled or self._suspended:
            return False
        # Evita que as teclas enviadas por nos redisparem outros gatilhos
        # e que duas acoes digitem ao mesmo tempo.
        if self.executor.busy or self.combo.running:
            return False
        if self.settings.require_game_focus and not self.windows.is_game_focused():
            log.info("Acao ignorada: %s nao esta em primeiro plano", self.profile.game)
            return False
        return True

    def _dispatch(self, label: str, func: Callable[[], None]) -> None:
        """Executa fora da thread do hook (que nunca pode bloquear)."""
        profile = self.profile

        def runner() -> None:
            try:
                if self.profile is not profile or self._suspended or not self._enabled:
                    return
                func()
            except Exception as exc:  # noqa: BLE001
                log.exception("Erro ao executar %s: %s", label, exc)

        threading.Thread(target=runner, name=f"action-{label}", daemon=True).start()

    def _make_skill_handler(self, number: int) -> Callable[[], None]:
        def handler() -> None:
            if not self._can_run():
                return
            skill = self.profile.skill(number)
            if skill is None or not skill.key:
                return
            self._dispatch(
                skill.name, lambda: self._run_skill(skill.name, skill.key, skill.hold_ms)
            )

        return handler

    def _run_skill(self, name: str, key: str, hold_ms: int) -> None:
        if self.executor.tap(key, hold_ms):
            log.info("%s executada", name)
            self._set_last_action(name)

    def _make_action_handler(self, label: str) -> Callable[[], None]:
        def handler() -> None:
            if not self._can_run():
                return
            action = self._action_by_label(label)
            if action is None:
                return
            self._dispatch(label, lambda: self._run_action(action))

        return handler

    def _action_by_label(self, label: str) -> ActionConfig | None:
        profile = self.profile
        for action in (profile.revive, profile.offensive, profile.defensive):
            if action.label == label:
                return action
        return None

    def _run_action(self, action: ActionConfig) -> None:
        if not self.executor.run_action(action):
            return
        log.info("%s acionado", action.label)
        self._apply_mode_from_text(action.label, action.command)
        self._set_last_action(action.label)

    def _apply_mode_from_text(self, label: str, command: str = "") -> None:
        """Atualiza o indicador visual de modo (nunca lido do jogo)."""
        haystack = f"{label} {command}".lower()
        if "offensive" in haystack:
            self._mode = MODE_OFFENSIVE
        elif "defensive" in haystack:
            self._mode = MODE_DEFENSIVE

    # ----------------------------------------------------------------- macros

    def macro_actions(self, macro: Macro) -> list[MacroAction]:
        """Resolve as etapas da macro em teclas e comandos concretos."""
        profile = self.profile
        actions: list[MacroAction] = []
        for position, step in enumerate(macro.steps, start=1):
            if step.type == STEP_COMMAND:
                if not step.command:
                    log.warning("Etapa %d de %s ignorada: comando vazio", position, macro.name)
                    continue
                actions.append(
                    MacroAction(
                        label=step.command,
                        kind=STEP_COMMAND,
                        command=step.command,
                        delay_ms=step.delay_ms,
                    )
                )
            elif step.type == STEP_KEY:
                if not step.key:
                    log.warning("Etapa %d de %s ignorada: tecla vazia", position, macro.name)
                    continue
                actions.append(
                    MacroAction(
                        label=f"tecla {step.key}",
                        kind=STEP_KEY,
                        key=step.key,
                        hold_ms=DEFAULT_HOLD_MS,
                        delay_ms=step.delay_ms,
                    )
                )
            else:
                skill = profile.skill(step.skill)
                if skill is None or not skill.key:
                    log.warning(
                        "Etapa %d de %s ignorada: Skill %d sem tecla",
                        position,
                        macro.name,
                        step.skill,
                    )
                    continue
                actions.append(
                    MacroAction(
                        label=skill.name,
                        kind=STEP_KEY,
                        key=skill.key,
                        hold_ms=skill.hold_ms,
                        delay_ms=step.delay_ms,
                    )
                )
        return actions

    def _make_macro_handler(self, name: str) -> Callable[[], None]:
        def handler() -> None:
            if not self._enabled or self._suspended or self.combo.running:
                return
            if self.settings.require_game_focus and not self.windows.is_game_focused():
                log.info("Macro %s ignorada: o jogo nao esta em primeiro plano", name)
                return
            self.start_macro(name)

        return handler

    def start_macro(self, name: str) -> bool:
        macro = self.profile.macro(name)
        if macro is None:
            log.warning("Macro %s nao existe no perfil ativo", name)
            return False
        if macro.rotation:
            return self._rotate_pokemon()
        actions = self.macro_actions(macro)
        if not actions:
            log.warning("Macro %s ignorada: nenhuma etapa valida", name)
            return False
        if not self.combo.start(actions, macro.name):
            return False
        log.info("Macro %s iniciada (%d etapas)", macro.name, len(actions))
        for step in macro.steps:
            if step.type == STEP_COMMAND:
                self._apply_mode_from_text("", step.command)
        self._set_last_action(f"{macro.name} iniciada")
        return True

    def _on_cancel_hotkey(self) -> None:
        # Cancelar funciona mesmo com o executor ocupado: so seta um Event.
        if self.cancel_combo():
            log.info("Macro cancelada pelo usuario")

    def cancel_combo(self) -> bool:
        return self.combo.cancel()

    def _on_macro_step(self, label: str) -> None:
        with self._state_lock:
            if self._rotation_target is not None and label.startswith(
                f"{PULL_STEP} {self._rotation_target} ("
            ):
                self._active_pokemon_slot = self._rotation_target
        log.info("Macro -> %s", label)
        self._set_last_action(label)

    def _on_macro_finish(self, status: str) -> None:
        for nome in (ROTATION_NAME, SWITCH_NAME):
            if not status.startswith(nome):
                continue
            with self._state_lock:
                if status == f"{nome} concluida":
                    self._active_pokemon_slot = self._rotation_target
                self._rotation_target = None
            break
        log.info("%s", status)
        self._set_last_action(status)

    # ------------------------------------------------------- edicao / estado

    def suspend(self, reason: str = "") -> None:
        """Pausa os disparos enquanto a interface esta em modo de edicao."""
        if self._suspended:
            return
        self._suspended = True
        self.combo.cancel()
        if reason:
            log.info("Acoes pausadas (%s)", reason)
        self._notify()

    def resume(self) -> None:
        if not self._suspended:
            return
        self._suspended = False
        self._notify()

    def set_active_profile(self, name: str) -> None:
        if self.profiles.get(name) is None:
            from app.services.profile_manager import ProfileError
            raise ProfileError(f"Perfil inexistente: {name}")
        self._suspended = True
        self.combo.cancel()
        self.combo.wait(2.0)
        if self.combo.running or self.executor.busy:
            self._suspended = False
            raise RuntimeError("Aguarde a acao atual terminar antes de trocar o perfil.")
        old_game = self.profile.game
        self._store_game_settings(old_game)
        self.profiles.set_active(name)
        with self._state_lock:
            self._active_pokemon_slot = None
            self._rotation_target = None
        if self.profile.game != old_game:
            self._load_game_settings(self.profile.game)
            self.setup_emergency()
        self._configure_game_window()
        self.settings.active_profile = name
        self._mode = MODE_NONE
        self._suspended = False
        log.info("Perfil %s carregado", name)
        self.refresh_bindings()
        self._notify()

    def save_profile(self) -> bool:
        ok = self.profiles.save()
        if ok:
            log.info("Perfil %s salvo", self.profile.name)
        self.refresh_bindings()
        self._notify()
        return ok

    def save_settings(self) -> bool:
        self.settings.active_profile = self.profiles.active_name
        self._store_game_settings(self.profile.game)
        self._configure_game_window()
        return self._settings_manager.save()

    def shutdown(self) -> None:
        """Encerramento limpo: para tudo e persiste o estado."""
        self.combo.cancel()
        self.combo.wait(1.0)
        self.hotkeys.shutdown()
        self.wheel.unbind_all()
        self._enabled = False
        self.profiles.save_all()
        self.save_settings()
        log.info("Aplicacao encerrada")
