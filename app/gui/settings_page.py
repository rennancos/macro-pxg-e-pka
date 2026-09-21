"""Configuracoes globais do programa."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import filedialog

from app.constants import MAX_DELAY_MS
from app.gui.widgets import (
    COLOR_ERROR,
    COLOR_MUTED,
    BasePage,
    Card,
    HotkeyEntry,
    IntEntry,
)
from app.utils.paths import CONFIG_DIR, LOGS_DIR


class SettingsPage(BasePage):
    title = "Configuracoes"

    def build(self) -> None:
        ctk.CTkLabel(
            self, text="Configuracoes", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=14)

        game = Card(container, title="Jogo do perfil ativo")
        game.pack(fill="x", pady=6)
        self.game_label = ctk.CTkLabel(game, text="")
        self.game_label.pack(anchor="w", padx=16)
        self.client_executable = ctk.CTkEntry(game, placeholder_text="Selecione o executavel do cliente do jogo", width=430)
        self.client_executable.pack(anchor="w", padx=16, pady=6)
        ctk.CTkButton(game, text="Selecionar executavel", command=self._choose_client).pack(anchor="w", padx=16, pady=(0, 12))

        chat = Card(container, title="Chat do jogo")
        chat.pack(fill="x", pady=6)
        grid = ctk.CTkFrame(chat, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(grid, text="Abrir chat", anchor="w", width=150).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.chat_key = HotkeyEntry(grid, self.controller, width=140)
        self.chat_key.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(grid, text="Confirmar (enviar)", anchor="w", width=150).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.confirm_key = HotkeyEntry(grid, self.controller, width=140)
        self.confirm_key.grid(row=1, column=1, sticky="w")

        ctk.CTkLabel(grid, text="Fechar chat", anchor="w", width=150).grid(
            row=5, column=0, sticky="w", pady=4
        )
        self.close_key = HotkeyEntry(grid, self.controller, width=140)
        self.close_key.grid(row=5, column=1, sticky="w")
        ctk.CTkLabel(
            grid,
            text="enviada apos cada comando, para a proxima etapa nao virar texto",
            text_color=COLOR_MUTED,
        ).grid(row=5, column=2, sticky="w", padx=(10, 0))

        ctk.CTkLabel(grid, text="Pausa antes de fechar (ms)", anchor="w", width=150).grid(
            row=6, column=0, sticky="w", pady=4
        )
        self.close_pause = IntEntry(grid, minimum=0, maximum=MAX_DELAY_MS, width=80)
        self.close_pause.grid(row=6, column=1, sticky="w")

        ctk.CTkLabel(grid, text="Digitacao (ms/tecla)", anchor="w", width=150).grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.type_delay = IntEntry(grid, minimum=0, maximum=500, width=80)
        self.type_delay.grid(row=2, column=1, sticky="w")

        ctk.CTkLabel(grid, text="Pausa apos abrir (ms)", anchor="w", width=150).grid(
            row=3, column=0, sticky="w", pady=4
        )
        self.open_pause = IntEntry(grid, minimum=0, maximum=MAX_DELAY_MS, width=80)
        self.open_pause.grid(row=3, column=1, sticky="w")

        ctk.CTkLabel(grid, text="Pausa antes de enviar (ms)", anchor="w", width=150).grid(
            row=4, column=0, sticky="w", pady=4
        )
        self.send_pause = IntEntry(grid, minimum=0, maximum=MAX_DELAY_MS, width=80)
        self.send_pause.grid(row=4, column=1, sticky="w")

        safety = Card(container, title="Seguranca e comportamento")
        safety.pack(fill="x", pady=6)
        safety_body = ctk.CTkFrame(safety, fg_color="transparent")
        safety_body.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(safety_body, text="Parada de emergencia", anchor="w", width=150).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.emergency = HotkeyEntry(safety_body, self.controller, width=140)
        self.emergency.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(safety_body, text="Cancelar macro", anchor="w", width=150).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.cancel_hotkey = HotkeyEntry(safety_body, self.controller, width=140)
        self.cancel_hotkey.grid(row=1, column=1, sticky="w")

        ctk.CTkLabel(
            safety_body, text="Trava da roda (ms)", anchor="w", width=150
        ).grid(row=2, column=0, sticky="w", pady=4)
        self.wheel_debounce = IntEntry(safety_body, minimum=0, maximum=5000, width=80)
        self.wheel_debounce.grid(row=2, column=1, sticky="w")
        ctk.CTkLabel(
            safety_body,
            text="um giro da roda gera varios eventos; so o primeiro dispara",
            text_color=COLOR_MUTED,
        ).grid(row=2, column=2, sticky="w", padx=(10, 0))

        self.require_focus = ctk.CTkCheckBox(
            safety_body,
            text="So executar com o jogo do perfil em primeiro plano (recomendado)",
        )
        self.require_focus.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 2))

        self.suppress = ctk.CTkCheckBox(
            safety_body,
            text="Bloquear a tecla da hotkey para o jogo (nao vale para a roda)",
        )
        self.suppress.grid(row=4, column=0, columnspan=3, sticky="w", pady=2)

        self.autostart = ctk.CTkCheckBox(
            safety_body, text="Ativar hotkeys automaticamente ao abrir o programa"
        )
        self.autostart.grid(row=5, column=0, columnspan=3, sticky="w", pady=2)

        self.always_on_top = ctk.CTkCheckBox(
            safety_body, text="Manter janela sempre visivel", command=self._apply_topmost
        )
        self.always_on_top.grid(row=6, column=0, columnspan=3, sticky="w", pady=2)

        appearance = Card(container, title="Aparencia")
        appearance.pack(fill="x", pady=6)
        self.appearance = ctk.CTkSegmentedButton(
            appearance, values=["dark", "light", "system"], command=self._apply_appearance
        )
        self.appearance.pack(anchor="w", padx=16, pady=(0, 14))

        paths = Card(container, title="Pastas")
        paths.pack(fill="x", pady=6)
        ctk.CTkLabel(
            paths,
            text=f"Configuracao: {CONFIG_DIR}\nLogs: {LOGS_DIR}",
            text_color=COLOR_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 14))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(buttons, text="Salvar configuracoes", command=self.save).pack(side="left")
        ctk.CTkButton(
            buttons, text="Descartar alteracoes", fg_color="gray30", command=self.on_show
        ).pack(side="left", padx=8)

    # ----------------------------------------------------------------- dados

    def on_show(self) -> None:
        settings = self.controller.settings
        self.game_label.configure(text=f"{self.controller.profile.game} — configuracoes independentes por jogo")
        self.client_executable.delete(0, "end")
        self.client_executable.insert(0, settings.client_executable)
        self.chat_key.set_value(settings.chat_key)
        self.confirm_key.set_value(settings.chat_confirm_key)
        self.close_key.set_value(settings.chat_close_key)
        self.close_pause.set_value(settings.chat_close_pause_ms)
        self.type_delay.set_value(settings.type_delay_ms)
        self.open_pause.set_value(settings.chat_open_pause_ms)
        self.send_pause.set_value(settings.chat_send_pause_ms)
        self.emergency.set_value(settings.emergency_hotkey)
        self.cancel_hotkey.set_value(settings.cancel_hotkey)
        self.wheel_debounce.set_value(settings.wheel_debounce_ms)
        self._set_check(self.require_focus, settings.require_game_focus)
        self._set_check(self.suppress, settings.suppress_hotkeys)
        self._set_check(self.autostart, settings.autostart_hotkeys)
        self._set_check(self.always_on_top, settings.always_on_top)
        self.appearance.set(settings.appearance)

    def save(self) -> None:
        settings = self.controller.settings
        settings.client_executable = self.client_executable.get().strip()
        settings.chat_key = self.chat_key.get_value()
        settings.chat_confirm_key = self.confirm_key.get_value() or "enter"
        settings.chat_close_key = self.close_key.get_value()
        settings.chat_close_pause_ms = self.close_pause.get_value(
            settings.chat_close_pause_ms
        )
        settings.type_delay_ms = self.type_delay.get_value(settings.type_delay_ms)
        settings.chat_open_pause_ms = self.open_pause.get_value(settings.chat_open_pause_ms)
        settings.chat_send_pause_ms = self.send_pause.get_value(settings.chat_send_pause_ms)
        settings.cancel_hotkey = self.cancel_hotkey.get_value()
        settings.wheel_debounce_ms = self.wheel_debounce.get_value(
            settings.wheel_debounce_ms
        )
        settings.require_game_focus = bool(self.require_focus.get())
        settings.suppress_hotkeys = bool(self.suppress.get())
        settings.autostart_hotkeys = bool(self.autostart.get())
        settings.always_on_top = bool(self.always_on_top.get())
        settings.appearance = self.appearance.get()

        new_emergency = self.emergency.get_value()
        emergency_changed = new_emergency != settings.emergency_hotkey
        if new_emergency:
            settings.emergency_hotkey = new_emergency

        if not self.controller.save_settings():
            self.notify("Falha ao salvar as configuracoes - veja os logs.", COLOR_ERROR)
            return

        if emergency_changed and not self.controller.setup_emergency():
            self.notify("Hotkey de emergencia invalida - verifique o valor.", COLOR_ERROR)
            return

        self.controller.refresh_bindings()
        self.notify("Configuracoes salvas.")
        self.on_show()

    # ---------------------------------------------------------------- visual

    def _choose_client(self) -> None:
        path = filedialog.askopenfilename(title="Selecione o cliente do jogo (nao o launcher)", filetypes=[("Executavel", "*.exe")])
        if path:
            self.client_executable.delete(0, "end")
            self.client_executable.insert(0, path)

    def _apply_appearance(self, value: str) -> None:
        ctk.set_appearance_mode(value)

    def _apply_topmost(self) -> None:
        window = self.winfo_toplevel()
        try:
            window.attributes("-topmost", bool(self.always_on_top.get()))
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _set_check(box: ctk.CTkCheckBox, value: bool) -> None:
        if value:
            box.select()
        else:
            box.deselect()
