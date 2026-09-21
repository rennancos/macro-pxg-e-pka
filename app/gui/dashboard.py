"""Pagina inicial: resumo do estado atual."""

from __future__ import annotations

import customtkinter as ctk

from app.constants import (
    MODE_DEFENSIVE,
    MODE_OFFENSIVE,
    MOUSE_LABELS,
    MOUSE_TRIGGERS,
)
from app.gui.widgets import (
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_MUTED,
    COLOR_OK,
    COLOR_WARN,
    BasePage,
    Card,
)


def _wheel_owners(controller: object) -> dict[str, str]:
    """Macros presas a roda do mouse, no formato gatilho -> nome."""
    owners: dict[str, str] = {}
    for macro in controller.profile.macros:  # type: ignore[attr-defined]
        if macro.enabled and macro.steps and macro.hotkey in MOUSE_TRIGGERS:
            owners.setdefault(macro.hotkey, macro.name)
    return owners


class InfoCard(Card):
    """Cartao com um rotulo fixo e um valor grande."""

    def __init__(self, master: object, title: str, value: str = "---") -> None:
        super().__init__(master, title="")
        ctk.CTkLabel(self, text=title.upper(), text_color=COLOR_MUTED).pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        self.value_label = ctk.CTkLabel(
            self, text=value, font=ctk.CTkFont(size=20, weight="bold"), anchor="w"
        )
        self.value_label.pack(anchor="w", padx=16, pady=(2, 14))

    def set_value(self, text: str, color: str | None = None) -> None:
        self.value_label.configure(text=text, text_color=color or ("#dce4f7", "#dce4f7"))


class DashboardPage(BasePage):
    title = "Dashboard"

    def build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            header, text="Dashboard", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=20)
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1, uniform="cards")

        self.profile_card = InfoCard(grid, "Perfil ativo")
        self.profile_card.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=6)

        self.status_card = InfoCard(grid, "Status")
        self.status_card.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=6)

        self.mode_card = InfoCard(grid, "Modo")
        self.mode_card.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=6)

        self.action_card = InfoCard(grid, "Ultima acao")
        self.action_card.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=6)

        hotkeys_card = Card(self, title="Hotkeys ativas")
        hotkeys_card.pack(fill="both", expand=True, padx=20, pady=(6, 12))
        self.hotkeys_box = ctk.CTkTextbox(hotkeys_card, activate_scrollbars=True)
        self.hotkeys_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.hotkeys_box.configure(state="disabled")

    def on_show(self) -> None:
        self.on_state_change()

    def on_state_change(self) -> None:
        controller = self.controller
        self.profile_card.set_value(f"{controller.profile.game} / {controller.profile.name}", COLOR_ACCENT)

        status = controller.status_text
        status_color = COLOR_OK if status == "ATIVO" else (
            COLOR_WARN if status.startswith("PAUSADO") else COLOR_ERROR
        )
        self.status_card.set_value(status, status_color)

        mode = controller.mode
        mode_color = {
            MODE_OFFENSIVE: COLOR_ERROR,
            MODE_DEFENSIVE: COLOR_ACCENT,
        }.get(mode, COLOR_MUTED)
        self.mode_card.set_value(mode, mode_color)

        self.action_card.set_value(controller.last_action)
        self._render_hotkeys()

    def _render_hotkeys(self) -> None:
        controller = self.controller
        lines: list[str] = [
            f"Emergencia (sempre ativa) : {controller.settings.emergency_hotkey or '---'}",
            f"Cancelar macro            : {controller.settings.cancel_hotkey or '---'}",
            "Exige jogo em foco        : "
            + ("sim" if controller.settings.require_game_focus else "nao"),
            "",
        ]
        if controller.enabled:
            active = controller.hotkeys.active_bindings
            wheel = {
                MOUSE_LABELS[trigger]: name
                for trigger, name in _wheel_owners(controller).items()
            }
            if active or wheel:
                labels = list(active) + list(wheel)
                width = max(len(label) for label in labels)
                lines += [f"{label:<{width}} : {hotkey}" for label, hotkey in active.items()]
                lines += [f"{label:<{width}} : {name}" for label, name in wheel.items()]
            else:
                lines.append("Nenhuma hotkey registrada.")
        else:
            lines.append("")
            lines.append("Hotkeys desativadas. Use ATIVAR HOTKEYS no topo da janela.")
            lines.append("")
            lines.append("Configuradas no perfil:")
            for binding in controller.build_bindings():
                lines.append(f"  {binding.label} : {binding.hotkey}")
            for trigger, name in _wheel_owners(controller).items():
                lines.append(f"  {name} : {MOUSE_LABELS[trigger]}")

        problems = controller.preview_conflicts()
        if problems:
            lines.append("")
            lines.append("Problemas encontrados:")
            lines += [f"  ! {problem}" for problem in problems]

        text = "\n".join(lines)
        if text == getattr(self, "_rendered_hotkeys", None):
            return
        self._rendered_hotkeys = text
        self.hotkeys_box.configure(state="normal")
        self.hotkeys_box.delete("1.0", "end")
        self.hotkeys_box.insert("1.0", text)
        self.hotkeys_box.configure(state="disabled")
