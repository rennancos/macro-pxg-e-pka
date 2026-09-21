"""Lista compacta de skills com um editor reutilizado para a selecao."""
from __future__ import annotations

from tkinter import ttk
import customtkinter as ctk

from app.constants import MAX_DELAY_MS
from app.gui.widgets import COLOR_ERROR, COLOR_MUTED, BasePage, Card, HotkeyEntry, IntEntry
from app.models.profile import SkillConfig


class SkillsPage(BasePage):
    title = "Skills"

    def build(self) -> None:
        self._skills: list[SkillConfig] = []
        self._selected = 0
        ctk.CTkLabel(self, text="Skills", font=ctk.CTkFont(size=22, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(self, text="Selecione uma skill para editar. As alteracoes ficam pendentes ate Salvar.",
                     text_color=COLOR_MUTED).pack(anchor="w", padx=20, pady=(0, 12))
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        list_frame = ctk.CTkFrame(body)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        self.table = ttk.Treeview(list_frame, columns=("name", "key", "hotkey"),
                                  show="headings", selectmode="browse", style="Skills.Treeview")
        for column, title, width in (("name", "Skill", 125), ("key", "No jogo", 65), ("hotkey", "Hotkey", 85)):
            self.table.heading(column, text=title)
            self.table.column(column, width=width, minwidth=50, stretch=True)
        self.table.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.table.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<<TreeviewSelect>>", self._select)

        detail = Card(body, title="Editar skill")
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        form = ctk.CTkFrame(detail, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=8)
        self.enabled = ctk.CTkCheckBox(form, text="Skill ativa")
        self.enabled.pack(anchor="w", pady=(0, 12))
        self.name_entry = ctk.CTkEntry(form, width=230)
        self.hotkey = HotkeyEntry(form, self.controller, width=150)
        self.key = HotkeyEntry(form, self.controller, width=150)
        self.hold = IntEntry(form, minimum=0, maximum=MAX_DELAY_MS, width=90)
        for label, widget in (("Nome", self.name_entry), ("Hotkey que voce aperta", self.hotkey),
                              ("Tecla enviada ao jogo", self.key), ("Tempo de toque (ms)", self.hold)):
            ctk.CTkLabel(form, text=label, anchor="w").pack(anchor="w")
            widget.pack(anchor="w", pady=(0, 10))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(actions, text="Salvar skills", command=self.save).pack(side="left")
        ctk.CTkButton(actions, text="Descartar alteracoes", fg_color="gray30",
                     command=self.on_show).pack(side="left", padx=8)
        self._style_table()

    def _style_table(self) -> None:
        dark = ctk.get_appearance_mode() == "Dark"
        background, foreground = ("#242424", "#eeeeee") if dark else ("#f4f4f4", "#202020")
        style = ttk.Style(self)
        style.configure("Skills.Treeview", background=background, fieldbackground=background,
                        foreground=foreground, rowheight=32, font=("Segoe UI", 10))
        style.map("Skills.Treeview", background=[("selected", "#245a8d")],
                  foreground=[("selected", "white")])

    def on_show(self) -> None:
        self._skills = [SkillConfig.from_dict(skill.to_dict(), i)
                        for i, skill in enumerate(self.controller.profile.skills)]
        self._selected = min(self._selected, len(self._skills) - 1)
        self.table.delete(*self.table.get_children())
        for index, skill in enumerate(self._skills):
            self.table.insert("", "end", iid=str(index), values=self._values(skill))
        self.table.selection_set(str(self._selected))
        self._load_selected()
        self._style_table()

    def on_state_change(self) -> None:
        self._style_table()

    @staticmethod
    def _values(skill: SkillConfig) -> tuple[str, str, str]:
        return (("" if skill.enabled else "(off) ") + skill.name, skill.key or "—", skill.hotkey or "—")

    def _collect(self) -> None:
        if not self._skills:
            return
        skill = self._skills[self._selected]
        skill.name = self.name_entry.get().strip() or f"Skill {self._selected + 1}"
        skill.key = self.key.get_value()
        skill.hotkey = self.hotkey.get_value()
        skill.hold_ms = self.hold.get_value(skill.hold_ms)
        skill.enabled = bool(self.enabled.get())
        self.table.item(str(self._selected), values=self._values(skill))

    def _load_selected(self) -> None:
        skill = self._skills[self._selected]
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, skill.name)
        self.key.set_value(skill.key)
        self.hotkey.set_value(skill.hotkey)
        self.hold.set_value(skill.hold_ms)
        self.enabled.select() if skill.enabled else self.enabled.deselect()

    def _select(self, _event=None) -> None:
        selection = self.table.selection()
        if not selection or int(selection[0]) == self._selected:
            return
        self._collect()
        self._selected = int(selection[0])
        self._load_selected()

    def save(self) -> None:
        self._collect()
        self.controller.profile.skills = [SkillConfig.from_dict(skill.to_dict(), i)
                                          for i, skill in enumerate(self._skills)]
        if not self.controller.save_profile():
            self.notify("Falha ao salvar o perfil - veja os logs.", COLOR_ERROR)
            return
        problems = self.controller.preview_conflicts()
        if problems:
            self.notify("Salvo, mas com problemas: " + "; ".join(problems), COLOR_ERROR)
        else:
            self.notify("Skills salvas.")
        self.on_show()
