"""Janela principal: navegacao, barra de status e ciclo de vida da app."""

from __future__ import annotations

import logging
from tkinter import messagebox

import customtkinter as ctk

from app.constants import APP_TITLE, MODE_DEFENSIVE, MODE_OFFENSIVE
from app.gui.combo_page import ComboPage
from app.gui.dashboard import DashboardPage
from app.gui.hotkeys_page import HotkeysPage
from app.gui.logs_page import LogsPage
from app.gui.profiles_page import ProfilesPage
from app.gui.settings_page import SettingsPage
from app.gui.skills_page import SkillsPage
from app.gui.widgets import (
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_MUTED,
    COLOR_OK,
    COLOR_WARN,
    BasePage,
)
from app.services.controller import AppController

log = logging.getLogger(__name__)

_REFRESH_MS = 200


def _virtual_screen() -> tuple[int, int, int, int]:
    """Retangulo de TODOS os monitores (left, top, right, bottom).

    winfo_screenwidth() so conhece o monitor primario: uma janela salva na
    segunda tela era considerada fora da tela e voltava para a primeira.
    """
    try:
        from ctypes import windll

        metric = windll.user32.GetSystemMetrics
        left, top = metric(76), metric(77)  # SM_X/YVIRTUALSCREEN
        return left, top, left + metric(78), top + metric(79)
    except Exception:  # noqa: BLE001 - fora do Windows
        return 0, 0, 1920, 1080


