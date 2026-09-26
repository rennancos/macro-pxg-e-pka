"""Gerenciamento de perfis de Pokemon."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from app.constants import MOUSE_LABELS
from app.gui.widgets import (
    COLOR_ERROR,
    COLOR_MUTED,
    BasePage,
    Card,
    accent,
    accent_hover,
)
from app.services.profile_manager import ProfileError


class ProfilesPage(BasePage):
    title = "Pokemon"

    def build(self) -> None:
        ctk.CTkLabel(
            self, text="Perfis PKA / PXG", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Cada perfil guarda skills, acoes e combo proprios em config/profiles/.",
            text_color=COLOR_MUTED,
            anchor="w",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        list_card = Card(body, title="Perfis")
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.listbox = ctk.CTkScrollableFrame(list_card, fg_color="transparent")
        self.listbox.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        detail_card = Card(body, title="Perfil selecionado")
        detail_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        form = ctk.CTkFrame(detail_card, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(form, text="Nome", anchor="w").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(form, width=240)
        self.name_entry.pack(anchor="w", pady=(2, 8))

        self.summary = ctk.CTkTextbox(detail_card, height=200)
        self.summary.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.summary.configure(state="disabled")

        actions = ctk.CTkFrame(detail_card, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(actions, text="Novo", width=90, command=self._new).pack(side="left")
        ctk.CTkButton(actions, text="Duplicar", width=90, command=self._duplicate).pack(
            side="left", padx=6
        )
        ctk.CTkButton(actions, text="Renomear", width=90, command=self._rename).pack(
            side="left"
        )
        ctk.CTkButton(
            actions, text="Excluir", width=90, fg_color="#8a3b44",
            hover_color="#713037", command=self._delete,
        ).pack(side="left", padx=6)

        self._buttons: list[ctk.CTkButton] = []

    # ----------------------------------------------------------------- dados

    def on_show(self) -> None:
        self._render_list()
        self._render_detail()

    def _render_list(self) -> None:
        for widget in self.listbox.winfo_children():
            widget.destroy()
        self._buttons = []
        active = self.controller.profiles.active_name
        for name in self.controller.profiles.names:
            is_active = name == active
            button = ctk.CTkButton(
                self.listbox,
                text=("* " if is_active else "   ") + f"[{self.controller.profiles.get(name).game}] {name}",
                anchor="w",
                fg_color=accent() if is_active else "gray25",
                hover_color=accent_hover(),
                command=lambda n=name: self._select(n),
            )
            button.pack(fill="x", pady=3)
            self._buttons.append(button)

    def _render_detail(self) -> None:
        profile = self.controller.profile
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, profile.name)

        lines = [f"Jogo: {profile.game}", f"Perfil: {profile.name}", "", "Skills:"]
        for index, skill in enumerate(profile.skills, start=1):
            state = "on " if skill.enabled else "off"
            lines.append(
                f"  {index}. [{state}] {skill.name:<14} hotkey={skill.hotkey or '-':<10}"
                f" tecla={skill.key or '-':<8} toque={skill.hold_ms}ms"
            )
        lines.append("")
        for action in (profile.revive, profile.offensive, profile.defensive):
            alvo = action.command if action.mode == "command" else action.key
            lines.append(
                f"{action.label:<10} hotkey={action.hotkey or '-':<10} "
                f"{action.mode}={alvo or '-'}"
            )
        lines.append("")
        lines.append("Macros:")
        if profile.macros:
            for macro in profile.macros:
                trigger = MOUSE_LABELS.get(macro.hotkey, macro.hotkey or "-")
                state = "on " if macro.enabled else "off"
                lines.append(
                    f"  [{state}] {macro.name:<14} gatilho={trigger:<22} "
                    f"etapas={len(macro.steps)}"
                )
                for step in macro.steps:
                    lines.append(f"          - {step.describe(profile)} ({step.delay_ms}ms)")
        else:
            lines.append("  (nenhuma)")

        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", "\n".join(lines))
        self.summary.configure(state="disabled")

    # ---------------------------------------------------------------- acoes

    def _select(self, name: str) -> None:
        try:
            self.controller.set_active_profile(name)
        except (ProfileError, RuntimeError) as exc:
            self.notify(str(exc), COLOR_ERROR)
            return
        self.controller.save_settings()
        self.on_show()
        self.notify(f"Perfil ativo: {name}")

    def _new(self) -> None:
        name = self._ask_name("Novo perfil", "Nome do novo perfil:")
        if not name:
            return
        self._run(lambda: self.controller.profiles.create(name, self.controller.profile.game), f'Perfil "{name}" criado.')

    def _duplicate(self) -> None:
        source = self.controller.profiles.active_name
        name = self._ask_name("Duplicar perfil", f'Nome da copia de "{source}":')
        if not name:
            return
        self._run(
            lambda: self.controller.profiles.duplicate(source, name),
            f'Perfil "{name}" duplicado.',
        )

    def _rename(self) -> None:
        old = self.controller.profiles.active_name
        new = self.name_entry.get().strip()
        if not new or new == old:
            self.notify("Altere o nome no campo acima antes de renomear.", COLOR_MUTED)
            return
        self._run(
            lambda: self.controller.profiles.rename(old, new), f'Perfil renomeado para "{new}".'
        )

    def _delete(self) -> None:
        name = self.controller.profiles.active_name
        game = self.controller.profile.game
        remaining = [n for n in self.controller.profiles.names
                     if n != name and self.controller.profiles.get(n).game == game]
        if not remaining:
            self.notify("Mantenha pelo menos um perfil para cada jogo.", COLOR_ERROR)
            return
        if not messagebox.askyesno("Excluir perfil", f'Excluir o perfil "{name}"?'):
            return
        def remove() -> None:
            self.controller.set_active_profile(remaining[0])
            self.controller.profiles.delete(name)
        self._run(remove, f'Perfil "{name}" excluido.')

    def _run(self, operation, success_message: str) -> None:
        """Executa uma operacao de perfil tratando o erro de forma amigavel."""
        try:
            operation()
        except (ProfileError, RuntimeError) as exc:
            self.notify(str(exc), COLOR_ERROR)
            return
        self.controller.settings.active_profile = self.controller.profiles.active_name
        self.controller.save_settings()
        self.controller.refresh_bindings()
        self.on_show()
        self.notify(success_message)

    def _ask_name(self, title: str, prompt: str) -> str:
        value = ctk.CTkInputDialog(title=title, text=prompt).get_input()
        return (value or "").strip()
