"""Widgets reutilizaveis da interface."""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk

from app.services.controller import AppController
from app.services.hotkey_manager import is_valid, read_hotkey

COLOR_OK = "#2fbf71"
COLOR_WARN = "#e0a800"
COLOR_ERROR = "#e05260"
COLOR_MUTED = "#8b93a7"
COLOR_ACCENT = "#3b8ed0"


class Card(ctk.CTkFrame):
    """Bloco visual com titulo opcional."""

    def __init__(self, master: Any, title: str = "", **kwargs: Any) -> None:
        super().__init__(master, corner_radius=10, **kwargs)
        self.body = self
        if title:
            ctk.CTkLabel(
                self, text=title, font=ctk.CTkFont(size=15, weight="bold")
            ).pack(anchor="w", padx=16, pady=(12, 6))


class IntEntry(ctk.CTkEntry):
    """Entrada numerica que nunca devolve valor invalido ou negativo."""

    def __init__(
        self,
        master: Any,
        value: int = 0,
        minimum: int = 0,
        maximum: int = 60_000,
        width: int = 80,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, width=width, **kwargs)
        self._minimum = minimum
        self._maximum = maximum
        self.set_value(value)

    def set_value(self, value: int) -> None:
        text = str(value)
        if self.get() == text:
            return  # reescrever o mesmo valor custa um redesenho do CTk
        self.delete(0, tk.END)
        self.insert(0, text)

    def get_value(self, default: int = 0) -> int:
        try:
            number = int(float(self.get().strip().replace(",", ".")))
        except (TypeError, ValueError):
            number = default
        number = max(self._minimum, min(self._maximum, number))
        self.set_value(number)
        return number


class HotkeyEntry(ctk.CTkFrame):
    """Campo de tecla/hotkey com botao de captura.

    Durante a captura o controller e suspenso, para que a tecla pressionada
    nao dispare nenhuma acao no jogo.
    """

    def __init__(
        self,
        master: Any,
        controller: AppController,
        value: str = "",
        width: int = 150,
        on_change: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._controller = controller
        self._on_change = on_change
        self._capturing = False

        self.entry = ctk.CTkEntry(self, width=width)
        self.entry.pack(side="left")
        self.entry.bind("<KeyRelease>", lambda _event: self._changed())

        self.button = ctk.CTkButton(self, text="Gravar", width=70, command=self.capture)
        self.button.pack(side="left", padx=(6, 0))

        self.set_value(value)

    # ------------------------------------------------------------------ valor

    def set_value(self, value: str) -> None:
        text = value or ""
        if self.entry.get() == text:
            return  # idem: mesmo valor, nada a redesenhar
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)
        self._paint()

    def get_value(self) -> str:
        return self.entry.get().strip().lower()

    def _changed(self) -> None:
        self._paint()
        if self._on_change is not None:
            self._on_change()

    def _paint(self) -> None:
        value = self.get_value()
        if not value:
            self.entry.configure(border_color=COLOR_MUTED)
        elif is_valid(value):
            self.entry.configure(border_color=COLOR_OK)
        else:
            self.entry.configure(border_color=COLOR_ERROR)

    # ---------------------------------------------------------------- captura

    def capture(self) -> None:
        if self._capturing:
            return
        self._capturing = True
        self.button.configure(text="...", state="disabled")
        self._controller.suspend("gravando hotkey")

        def worker() -> None:
            try:
                hotkey = read_hotkey()
            except Exception:  # noqa: BLE001 - biblioteca indisponivel/sem permissao
                hotkey = ""
            self._safe_after(hotkey)

        threading.Thread(target=worker, name="hotkey-capture", daemon=True).start()

    def _safe_after(self, hotkey: str) -> None:
        try:
            self.after(0, lambda: self._finish_capture(hotkey))
        except (tk.TclError, RuntimeError):
            self._controller.resume()

    def _finish_capture(self, hotkey: str) -> None:
        self._capturing = False
        try:
            self.button.configure(text="Gravar", state="normal")
            if hotkey:
                self.set_value(hotkey)
                self._changed()
        except tk.TclError:
            pass
        finally:
            self._controller.resume()


def labeled(master: Any, text: str, width: int = 110) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=text, width=width, anchor="w")


def toast(master: Any, text: str, color: str = COLOR_OK) -> None:
    """Mensagem curta no rodape da pagina (sem janelas modais)."""
    label = getattr(master, "status_label", None)
    if label is None:
        return
    try:
        label.configure(text=text, text_color=color)
        label.after(6000, lambda: _clear(label))
    except tk.TclError:
        pass


def _clear(label: ctk.CTkLabel) -> None:
    try:
        label.configure(text="")
    except tk.TclError:
        pass


class BasePage(ctk.CTkFrame):
    """Base das paginas: guarda o controller e expoe um rodape de status."""

    title: str = ""

    def __init__(self, master: Any, controller: AppController) -> None:
        super().__init__(master, fg_color=ctk.ThemeManager.theme["CTk"]["fg_color"])
        self.controller = controller
        self._loaded_context = None
        self.status_label = ctk.CTkLabel(self, text="", anchor="w")
        self.build()
        self.status_label.pack(side="bottom", fill="x", padx=20, pady=(0, 10))

    def build(self) -> None:
        """Monta os widgets da pagina (sobrescrito pelas subclasses)."""

    def on_show(self) -> None:
        """Chamado ao exibir a pagina: recarrega os dados do perfil ativo."""

    def activate(self) -> None:
        """Recarrega apenas quando os dados salvos mudaram; mantem os rascunhos."""
        context = (
            id(self.controller.profile),
            repr(self.controller.profile.to_dict()),
            repr(self.controller.settings.to_dict()),
            tuple(self.controller.profiles.names),
        )
        if context != self._loaded_context:
            self.on_show()
            self._loaded_context = context
        else:
            self.on_state_change()

    def on_state_change(self) -> None:
        """Chamado quando o controller muda de estado (nao recarrega edicoes)."""

    def notify(self, text: str, color: str = COLOR_OK) -> None:
        toast(self, text, color)
