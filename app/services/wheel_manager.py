"""Gatilhos pelo mouse: roda e botoes que nao sao o esquerdo/direito.

A biblioteca `keyboard` nao enxerga o mouse, entao isto vem da `mouse`.
Um giro fisico gera varios eventos; o debounce garante uma execucao por giro.
O mesmo debounce cobre os botoes contra repique do firmware.

Atencao: este hook NAO suprime o evento — a rolagem e o clique tambem chegam
ao jogo. Por isso esquerdo e direito nao sao oferecidos como gatilho.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from app.constants import MOUSE_MIDDLE, MOUSE_TRIGGERS, MOUSE_X1, MOUSE_X2, WHEEL_DOWN, WHEEL_UP

log = logging.getLogger(__name__)

try:
    import mouse as _mouse
except Exception as exc:  # noqa: BLE001 - a lib pode faltar no ambiente
    _mouse = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

MOUSE_AVAILABLE = _mouse is not None


def mouse_module() -> Any:
    """Devolve o modulo `mouse` ou levanta erro legivel. Ponto unico de acesso."""
    if _mouse is None:
        raise RuntimeError(
            "A biblioteca 'mouse' nao esta disponivel "
            f"({_IMPORT_ERROR}). Instale com: pip install mouse"
        )
    return _mouse


# Nomes de botao da lib `mouse` -> gatilho nosso. O que nao esta aqui
# (esquerdo, direito) e ignorado de proposito.
_BUTTON_TRIGGERS = {"middle": MOUSE_MIDDLE, "x": MOUSE_X1, "x2": MOUSE_X2}


def read_click(timeout: float = 25.0) -> tuple[int, int] | None:
    """Bloqueia ate o proximo clique esquerdo e devolve a posicao na tela.

    Usado so pelo botao de gravar a posicao dos retratos do time. Nao registra
    nada em log alem da posicao final: nao existe captura de mouse continua.
    """
    mouse = mouse_module()
    done = threading.Event()
    spot: list[tuple[int, int]] = []

    def on_event(event: object) -> None:
        if not isinstance(event, mouse.ButtonEvent):
            return
        if getattr(event, "button", "") != "left":
            return
        if getattr(event, "event_type", "") not in ("down", "double"):
            return
        spot.append(mouse.get_position())
        done.set()

    hook = mouse.hook(on_event)
    try:
        done.wait(timeout)
    finally:
        try:
            mouse.unhook(hook)
        except Exception:  # noqa: BLE001 - hook ja removido
            pass
    return spot[0] if spot else None


class WheelManager:
    """Registra callbacks para a roda e para os botoes extras do mouse."""

    def __init__(self, debounce_ms: Callable[[], int]) -> None:
        self._debounce_ms = debounce_ms
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._last_fired: dict[str, float] = {}
        self._hook: Callable | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return MOUSE_AVAILABLE

    @property
    def unavailable_reason(self) -> str:
        if MOUSE_AVAILABLE:
            return ""
        return (
            f"A biblioteca 'mouse' nao esta disponivel ({_IMPORT_ERROR}). "
            "Instale com: pip install mouse"
        )

    @property
    def active_triggers(self) -> list[str]:
        with self._lock:
            return sorted(self._callbacks)

    def bind(self, callbacks: dict[str, Callable[[], None]]) -> bool:
        """Substitui os gatilhos da roda. Retorna False se a lib faltar."""
        self.unbind_all()
        wanted = {
            trigger: callback
            for trigger, callback in callbacks.items()
            if trigger in MOUSE_TRIGGERS and callback is not None
        }
        if not wanted:
            return True
        if _mouse is None:
            log.error("Gatilhos da roda ignorados: %s", self.unavailable_reason)
            return False

        with self._lock:
            self._callbacks = wanted
            self._last_fired.clear()
        try:
            self._hook = _mouse.hook(self._on_event)
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao instalar o hook da roda do mouse: %s", exc)
            self._hook = None
            return False
        log.info("Gatilhos de mouse ativos (%s)", ", ".join(sorted(wanted)))
        return True

    def unbind_all(self) -> None:
        hook, self._hook = self._hook, None
        with self._lock:
            self._callbacks = {}
            self._last_fired.clear()
        if hook is not None and _mouse is not None:
            try:
                _mouse.unhook(hook)
            except Exception:  # noqa: BLE001 - hook ja removido
                pass

    # ---------------------------------------------------------------- interno

    @staticmethod
    def _trigger_for(event: object) -> str | None:
        """Traduz o evento da lib `mouse` para um gatilho nosso, ou None."""
        if _mouse is None:
            return None
        if isinstance(event, _mouse.WheelEvent):
            delta = getattr(event, "delta", 0)
            if not delta:
                return None
            return WHEEL_UP if delta > 0 else WHEEL_DOWN
        if isinstance(event, _mouse.ButtonEvent):
            # So a descida conta: a subida do mesmo clique dispararia de novo.
            # "double" tambem e descida: a lib renomeia o segundo clique rapido
            # (_winmouse.py), e ignora-lo comeria um clique a cada dois.
            if getattr(event, "event_type", "") not in ("down", "double"):
                return None
            return _BUTTON_TRIGGERS.get(getattr(event, "button", ""))
        return None

    def _on_event(self, event: object) -> None:
        """Roda na thread do listener da lib: precisa ser rapido."""
        trigger = self._trigger_for(event)
        if trigger is None:
            return

        with self._lock:
            callback = self._callbacks.get(trigger)
            if callback is None:
                return
            now = time.monotonic()
            window = max(0, self._debounce_ms()) / 1000.0
            if now - self._last_fired.get(trigger, 0.0) < window:
                return  # mesmo giro da roda / repique do botao: ja disparou
            self._last_fired[trigger] = now

        try:
            callback()
        except Exception:  # noqa: BLE001 - nunca derruba o listener
            log.exception("Erro no gatilho do mouse")