class MainWindow(ctk.CTk):
    def __init__(self, controller: AppController) -> None:
        # A janela congela ao mudar de monitor quando o CustomTkinter refaz a
        # escala: ele repinta TODOS os widgets de uma vez, deixa a janela em
        # alpha 0.15 e prende minsize == maxsize por 1s. Sem DPI awareness o
        # proprio Windows redimensiona a janela, sem repintar nada.
        ctk.deactivate_automatic_dpi_awareness()
        super().__init__()
        self.controller = controller
        self._dirty = True
        self._tick_id = None

        ctk.set_appearance_mode(controller.settings.appearance)
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.minsize(900, 600)
        self._restore_geometry()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_topbar()
        self._build_pages()

        controller.add_listener(self._mark_dirty)
        self._refresh()
        self._tick_id = self.after(_REFRESH_MS, self._tick)

    # --------------------------------------------------------------- layout

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=190, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="PKA / PXG", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(padx=18, pady=(22, 0), anchor="w")
        ctk.CTkLabel(sidebar, text="Hotkeys", text_color=COLOR_MUTED).pack(
            padx=18, pady=(0, 18), anchor="w"
        )

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._sidebar = sidebar
        self.game_menu = ctk.CTkSegmentedButton(
            sidebar, values=["PKA", "PXG"], command=self._on_game_selected
        )
        self.game_menu.pack(fill="x", padx=10, pady=(0, 12))
        self.game_menu.set(self.controller.profile.game)

    def _build_topbar(self) -> None:
        top = ctk.CTkFrame(self, height=64, corner_radius=0)
        top.grid(row=0, column=1, sticky="new")

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(left, text="Perfil:", text_color=COLOR_MUTED).pack(side="left")
        self.profile_menu = ctk.CTkOptionMenu(
            left, values=["---"], width=170, command=self._on_profile_selected
        )
        self.profile_menu.pack(side="left", padx=8)

        self.status_badge = ctk.CTkLabel(
            left, text="DESATIVADO", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_badge.pack(side="left", padx=(16, 6))

        self.mode_badge = ctk.CTkLabel(
            left, text="---", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.mode_badge.pack(side="left", padx=6)

        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side="right", padx=16, pady=12)

        self.toggle_button = ctk.CTkButton(
            right, text="ATIVAR HOTKEYS", width=170, command=self._toggle_hotkeys
        )
        self.toggle_button.pack(side="right")

        self.emergency_label = ctk.CTkLabel(self._sidebar, text="", text_color=COLOR_MUTED)
        self.emergency_label.pack(side="bottom", padx=12, pady=16)

    def _build_pages(self) -> None:
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_propagate(False)

        self._page_classes: dict[str, type[BasePage]] = {
            page_class.title: page_class
            for page_class in (
                DashboardPage,
                SkillsPage,
                ComboPage,
                ProfilesPage,
                HotkeysPage,
                SettingsPage,
                LogsPage,
            )
        }
        self.page_titles: tuple[str, ...] = tuple(self._page_classes)
        self.pages: dict[str, BasePage] = {}

        for title in self.page_titles:
            button = ctk.CTkButton(
                self._sidebar,
                text=title,
                anchor="w",
                height=38,
                corner_radius=6,
                fg_color="transparent",
                command=lambda name=title: self.show_page(name),
            )
            button.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[title] = button

        self.current_page: BasePage | None = None
        self._current_title = ""
        self.show_page(self.page_titles[0])

    def page(self, name: str) -> BasePage | None:
        """Devolve a pagina, montando-a na primeira vez que for pedida.

        Montar as sete no arranque custava o tempo todo de criacao de widget
        do CustomTkinter antes de a janela aparecer. Quem so usa o Dashboard
        nunca paga pelas outras seis.
        """
        page = self.pages.get(name)
        if page is not None:
            return page
        page_class = self._page_classes.get(name)
        if page_class is None:
            return None
        page = page_class(self.container, self.controller)
        self.pages[name] = page
        return page

    def show_page(self, name: str) -> None:
        if name == self._current_title:
            return
        page = self.page(name)
        if page is None:
            return
        # Uma unica pagina participa do layout. As demais mantem os widgets
        # e os rascunhos, mas nao podem aparecer nem receber cliques.
        self._safe(page.activate)
        if self.current_page is not None:
            self.current_page.grid_remove()
        if self._current_title:
            self._nav_buttons[self._current_title].configure(fg_color="transparent")
        self._nav_buttons[name].configure(fg_color="#245a8d")
        page.grid(row=0, column=0, sticky="nsew")
        self.current_page = page
        self._current_title = name

    # --------------------------------------------------------------- estado

    def _mark_dirty(self) -> None:
        """Chamado de qualquer thread; a atualizacao real ocorre no _tick."""
        self._dirty = True

    def _tick(self) -> None:
        if self._dirty:
            self._dirty = False
            self._refresh()
        self._tick_id = self.after(_REFRESH_MS, self._tick)

    def _refresh(self) -> None:
        controller = self.controller

        self.game_menu.set(controller.profile.game)
        names = [name for name in controller.profiles.names
                 if controller.profiles.get(name).game == controller.profile.game]
        if list(self.profile_menu.cget("values")) != names:
            self.profile_menu.configure(values=names)
        if self.profile_menu.get() != controller.profiles.active_name:
            self.profile_menu.set(controller.profiles.active_name)

        status = controller.status_text
        self.status_badge.configure(
            text=status,
            text_color=COLOR_OK
            if status == "ATIVO"
            else (COLOR_WARN if status.startswith("PAUSADO") else COLOR_ERROR),
        )

        mode = controller.mode
        self.mode_badge.configure(
            text=mode,
            text_color={MODE_OFFENSIVE: COLOR_ERROR, MODE_DEFENSIVE: COLOR_ACCENT}.get(
                mode, COLOR_MUTED
            ),
        )

        self.toggle_button.configure(
            text="DESATIVAR HOTKEYS" if controller.enabled else "ATIVAR HOTKEYS",
            fg_color="#8a3b44" if controller.enabled else "#245a8d",
            hover_color="#713037" if controller.enabled else "#1f4d78",
        )
        self.emergency_label.configure(
            text=f"Emergencia: {controller.settings.emergency_hotkey.upper()}"
        )

        if self.current_page is not None:
            self._safe(self.current_page.on_state_change)

    def _toggle_hotkeys(self) -> None:
        controller = self.controller
        if controller.enabled:
            controller.disable_hotkeys("botao")
            return
        try:
            result = controller.enable_hotkeys()
        except RuntimeError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        if result.has_problems:
            messagebox.showwarning(
                APP_TITLE,
                "Algumas hotkeys nao foram registradas:\n\n"
                + "\n".join(result.duplicates + result.invalid),
            )
        elif not result.registered:
            messagebox.showinfo(
                APP_TITLE, "Nenhuma hotkey configurada neste perfil ainda."
            )

    def _on_profile_selected(self, name: str) -> None:
        if name == self.controller.profiles.active_name:
            return
        try:
            self.controller.set_active_profile(name)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.controller.save_settings()
        if self.current_page is not None:
            self._safe(self.current_page.activate)

    def _on_game_selected(self, game: str) -> None:
        names = [name for name in self.controller.profiles.names
                 if self.controller.profiles.get(name).game == game]
        if names:
            self._on_profile_selected(names[0])
        self.game_menu.set(self.controller.profile.game)

    # ------------------------------------------------------------ ciclo vida

    def destroy(self) -> None:
        if self._tick_id is not None:
            self.after_cancel(self._tick_id)
            self._tick_id = None
        super().destroy()

    def _restore_geometry(self) -> None:
        window = self.controller.settings.window
        geometry = window.geometry()
        if window.x is not None and window.y is not None:
            left, top, right, bottom = _virtual_screen()
            off_screen = (
                window.x < left - 50
                or window.y < top - 50
                or window.x > right - 100
                or window.y > bottom - 100
            )
            if off_screen:
                geometry = f"{window.width}x{window.height}"
        self.geometry(geometry)
        if self.controller.settings.always_on_top:
            self.attributes("-topmost", True)

    def _store_geometry(self) -> None:
        window = self.controller.settings.window
        window.width = max(820, self.winfo_width())
        window.height = max(560, self.winfo_height())
        window.x = self.winfo_x()
        window.y = self.winfo_y()

    def on_close(self) -> None:
        if self.controller.combo.running and not messagebox.askyesno(
            APP_TITLE, "Ha um combo em execucao. Fechar mesmo assim?"
        ):
            return
        self._safe(self._store_geometry)
        self._safe(self.controller.shutdown)
        self.destroy()

    @staticmethod
    def _safe(func) -> None:
        """Executa uma callback de GUI sem deixar excecao derrubar a janela."""
        try:
            func()
        except Exception as exc:  # noqa: BLE001
            log.exception("Erro na interface: %s", exc)

    def report_callback_exception(self, exc_type, exc_value, exc_tb) -> None:
        """Manda erro de callback do Tk para o log.

        Por padrao o Tkinter imprime no stderr — que nao existe num build
        `--windowed`. O efeito era um botao simplesmente parar de responder,
        sem nenhum registro. Agora aparece em logs/app.log e na aba Logs.
        """
        log.error(
            "Erro na interface", exc_info=(exc_type, exc_value, exc_tb)
        )
