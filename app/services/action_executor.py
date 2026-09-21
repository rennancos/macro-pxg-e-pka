"""Execucao das acoes de teclado (unico ponto que "digita" no jogo)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.models.profile import ActionConfig
from app.models.settings import Settings
from app.constants import ACTION_MODE_COMMAND, CLICK_SETTLE_MS
from app.services.hotkey_manager import keyboard_module
from app.services.wheel_manager import mouse_module

log = logging.getLogger(__name__)


def _sleep_ms(milliseconds: int) -> None:
    if milliseconds > 0:
        time.sleep(milliseconds / 1000.0)


class ActionExecutor:
    """Envia teclas/comandos.

    Um lock serializa os envios: duas acoes nunca digitam ao mesmo tempo.
    `busy` e consultado pelo controller para descartar disparos concorrentes
    (inclusive os causados pelas proprias teclas que enviamos).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._pointer_home: tuple[int, int] | None = None

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    # ------------------------------------------------------------------ teclas

    def tap(self, key: str, hold_ms: int) -> bool:
        """Pressiona e solta uma tecla, respeitando o intervalo configurado."""
        key = (key or "").strip()
        if not key:
            log.warning("Acao ignorada: nenhuma tecla configurada")
            return False
        keyboard = keyboard_module()
        with self._lock:
            try:
                keyboard.press(key)
                _sleep_ms(max(0, hold_ms))
                keyboard.release(key)
                return True
            except Exception as exc:  # noqa: BLE001
                log.error("Falha ao enviar a tecla %r: %s", key, exc)
                try:
                    keyboard.release(key)
                except Exception:  # noqa: BLE001
                    pass
                return False

    def click(self, x: int, y: int, restore: bool = True) -> bool:
        """Clica com o botao esquerdo em (x, y).

        `restore=False` DEIXA o ponteiro em cima do alvo e guarda de onde ele
        veio, para `restore_pointer()` devolver depois. Isso existe porque o
        revive do cliente se aplica ao que esta sob o cursor: devolver o
        ponteiro antes da tecla fazia o revive cair no vazio.

        O clique sai pelo mesmo lock das teclas, entao nunca acontece no meio
        de uma sequencia de teclado. O nosso proprio hook de mouse ve este
        clique, mas botao esquerdo nao e gatilho de nada — nao ha realimentacao.
        """
        mouse = mouse_module()
        with self._lock:
            try:
                home = mouse.get_position()
                mouse.move(x, y)
                _sleep_ms(CLICK_SETTLE_MS)
                mouse.click()
                _sleep_ms(CLICK_SETTLE_MS)
                if restore:
                    mouse.move(*home)
                else:
                    self._pointer_home = home
                return True
            except Exception as exc:  # noqa: BLE001
                log.error("Falha ao clicar em (%d, %d): %s", x, y, exc)
                return False

    def restore_pointer(self) -> bool:
        """Devolve o ponteiro para onde ele estava antes do ultimo clique.

        Sem isto o mouse do usuario ficaria parado sobre a barra do time
        depois de cada rotacao.
        """
        home, self._pointer_home = self._pointer_home, None
        if home is None:
            return True
        with self._lock:
            try:
                mouse_module().move(*home)
                return True
            except Exception as exc:  # noqa: BLE001
                log.error("Falha ao devolver o ponteiro: %s", exc)
                return False

    def send_command(self, command: str) -> bool:
        """Abre o chat, digita o comando, confirma e devolve o chat ao normal.

        O passo final importa: se o cliente deixar o campo de chat com o foco,
        a proxima etapa da macro vira texto digitado. Uma tecla de item como
        `q` viraria a letra "q" no chat, e o Enter seguinte publicaria isso
        como mensagem.
        """
        command = (command or "").strip()
        if not command:
            log.warning("Acao ignorada: nenhum comando configurado")
            return False
        settings = self._settings
        keyboard = keyboard_module()
        with self._lock:
            try:
                if settings.chat_key.strip():
                    keyboard.send(settings.chat_key.strip())
                    _sleep_ms(settings.chat_open_pause_ms)
                keyboard.write(command, delay=settings.type_delay_ms / 1000.0)
                _sleep_ms(settings.chat_send_pause_ms)
                keyboard.send(settings.chat_confirm_key.strip() or "enter")
                self._close_chat(keyboard, settings)
                return True
            except Exception as exc:  # noqa: BLE001
                log.error("Falha ao enviar o comando %r: %s", command, exc)
                # Mesmo com falha, tenta tirar o foco do chat: deixar o campo
                # aberto faria a proxima etapa digitar dentro dele.
                try:
                    self._close_chat(keyboard, settings)
                except Exception:  # noqa: BLE001
                    pass
                return False

    @staticmethod
    def _close_chat(keyboard: Any, settings: Settings) -> None:
        close_key = settings.chat_close_key.strip()
        if not close_key:
            return
        _sleep_ms(settings.chat_close_pause_ms)
        keyboard.send(close_key)

    def run_action(self, action: ActionConfig) -> bool:
        """Executa uma acao conforme o modo configurado (tecla ou comando)."""
        if not action.is_runnable():
            log.warning("%s ignorado: configuracao incompleta", action.label)
            return False
        if action.mode == ACTION_MODE_COMMAND:
            return self.send_command(action.command)
        return self.tap(action.key, action.hold_ms)
