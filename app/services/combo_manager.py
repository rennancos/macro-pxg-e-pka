"""Execucao de macros (sequencias manuais) em thread separada.

Uma macro so comeca por um comando do usuario e sempre termina sozinha.
Nao existe repeticao automatica.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

from app.constants import STEP_CLICK, STEP_COMMAND, STEP_POINTER_HOME
from app.services.action_executor import ActionExecutor

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class MacroAction:
    """Uma etapa ja resolvida em tecla ou comando concreto."""

    label: str
    kind: str
    key: str = ""
    command: str = ""
    hold_ms: int = 0
    delay_ms: int = 0
    x: int = 0
    y: int = 0
    restore: bool = True
    # Alvo decidido na hora de clicar (a tela so mostra o desmaiado depois
    # da troca). None do resolvedor = sem alvo, a macro para ali.
    target: Callable[[], tuple[int, int] | None] | None = None


class ComboManager:
    """Roda no maximo uma macro por vez e cancela na hora via threading.Event."""

    def __init__(
        self,
        executor: ActionExecutor,
        on_step: Callable[[str], None] | None = None,
        on_finish: Callable[[str], None] | None = None,
    ) -> None:
        self._executor = executor
        self._on_step = on_step
        self._on_finish = on_finish
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._current = ""

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def current(self) -> str:
        return self._current if self.running else ""

    def start(self, actions: list[MacroAction], name: str = "Macro") -> bool:
        """Inicia a macro. Retorna False se ja houver uma em execucao."""
        if not actions:
            log.warning("%s ignorada: nenhuma etapa configurada", name)
            return False
        with self._lock:
            if self.running:
                log.warning(
                    "%s ignorada: '%s' ainda esta em execucao", name, self._current
                )
                return False
            self._cancel.clear()
            self._current = name
            self._thread = threading.Thread(
                target=self._run,
                args=(list(actions), name),
                name=f"macro-{name}",
                daemon=True,
            )
            self._thread.start()
        return True

    def cancel(self) -> bool:
        """Sinaliza o cancelamento; a espera entre etapas e interrompida."""
        if not self.running:
            return False
        log.info("Macro %s: cancelamento solicitado", self._current)
        self._cancel.set()
        return True

    def wait(self, timeout: float = 2.0) -> None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    # ---------------------------------------------------------------- interno

    def _run(self, actions: list[MacroAction], name: str) -> None:
        total = len(actions)
        finished = "concluida"
        started = time.perf_counter()
        log.info("Macro %s: inicio (%d etapas)", name, total)
        try:
            for index, action in enumerate(actions, start=1):
                if self._cancel.is_set():
                    log.info("Macro %s: cancelada antes da etapa %d/%d", name, index, total)
                    finished = "cancelada"
                    break
                log.info("Macro %s: etapa %d/%d iniciada: %s (tipo=%s)",
                         name, index, total, action.label, action.kind)
                step_started = time.perf_counter()
                if not self._execute(action):
                    log.error("Macro %s: etapa %d/%d falhou: %s", name, index, total, action.label)
                    finished = "interrompida por erro"
                    break
                self._notify_step(f"{action.label} ({index}/{total})")
                log.info("Macro %s: etapa %d/%d enviada em %.1f ms", name, index, total,
                         (time.perf_counter() - step_started) * 1000)
                if index < total:
                    log.info("Macro %s: espera de %d ms apos etapa %d/%d",
                             name, action.delay_ms, index, total)
                if index < total and self._cancel.wait(action.delay_ms / 1000.0):
                    log.info("Macro %s: espera interrompida por cancelamento", name)
                    finished = "cancelada"
                    break
        except Exception as exc:  # noqa: BLE001 - thread nunca derruba a app
            log.exception("Erro durante a macro %s: %s", name, exc)
            finished = "interrompida por erro"
        finally:
            # Erro ou cancelamento no meio: o ponteiro nao pode ficar no
            # retrato. Sem clique pendente, e um nada.
            self._executor.restore_pointer()
            log.info("Macro %s: %s (duracao %.1f ms)", name, finished,
                     (time.perf_counter() - started) * 1000)
            self._cancel.clear()
            self._current = ""
            if self._on_finish is not None:
                try:
                    self._on_finish(f"{name} {finished}")
                except Exception:  # noqa: BLE001
                    log.exception("Falha ao notificar o fim da macro")

    def _execute(self, action: MacroAction) -> bool:
        if action.kind == STEP_COMMAND:
            return self._executor.send_command(action.command)
        if action.kind == STEP_CLICK:
            x, y = action.x, action.y
            if action.target is not None:
                spot = action.target()
                if spot is None:
                    log.warning("%s: alvo nao encontrado na tela", action.label)
                    return False
                x, y = spot
            return self._executor.click(x, y, action.restore)
        if action.kind == STEP_POINTER_HOME:
            return self._executor.restore_pointer()
        return self._executor.tap(action.key, action.hold_ms)

    def _notify_step(self, label: str) -> None:
        if self._on_step is not None:
            try:
                self._on_step(label)
            except Exception:  # noqa: BLE001
                log.exception("Falha ao notificar etapa da macro")
