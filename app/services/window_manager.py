"""Descobre se a janela em primeiro plano e o cliente do PokeAlliance.

Usa somente APIs publicas do Windows, com o direito minimo de processo
(PROCESS_QUERY_LIMITED_INFORMATION), que nao permite ler memoria. Nao injeta
codigo e nao modifica o cliente.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

log = logging.getLogger(__name__)

# O launcher tem janela propria e fica aberto junto do jogo: nao conta.
CLIENT_EXECUTABLES: frozenset[str] = frozenset(
    {"pokealliance_dx.exe", "pokealliance_gl.exe"}
)

# Classe da janela do cliente, confirmada em runtime. Reforco defensivo para
# quando o caminho do executavel nao puder ser lido por qualquer motivo.
#
# Nota: a elevacao do jogo NAO e um desses motivos. Medido: OpenProcess com
# PROCESS_QUERY_LIMITED_INFORMATION funciona sobre o cliente elevado e devolve
# o caminho normalmente (QUERY_INFORMATION e VM_READ e que sao negados).
# O que a elevacao quebra e o envio de teclas e o recebimento de hooks globais,
# e a solucao para isso e rodar este app como administrador.
CLIENT_WINDOW_CLASSES: frozenset[str] = frozenset({"pokealliancev3"})

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

_IS_WINDOWS = sys.platform == "win32"
if _IS_WINDOWS:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
else:  # pragma: no cover - o app e para Windows
    _user32 = _kernel32 = None


class WindowManager:
    """Consulta a janela ativa, com cache por handle."""

    def __init__(
        self,
        executables: frozenset[str] = CLIENT_EXECUTABLES,
        window_classes: frozenset[str] = CLIENT_WINDOW_CLASSES,
    ) -> None:
        self._executables = executables
        self._window_classes = window_classes
        self._cached_hwnd: int | None = None
        self._cached_result = False
        self._warned_about_access = False

    @property
    def available(self) -> bool:
        return _IS_WINDOWS

    def foreground_executable(self) -> str:
        """Caminho completo do executavel dono da janela ativa ('' se falhar)."""
        if not _IS_WINDOWS:
            return ""
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return ""
        return self._executable_of(hwnd)

    def is_game_focused(self) -> bool:
        """True quando o cliente do jogo esta em primeiro plano."""
        if not _IS_WINDOWS:
            return False
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        # O hwnd so muda quando o usuario troca de janela: cache barato e seguro.
        if hwnd == self._cached_hwnd:
            return self._cached_result

        path = self._executable_of(hwnd)
        result = self.decide(path, self.window_class(hwnd))

        if result and not path and not self._warned_about_access:
            self._warned_about_access = True
            log.warning(
                "O jogo foi reconhecido pela classe da janela porque o caminho "
                "do processo nao pode ser lido. Situacao incomum: verifique se "
                "o app esta rodando como administrador."
            )

        self._cached_hwnd = hwnd
        self._cached_result = result
        return result

    def decide(self, executable_path: str, window_class: str) -> bool:
        """Decide se a janela e o cliente, a partir dos dados ja coletados.

        Separado de `is_game_focused` para poder ser testado sem Win32: o
        caminho do executavel vem vazio quando o jogo roda elevado e o app nao,
        e nesse caso so a classe da janela resta.
        """
        if executable_path:
            return executable_path.rsplit("\\", 1)[-1].lower() in self._executables
        return window_class.lower() in self._window_classes

    def foreground_is_elevated_stranger(self) -> bool:
        """True quando a janela ativa existe mas o processo dela e inacessivel.

        Indica que a janela pertence a um processo de integridade mais alta.
        """
        if not _IS_WINDOWS:
            return False
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        return not self._executable_of(hwnd)

    @staticmethod
    def window_class(hwnd: int) -> str:
        if not _IS_WINDOWS or not hwnd:
            return ""
        buffer = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, buffer, 256)
        return buffer.value

    def game_client_origin(self) -> tuple[int, int] | None:
        """Canto superior esquerdo da area util do jogo, em coordenadas de tela.

        As posicoes da barra do time sao guardadas em relacao a este ponto, e
        nao a tela: assim o usuario pode mover a janela do jogo sem ter de
        gravar tudo de novo. Mudar a RESOLUCAO ainda exige regravar — a barra
        muda de lugar dentro da propria janela.
        """
        if not _IS_WINDOWS:
            return None
        hwnd = _user32.GetForegroundWindow()
        if not hwnd or not self.is_game_focused():
            return None
        point = wintypes.POINT(0, 0)
        if not _user32.ClientToScreen(hwnd, ctypes.byref(point)):
            return None
        return point.x, point.y

    def invalidate(self) -> None:
        self._cached_hwnd = None
        self._cached_result = False

    # ---------------------------------------------------------------- interno

    @staticmethod
    def _executable_of(hwnd: int) -> str:
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = _kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
        )
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(32768)
            if _kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                return buffer.value
            return ""
        except OSError as exc:  # pragma: no cover
            log.debug("Falha ao consultar o processo da janela: %s", exc)
            return ""
        finally:
            _kernel32.CloseHandle(handle)
