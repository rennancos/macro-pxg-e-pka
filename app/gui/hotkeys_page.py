"""Configuracao de Revive, Offensive, Defensive e demais acoes."""

from __future__ import annotations

import customtkinter as ctk

from app.constants import ACTION_MODE_COMMAND, ACTION_MODE_KEY, MAX_DELAY_MS
from app.gui.widgets import (
    COLOR_ERROR,
    COLOR_MUTED,
    BasePage,
    Card,
    HotkeyEntry,
    IntEntry,
)
from app.models.profile import ActionConfig

_MODE_LABELS = {
    ACTION_MODE_KEY: "Tecla",
    ACTION_MODE_COMMAND: "Comando no chat",
}
_MODE_VALUES = {label: mode for mode, label in _MODE_LABELS.items()}


class ActionEditor(Card):
    """Editor de uma acao: hotkey + tecla ou comando de chat."""

    def __init__(self, master: object, page: BasePage, title: str, hint: str = "") -> None:
        super().__init__(master, title=title)
        self.page = page
        controller = page.controller

        if hint:
            ctk.CTkLabel(self, text=hint, text_color=COLOR_MUTED, anchor="w").pack(
                anchor="w", padx=16, pady=(0, 6)
            )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(0, 14))

        self.enabled = ctk.CTkCheckBox(body, text="Ativa")
        self.enabled.grid(row=0, column=0, sticky="w", pady=4)

        ctk.CTkLabel(body, text="Hotkey", anchor="w", width=90).grid(
            row=0, column=1, sticky="w", padx=(16, 4)
        )
        self.hotkey = HotkeyEntry(body, controller, width=140)
        self.hotkey.grid(row=0, column=2, sticky="w")

        ctk.CTkLabel(body, text="Modo", anchor="w", width=90).grid(
            row=1, column=1, sticky="w", padx=(16, 4), pady=6
        )
        self.mode = ctk.CTkSegmentedButton(
            body, values=list(_MODE_LABELS.values()), command=self._on_mode_change
        )
        self.mode.grid(row=1, column=2, sticky="w", pady=6)

        ctk.CTkLabel(body, text="Tecla no jogo", anchor="w", width=90).grid(
            row=2, column=1, sticky="w", padx=(16, 4)
        )
        self.key = HotkeyEntry(body, controller, width=140)
        self.key.grid(row=2, column=2, sticky="w")

        ctk.CTkLabel(body, text="Toque (ms)", anchor="w", width=90).grid(
            row=2, column=3, sticky="w", padx=(16, 4)
        )
        self.hold = IntEntry(body, minimum=0, maximum=MAX_DELAY_MS, width=80)
        self.hold.grid(row=2, column=4, sticky="w")

        ctk.CTkLabel(body, text="Comando", anchor="w", width=90).grid(
            row=3, column=1, sticky="w", padx=(16, 4), pady=6
        )
        self.command = ctk.CTkEntry(body, width=240, placeholder_text="!offensive")
        self.command.grid(row=3, column=2, columnspan=3, sticky="w", pady=6)

    def load(self, action: ActionConfig) -> None:
        if action.enabled:
            self.enabled.select()
        else:
            self.enabled.deselect()
        self.hotkey.set_value(action.hotkey)
        self.key.set_value(action.key)
        self.hold.set_value(action.hold_ms)
        self.command.delete(0, "end")
        self.command.insert(0, action.command)
        self.mode.set(_MODE_LABELS.get(action.mode, _MODE_LABELS[ACTION_MODE_KEY]))
        self._on_mode_change(self.mode.get())

    def apply(self, action: ActionConfig) -> None:
        action.enabled = bool(self.enabled.get())
        action.hotkey = self.hotkey.get_value()
        action.mode = _MODE_VALUES.get(self.mode.get(), ACTION_MODE_KEY)
        action.key = self.key.get_value()
        action.hold_ms = self.hold.get_value(action.hold_ms)
        action.command = self.command.get().strip()

    def _on_mode_change(self, label: str) -> None:
        """Mostra apenas os campos relevantes ao modo escolhido."""
        is_command = _MODE_VALUES.get(label) == ACTION_MODE_COMMAND
        self.command.configure(state="normal" if is_command else "disabled")
        state = "disabled" if is_command else "normal"
        self.key.entry.configure(state=state)
        self.key.button.configure(state=state)
        self.hold.configure(state=state)


class HotkeysPage(BasePage):
    title = "Hotkeys"

    def build(self) -> None:
        ctk.CTkLabel(
            self, text="Acoes e hotkeys", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=14)

        self.revive = ActionEditor(container, self, "Revive")
        self.revive.pack(fill="x", pady=6)

        self.offensive = ActionEditor(
            container,
            self,
            "Offensive",
            "No modo comando: abre o chat, digita o texto e envia com Enter.",
        )
        self.offensive.pack(fill="x", pady=6)

        self.defensive = ActionEditor(
            container,
            self,
            "Defensive",
            "Mesmo funcionamento do Offensive, com outro comando.",
        )
        self.defensive.pack(fill="x", pady=6)

        self.emergency_label = ctk.CTkLabel(container, text="", text_color=COLOR_MUTED)
        self.emergency_label.pack(anchor="w", padx=16, pady=(10, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(actions, text="Salvar acoes", command=self.save).pack(side="left")
        ctk.CTkButton(
            actions, text="Descartar alteracoes", fg_color="gray30", command=self.on_show
        ).pack(side="left", padx=8)

    def on_show(self) -> None:
        profile = self.controller.profile
        self.revive.load(profile.revive)
        self.offensive.load(profile.offensive)
        self.defensive.load(profile.defensive)
        self.emergency_label.configure(
            text=(
                "Parada de emergencia: "
                f"{self.controller.settings.emergency_hotkey or 'nao configurada'} "
                "(altere em Configuracoes)"
            )
        )

    def save(self) -> None:
        profile = self.controller.profile
        self.revive.apply(profile.revive)
        self.offensive.apply(profile.offensive)
        self.defensive.apply(profile.defensive)

        if not self.controller.save_profile():
            self.notify("Falha ao salvar o perfil - veja os logs.", COLOR_ERROR)
            return

        problems = self.controller.preview_conflicts()
        if problems:
            self.notify("Salvo, mas com problemas: " + "; ".join(problems), COLOR_ERROR)
        else:
            self.notify("Acoes salvas.")
        self.on_show()
