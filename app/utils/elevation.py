"""Privilegio de administrador.

O Windows impede que um processo de integridade normal envie teclas para uma
janela de integridade mais alta (UIPI). Se o PokeAlliance abre como
administrador, o app precisa abrir tambem — caso contrario as teclas
simplesmente nao chegam, sem nenhum erro visivel.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_SW_SHOWNORMAL = 1


def is_elevated() -> bool:
    """True se o processo atual roda com privilegio de administrador."""
    if not _IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001 - API indisponivel
        return False


def relaunch_as_admin() -> bool:
    """Reabre o proprio programa pedindo elevacao (dispara o UAC).

    Retorna True quando o novo processo foi iniciado — nesse caso o chamador
    deve encerrar o processo atual. False se o usuario recusou o UAC ou se a
    chamada falhou.
    """
    if not _IS_WINDOWS:
        return False

    if getattr(sys, "frozen", False):
        program = sys.executable
        arguments = _join(sys.argv[1:])
    else:
        program = sys.executable  # python.exe
        arguments = _join([str(Path(sys.argv[0]).resolve()), *sys.argv[1:]])

    try:
        # > 32 significa sucesso na API antiga do ShellExecute.
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", program, arguments, str(Path.cwd()), _SW_SHOWNORMAL
        )
    except Exception as exc:  # noqa: BLE001
        log.error("Falha ao reabrir como administrador: %s", exc)
        return False

    if result <= 32:
        log.warning("Reabertura como administrador recusada ou falhou (codigo %s)", result)
        return False
    return True


def _join(parts: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in parts)
