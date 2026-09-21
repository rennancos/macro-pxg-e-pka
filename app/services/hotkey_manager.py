"""Camada unica de acesso a biblioteca `keyboard` para hotkeys globais.

Nenhum outro modulo importa `keyboard` para registrar atalhos. Aqui tambem
ficam a normalizacao (usada para detectar hotkeys duplicadas) e a remocao
segura dos registros.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

log = logging.getLogger(__name__)

try:  # a biblioteca so existe no ambiente com dependencias instaladas
    import keyboard as _keyboard
except Exception as exc:  # noqa: BLE001 - importar keyboard pode falhar por permissao
    _keyboard = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

KEYBOARD_AVAILABLE = _keyboard is not None


def keyboard_module() -> Any:
    """Devolve o modulo `keyboard` ou levanta erro legivel para a GUI."""
    if _keyboard is None:
        raise RuntimeError(
            "A biblioteca 'keyboard' nao esta disponivel "
            f"({_IMPORT_ERROR}). Instale com: pip install keyboard"
        )
    return _keyboard


@dataclass(frozen=True)
class Binding:
    """Uma hotkey a registrar."""

    label: str
    hotkey: str
    callback: Callable[[], None]
    suppress: bool = False


@dataclass
class BindResult:
    registered: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)

    @property
    def has_problems(self) -> bool:
        return bool(self.duplicates or self.invalid)


def normalize(hotkey: str) -> tuple | None:
    """Forma canonica da hotkey, usada para comparar duplicatas.

    Retorna None quando a hotkey nao pode ser interpretada.
    """
    text = (hotkey or "").strip().lower()
    if not text:
        return None
    if _keyboard is None:
        return (text,)
    try:
        return _keyboard.parse_hotkey(text)
    except Exception:  # noqa: BLE001 - parse lanca ValueError e outros
        return None


def is_valid(hotkey: str) -> bool:
    return normalize(hotkey) is not None


class HotkeyManager:
    """Registra/remove hotkeys globais, recusando duplicatas e invalidas."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handles: list[Any] = []
        self._emergency_handle: Any | None = None
        self._emergency_hotkey: str = ""
        self._active: dict[str, str] = {}

    @property
    def active_bindings(self) -> dict[str, str]:
        """Mapa label -> hotkey atualmente registrada."""
        with self._lock:
            return dict(self._active)

    def bind(self, bindings: Iterable[Binding]) -> BindResult:
        """Substitui todos os registros (exceto o de emergencia)."""
        keyboard = keyboard_module()
        result = BindResult()
        self.unbind_all()

        seen: dict[tuple, str] = {}
        if self._emergency_hotkey:
            emergency = normalize(self._emergency_hotkey)
            if emergency is not None:
                seen[emergency] = "Emergencia"

        with self._lock:
            for binding in bindings:
                if not binding.hotkey.strip():
                    continue
                canonical = normalize(binding.hotkey)
                if canonical is None:
                    result.invalid.append(f"{binding.label}: {binding.hotkey}")
                    continue
                owner = seen.get(canonical)
                if owner is not None:
                    result.duplicates.append(
                        f"{binding.label}: {binding.hotkey} (ja usada por {owner})"
                    )
                    continue
                try:
                    handle = keyboard.add_hotkey(
                        binding.hotkey.strip().lower(),
                        binding.callback,
                        suppress=binding.suppress,
                        trigger_on_release=False,
                    )
                except Exception as exc:  # noqa: BLE001
                    log.error("Falha ao registrar %s (%s): %s", binding.label, binding.hotkey, exc)
                    result.invalid.append(f"{binding.label}: {binding.hotkey}")
                    continue
                self._handles.append(handle)
                seen[canonical] = binding.label
                self._active[binding.label] = binding.hotkey
                result.registered.append(f"{binding.label}: {binding.hotkey}")
        return result

    def unbind_all(self) -> None:
        keyboard = _keyboard
        with self._lock:
            handles, self._handles = self._handles, []
            self._active.clear()
        if keyboard is None:
            return
        for handle in handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:  # noqa: BLE001 - handle ja removido
                pass

    def bind_emergency(self, hotkey: str, callback: Callable[[], None]) -> bool:
        """Registra a parada de emergencia (fica ativa o tempo todo)."""
        self.unbind_emergency()
        if not hotkey.strip() or normalize(hotkey) is None:
            log.error("Hotkey de emergencia invalida: %r", hotkey)
            return False
        try:
            keyboard = keyboard_module()
            self._emergency_handle = keyboard.add_hotkey(
                hotkey.strip().lower(), callback, suppress=False
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao registrar a hotkey de emergencia: %s", exc)
            return False
        self._emergency_hotkey = hotkey
        return True

    def unbind_emergency(self) -> None:
        if self._emergency_handle is not None and _keyboard is not None:
            try:
                _keyboard.remove_hotkey(self._emergency_handle)
            except Exception:  # noqa: BLE001
                pass
        self._emergency_handle = None
        self._emergency_hotkey = ""

    def shutdown(self) -> None:
        self.unbind_all()
        self.unbind_emergency()


def read_hotkey(timeout: float | None = None) -> str:
    """Bloqueia ate o usuario terminar de pressionar uma combinacao.

    Usado apenas pelo botao "Gravar" da interface, em thread separada.
    Nao registra nada em log: nao existe captura de digitacao no programa.
    """
    keyboard = keyboard_module()
    del timeout  # a API de leitura da biblioteca nao aceita timeout
    return keyboard.read_hotkey(suppress=False)
