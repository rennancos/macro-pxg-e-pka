"""Editor de macros: sequencias manuais de skills, teclas e comandos."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from app.constants import (
    DEFAULT_STEP_DELAY_MS,
    MAX_DELAY_MS,
    MAX_MACROS,
    MIN_STEP_DELAY_MS,
    STEP_COMMAND,
    STEP_KEY,
    STEP_LABELS,
    STEP_SKILL,
    MOUSE_LABELS,
    MOUSE_SHORT_LABELS,
    MOUSE_TRIGGERS,
    WHEEL_DOWN,
)
from app.gui.widgets import (
    COLOR_ERROR,
    COLOR_MUTED,
    COLOR_WARN,
    BasePage,
    Card,
    HotkeyEntry,
    IntEntry,
)
from app.models.profile import Macro, MacroStep

_TRIGGER_KEYBOARD = "Teclado"
_TRIGGER_MOUSE = "Mouse"
# Rotulo mostrado no menu -> gatilho gravado no perfil.
_MOUSE_CHOICES = {MOUSE_SHORT_LABELS[t]: t for t in MOUSE_TRIGGERS}
_STEP_LABEL_TO_TYPE = {label: kind for kind, label in STEP_LABELS.items()}


class ComboPage(BasePage):
    title = "Combo"

    def build(self) -> None:
        self._macros: list[Macro] = []
        self._selected = 0
        self._step_widgets: list[dict] = []
        # indice do macro -> (assinatura das etapas, quadro pronto, widgets)
        self._step_cache: dict[int, tuple[tuple, ctk.CTkFrame, list[dict]]] = {}
        self._shown_steps: ctk.CTkFrame | None = None

        ctk.CTkLabel(
            self, text="Macros", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text=(
                "Cada macro so comeca quando voce aciona o gatilho, executa uma vez "
                "e termina. Nao existe repeticao automatica."
            ),
            text_color=COLOR_MUTED,
            anchor="w",
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # ------------------------------------------------------ lista lateral
        left = Card(body, title="Macros")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        self.macro_list = ctk.CTkScrollableFrame(left, width=190, fg_color="transparent")
        self.macro_list.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        list_buttons = ctk.CTkFrame(left, fg_color="transparent")
        list_buttons.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkButton(list_buttons, text="+ Nova", width=85, command=self._add_macro).pack(
            side="left"
        )
        ctk.CTkButton(
            list_buttons, text="Remover", width=85, fg_color="#8a3b44",
            hover_color="#713037", command=self._remove_macro,
        ).pack(side="right")

        # ----------------------------------------------------- editor direita
        right = Card(body, title="")
        right.grid(row=0, column=1, sticky="nsew")

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(header, text="Nome", width=70, anchor="w").grid(row=0, column=0, sticky="w")
        self.name_entry = ctk.CTkEntry(header, width=200)
        self.name_entry.grid(row=0, column=1, sticky="w")
        self.enabled_box = ctk.CTkCheckBox(header, text="Ativa")
        self.enabled_box.grid(row=0, column=2, sticky="w", padx=(16, 0))

        ctk.CTkLabel(header, text="Gatilho", width=70, anchor="w").grid(
            row=1, column=0, sticky="w", pady=(10, 0)
        )
        self.trigger_kind = ctk.CTkSegmentedButton(
            header,
            values=[_TRIGGER_KEYBOARD, _TRIGGER_MOUSE],
            command=self._on_trigger_kind,
        )
        self.trigger_kind.grid(row=1, column=1, columnspan=2, sticky="w", pady=(10, 0))

        self.hotkey = HotkeyEntry(header, self.controller, width=140)
        self.hotkey.grid(row=2, column=1, columnspan=2, sticky="w", pady=(6, 0))

        self.mouse_menu = ctk.CTkOptionMenu(header, values=list(_MOUSE_CHOICES), width=180)
        self.mouse_menu.grid(row=3, column=1, columnspan=2, sticky="w", pady=(6, 0))
        ctk.CTkLabel(
            header,
            text=("Esquerdo e direito nao entram: o clique tambem chega ao jogo, "
                  "entao o macro dispararia em cada clique."),
            wraplength=320,
            text_color=COLOR_MUTED,
            justify="left",
        ).grid(row=4, column=1, columnspan=2, sticky="w", pady=(2, 0))

        # O painel mora num suporte que fica SEMPRE empacotado, criado antes
        # da lista de etapas. Assim mostrar/esconder o painel nao precisa de
        # `before=steps_frame` — que nunca funcionou: CTkScrollableFrame
        # empacota um frame interno, entao o widget referenciado nao e o que
        # esta sob o pack, e o Tk respondia "isn't packed".
        self._rotation_holder = ctk.CTkFrame(right, fg_color="transparent")
        self._rotation_holder.pack(fill="x")
        self.rotation_panel = ctk.CTkFrame(self._rotation_holder)
        self.rotation_panel.pack(fill="x", padx=16, pady=(4, 4))
        self.rotation_info = ctk.CTkLabel(
            self.rotation_panel, text="", anchor="w", justify="left", wraplength=530,
        )
        self.rotation_info.pack(fill="x", padx=10, pady=(8, 4))
        sync_row = ctk.CTkFrame(self.rotation_panel, fg_color="transparent")
        sync_row.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(sync_row, text="Pokémon atual:").pack(side="left")
        self.rotation_slot = ctk.CTkOptionMenu(
            sync_row, values=[str(n) for n in range(1, 7)], width=65,
        )
        self.rotation_slot.pack(side="left", padx=8)
        ctk.CTkButton(
            sync_row, text="Sincronizar", width=110, command=self._sync_rotation_slot,
        ).pack(side="left")

        self.steps_frame = ctk.CTkScrollableFrame(right, label_text="Etapas")
        self.steps_frame.pack(fill="both", expand=True, padx=16, pady=(10, 6))

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(buttons, text="+ Etapa", width=95, command=self._add_step).pack(side="left")
        ctk.CTkButton(buttons, text="Salvar", width=95, command=self.save).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            buttons, text="Descartar", width=95, fg_color="gray30", command=self.discard
        ).pack(side="left")
        execution = ctk.CTkFrame(right, fg_color="transparent")
        execution.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(
            execution, text="Cancelar execucao", fg_color="#8a3b44",
            hover_color="#713037", command=self._cancel_now,
        ).pack(side="right")
        ctk.CTkButton(
            execution, text="Executar agora", fg_color="#2f7d4f",
            hover_color="#27673f", command=self._run_now,
        ).pack(side="right", padx=8)

    # ------------------------------------------------------------------ dados

    def discard(self) -> None:
        """Botao Descartar: joga fora o que esta nos widgets e redesenha.

        Separado do on_show porque o on_show da troca de aba reaproveita as
        etapas ja desenhadas; aqui a intencao e justamente perder o que o
        usuario digitou e nao salvou.
        """
        # Os widgets guardados ainda tem o que o usuario digitou e nao salvou;
        # descartar so tem efeito se eles forem embora junto.
        self._drop_step_frames(list(self._step_cache))
        self.on_show()

    def on_show(self) -> None:
        profile = self.controller.profile
        self._macros = [Macro.from_dict(m.to_dict()) for m in profile.macros]
        if not self._macros:
            self._macros = [Macro(name="Macro 1")]
        self._selected = min(self._selected, len(self._macros) - 1)
        # Quadros de macros que nao existem mais (perfil trocado, macro
        # apagado) so ocupariam memoria. O resto continua valendo: se a
        # assinatura bater, a aba reabre sem remontar nada.
        self._drop_step_frames(
            [i for i in self._step_cache if i >= len(self._macros)]
        )
        self._render_list()
        self._load_selected()

    def save(self) -> None:
        self._collect()
        profile = self.controller.profile
        profile.macros = [Macro.from_dict(m.to_dict()) for m in self._macros]

        if not self.controller.save_profile():
            self.notify("Falha ao salvar o perfil - veja os logs.", COLOR_ERROR)
            return
        problems = self.controller.preview_conflicts()
        if problems:
            self.notify("Salvo, mas com problemas: " + "; ".join(problems), COLOR_ERROR)
        else:
            self.notify("Macros salvas.")
        self.on_show()

    @property
    def _current(self) -> Macro:
        return self._macros[self._selected]

    def _collect(self) -> None:
        """Le os widgets para o objeto em memoria antes de redesenhar."""
        if not self._macros:
            return
        macro = self._current
        macro.name = self.name_entry.get().strip() or f"Macro {self._selected + 1}"
        macro.enabled = bool(self.enabled_box.get())

        if self.trigger_kind.get() == _TRIGGER_MOUSE:
            macro.hotkey = _MOUSE_CHOICES.get(self.mouse_menu.get(), WHEEL_DOWN)
        else:
            macro.hotkey = self.hotkey.get_value()

        for index, widgets in enumerate(self._step_widgets):
            if index >= len(macro.steps):
                break
            step = macro.steps[index]
            step.delay_ms = widgets["delay"].get_value(step.delay_ms)

            # Ler pelos widgets que EXISTEM na linha, nunca pelo tipo escolhido
            # no menu: ao trocar de tipo, a linha ainda mostra os campos do tipo
            # anterior. Guardar os tres campos tambem preserva o que ja estava
            # preenchido quando o usuario vai e volta entre os tipos.
            if "skill" in widgets:
                step.skill = self._skill_number(widgets["skill"].get())
            if "key" in widgets:
                step.key = widgets["key"].get_value()
            if "command" in widgets:
                step.command = widgets["command"].get().strip()

            step.type = _STEP_LABEL_TO_TYPE.get(widgets["type"].get(), step.type)

    # --------------------------------------------------------------- desenho

    def _render_list(self) -> None:
        for widget in self.macro_list.winfo_children():
            widget.destroy()
        for index, macro in enumerate(self._macros):
            trigger = MOUSE_LABELS.get(macro.hotkey, macro.hotkey or "sem gatilho")
            mark = "↻ " if macro.rotation else ("" if macro.enabled else "(off) ")
            ctk.CTkButton(
                self.macro_list,
                text=f"{mark}{macro.name}\n{trigger}",
                anchor="w",
                height=46,
                fg_color="#245a8d" if index == self._selected else "gray25",
                hover_color="#1f4d78",
                command=lambda i=index: self._select(i),
            ).pack(fill="x", pady=3)

    def _load_selected(self) -> None:
        macro = self._current
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, macro.name)
        if macro.enabled:
            self.enabled_box.select()
        else:
            self.enabled_box.deselect()

        if macro.hotkey in MOUSE_TRIGGERS:
            self.trigger_kind.set(_TRIGGER_MOUSE)
            self.mouse_menu.set(MOUSE_SHORT_LABELS[macro.hotkey])
        else:
            self.trigger_kind.set(_TRIGGER_KEYBOARD)
            self.hotkey.set_value(macro.hotkey)
        self._on_trigger_kind(self.trigger_kind.get())
        self._show_rotation_panel(macro)
        self._render_steps()

    def _show_rotation_panel(self, macro: Macro) -> None:
        if not macro.rotation:
            self.rotation_panel.pack_forget()
            return
        slot = self.controller.active_pokemon_slot
        if slot is not None:
            self.rotation_slot.set(str(slot))
        delay = macro.steps[0].delay_ms if macro.steps else 0
        key = macro.steps[0].key if macro.steps else "(vazia)"
        self.rotation_info.configure(text=(
            f"Rotação: puxa o próximo Pokémon (Ctrl+1 a Ctrl+6) → espera "
            f"{delay} ms → {key.upper()} para revivê-lo. "
            "Sincronize o slot antes do primeiro giro. "
            f"Slot acompanhado: {slot if slot is not None else 'desconhecido'}."
        ))
        self.rotation_panel.pack(fill="x", padx=16, pady=(4, 4))

    def _sync_rotation_slot(self) -> None:
        slot = int(self.rotation_slot.get())
        self.controller.set_pokemon_slot(slot)
        self._show_rotation_panel(self._current)
        self.notify(f"Pokémon {slot} definido como ativo.")

    def _on_trigger_kind(self, value: str) -> None:
        keyboard = value == _TRIGGER_KEYBOARD
        state = "normal" if keyboard else "disabled"
        self.hotkey.entry.configure(state=state)
        self.hotkey.button.configure(state=state)
        self.mouse_menu.configure(state="disabled" if keyboard else "normal")
        if not keyboard:
            self.hotkey.set_value("")

    def _skill_names(self) -> list[str]:
        return [
            f"{i}. {skill.name}"
            for i, skill in enumerate(self.controller.profile.skills, start=1)
        ]

    @staticmethod
    def _skill_number(label: str) -> int:
        try:
            return int(label.split(".", 1)[0])
        except (ValueError, AttributeError):
            return 1

    def _render_steps(self) -> None:
        """Mostra as etapas do macro atual, reaproveitando o que ja foi montado.

        Cada etapa custa ~8 widgets do CustomTkinter, e cada widget custa
        centenas de idas ao Tcl: montar um macro de 11 etapas passava de dois
        segundos. Por isso cada macro guarda o seu proprio quadro de etapas —
        trocar de macro vira esconder um e mostrar o outro.

        O quadro so entra na tela DEPOIS de montado: enquanto esta solto, o
        frame rolavel nao recalcula a barra a cada widget inserido.
        """
        macro = self._current
        signature = (
            tuple(
                (step.type, step.skill, step.key, step.command, step.delay_ms)
                for step in macro.steps
            ),
            tuple(self._skill_names()),
        )

        cached = self._step_cache.get(self._selected)
        if cached is not None and cached[0] == signature:
            self._show_step_frame(cached[1])
            self._step_widgets = cached[2]
            return

        stale = self._step_cache.pop(self._selected, None)
        if stale is not None:
            stale[1].destroy()

        container = ctk.CTkFrame(self.steps_frame, fg_color="transparent")
        self._step_widgets = []

        if not macro.steps:
            ctk.CTkLabel(
                container,
                text="Nenhuma etapa. Use + Etapa para montar a sequencia.",
                text_color=COLOR_MUTED,
            ).pack(anchor="w", padx=8, pady=8)
        else:
            self._build_step_rows(container, macro)

        self._show_step_frame(container)
        self._step_cache[self._selected] = (signature, container, self._step_widgets)

    def _drop_step_frames(self, indexes: list[int]) -> None:
        """Destroi os quadros guardados nesses indices."""
        for index in indexes:
            entry = self._step_cache.pop(index, None)
            if entry is None:
                continue
            if entry[1] is self._shown_steps:
                self._shown_steps = None
            entry[1].destroy()

    def _show_step_frame(self, container: ctk.CTkFrame) -> None:
        if container is self._shown_steps:
            return
        if self._shown_steps is not None:
            self._shown_steps.pack_forget()
        container.pack(fill="both", expand=True)
        self._shown_steps = container

    def _build_step_rows(self, container: ctk.CTkFrame, macro: Macro) -> None:
        names = self._skill_names()
        for index, step in enumerate(macro.steps):
            card = ctk.CTkFrame(container)
            card.pack(fill="x", pady=3, padx=4)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x")
            controls = ctk.CTkFrame(card, fg_color="transparent")
            controls.pack(fill="x", padx=8, pady=(0, 6))

            ctk.CTkLabel(row, text=f"{index + 1:02d}", width=26).pack(side="left", padx=(8, 4))

            type_menu = ctk.CTkOptionMenu(
                row,
                values=list(STEP_LABELS.values()),
                width=110,
                command=lambda _v, i=index: self._on_step_type(i),
            )
            type_menu.set(STEP_LABELS.get(step.type, STEP_LABELS[STEP_SKILL]))
            type_menu.pack(side="left", padx=4, pady=6)

            payload = ctk.CTkFrame(row, fg_color="transparent")
            payload.pack(side="left", padx=6)

            widgets: dict = {"type": type_menu}
            if step.type == STEP_SKILL:
                menu = ctk.CTkOptionMenu(payload, values=names, width=170)
                menu.set(names[min(step.skill, len(names)) - 1])
                menu.pack(side="left")
                widgets["skill"] = menu
            elif step.type == STEP_KEY:
                entry = HotkeyEntry(payload, self.controller, value=step.key, width=110)
                entry.pack(side="left")
                widgets["key"] = entry
            else:
                entry = ctk.CTkEntry(payload, width=180, placeholder_text="Comando")
                entry.insert(0, step.command)
                entry.pack(side="left")
                widgets["command"] = entry

            ctk.CTkLabel(controls, text="Esperar").pack(side="left", padx=(0, 4))
            delay = IntEntry(
                controls, value=step.delay_ms, minimum=0, maximum=MAX_DELAY_MS, width=70
            )
            delay.pack(side="left")
            widgets["delay"] = delay
            ctk.CTkLabel(controls, text="ms").pack(side="left", padx=(4, 8))

            ctk.CTkButton(
                controls, text="X", width=30, fg_color="#8a3b44",
                command=lambda i=index: self._remove_step(i),
            ).pack(side="right", padx=(4, 8))
            ctk.CTkButton(
                controls, text="v", width=30, fg_color="gray30",
                command=lambda i=index: self._move_step(i, 1),
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                controls, text="^", width=30, fg_color="gray30",
                command=lambda i=index: self._move_step(i, -1),
            ).pack(side="right", padx=2)

            self._step_widgets.append(widgets)

    # ---------------------------------------------------------------- acoes

    def _select(self, index: int) -> None:
        self._collect()
        self._selected = index
        self._render_list()
        self._load_selected()

    def _add_macro(self) -> None:
        self._collect()
        if len(self._macros) >= MAX_MACROS:
            self.notify(f"Limite de {MAX_MACROS} macros por perfil.", COLOR_WARN)
            return
        self._macros.append(Macro(name=f"Macro {len(self._macros) + 1}"))
        self._selected = len(self._macros) - 1
        self._render_list()
        self._load_selected()

    def _remove_macro(self) -> None:
        if len(self._macros) <= 1:
            self.notify("E preciso manter pelo menos uma macro.", COLOR_WARN)
            return
        del self._macros[self._selected]
        self._selected = max(0, self._selected - 1)
        self._render_list()
        self._load_selected()

    def _on_step_type(self, index: int) -> None:
        """Troca o tipo da etapa e redesenha os campos correspondentes."""
        del index  # _collect ja le o menu de todas as linhas
        self._collect()
        self._render_steps()

    def _add_step(self) -> None:
        self._collect()
        self._current.steps.append(
            MacroStep(type=STEP_SKILL, skill=1, delay_ms=DEFAULT_STEP_DELAY_MS)
        )
        self._render_steps()

    def _remove_step(self, index: int) -> None:
        self._collect()
        steps = self._current.steps
        if 0 <= index < len(steps):
            del steps[index]
        self._render_steps()

    def _move_step(self, index: int, offset: int) -> None:
        self._collect()
        steps = self._current.steps
        target = index + offset
        if 0 <= index < len(steps) and 0 <= target < len(steps):
            steps[index], steps[target] = steps[target], steps[index]
        self._render_steps()

    def _run_now(self) -> None:
        """Execucao manual, disparada por este botao (nunca automatica)."""
        self._collect()
        name = self._current.name
        if self.controller.profile.macro(name) is None:
            self.notify("Salve a macro antes de executar.", COLOR_WARN)
            return
        if self.controller.start_macro(name):
            self.notify(f"{name} iniciada.")
        else:
            self.notify("Nao foi possivel iniciar (veja os logs).", COLOR_WARN)

    def _cancel_now(self) -> None:
        if self.controller.cancel_combo():
            self.notify("Macro cancelada.", COLOR_WARN)
        else:
            self.notify("Nenhuma macro em execucao.", COLOR_MUTED)
