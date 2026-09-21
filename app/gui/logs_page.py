"""Visualizacao dos logs da aplicacao."""

from __future__ import annotations

import os
import subprocess
import sys

import customtkinter as ctk

from app.gui.widgets import COLOR_MUTED, BasePage
from app.utils.logger import memory_handler
from app.utils.paths import LOGS_DIR


class LogsPage(BasePage):
    title = "Logs"

    def build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 6))
        ctk.CTkLabel(
            header, text="Logs", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")
        ctk.CTkButton(header, text="Atualizar", width=90, command=self.on_show).pack(
            side="right"
        )
        ctk.CTkButton(
            header, text="Abrir pasta", width=100, fg_color="gray30", command=self._open_folder
        ).pack(side="right", padx=8)
        ctk.CTkButton(
            header, text="Limpar tela", width=100, fg_color="gray30", command=self._clear
        ).pack(side="right")

        ctk.CTkLabel(
            self,
            text="Apenas acoes do proprio programa sao registradas - nada do que voce digita.",
            text_color=COLOR_MUTED,
            anchor="w",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.textbox.configure(state="disabled")

    def on_show(self) -> None:
        self._render(memory_handler.dump())

    def on_state_change(self) -> None:
        self.on_show()

    def _render(self, text: str) -> None:
        if text == getattr(self, "_rendered_text", None):
            return
        self._rendered_text = text
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def _clear(self) -> None:
        memory_handler.clear()
        self._render("")

    def _open_folder(self) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(LOGS_DIR)  # noqa: S606 - abre o explorador do Windows
            else:
                subprocess.Popen(["xdg-open", str(LOGS_DIR)])
        except Exception:  # noqa: BLE001
            self.notify(f"Abra manualmente: {LOGS_DIR}", COLOR_MUTED)
