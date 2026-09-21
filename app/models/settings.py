"""Configuracoes globais persistentes (settings.json)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.constants import (
    CHAT_OPEN_PAUSE_MS,
    CHAT_CLOSE_PAUSE_MS,
    CHAT_SEND_PAUSE_MS,
    DEFAULT_CANCEL_HOTKEY,
    DEFAULT_CHAT_CLOSE_KEY,
    DEFAULT_CHAT_KEY,
    DEFAULT_EMERGENCY_HOTKEY,
    DEFAULT_TYPE_DELAY_MS,
    DEFAULT_WHEEL_DEBOUNCE_MS,
)
from app.models.profile import clamp_ms


@dataclass
class WindowState:
    width: int = 1040
    height: int = 680
    x: int | None = None
    y: int | None = None

    @classmethod
    def from_dict(cls, data: Any) -> WindowState:
        if not isinstance(data, dict):
            return cls()
        state = cls()
        state.width = _int(data.get("width"), state.width, 820, 3840)
        state.height = _int(data.get("height"), state.height, 560, 2160)
        state.x = _opt_int(data.get("x"))
        state.y = _opt_int(data.get("y"))
        return state

    def to_dict(self) -> dict[str, Any]:
        return {"width": self.width, "height": self.height, "x": self.x, "y": self.y}

    def geometry(self) -> str:
        if self.x is None or self.y is None:
            return f"{self.width}x{self.height}"
        return f"{self.width}x{self.height}+{self.x}+{self.y}"


@dataclass
class Settings:
    """Tudo que nao pertence a um perfil especifico."""

    active_profile: str = ""
    game_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    client_executable: str = ""
    emergency_hotkey: str = DEFAULT_EMERGENCY_HOTKEY
    cancel_hotkey: str = DEFAULT_CANCEL_HOTKEY
    wheel_debounce_ms: int = DEFAULT_WHEEL_DEBOUNCE_MS
    require_game_focus: bool = True
    chat_key: str = DEFAULT_CHAT_KEY
    chat_confirm_key: str = "enter"
    chat_close_key: str = DEFAULT_CHAT_CLOSE_KEY
    chat_close_pause_ms: int = CHAT_CLOSE_PAUSE_MS
    type_delay_ms: int = DEFAULT_TYPE_DELAY_MS
    chat_open_pause_ms: int = CHAT_OPEN_PAUSE_MS
    chat_send_pause_ms: int = CHAT_SEND_PAUSE_MS
    suppress_hotkeys: bool = True
    autostart_hotkeys: bool = False
    always_on_top: bool = False
    appearance: str = "dark"
    window: WindowState = field(default_factory=WindowState)

    @classmethod
    def from_dict(cls, data: Any) -> Settings:
        if not isinstance(data, dict):
            data = {}
        settings = cls()
        settings.active_profile = _str(data.get("active_profile"), "")
        raw_games = data.get("game_settings", {})
        if isinstance(raw_games, dict):
            settings.game_settings = {
                key: dict(value) for key, value in raw_games.items()
                if key in ("PKA", "PXG") and isinstance(value, dict)
            }
        settings.client_executable = _str(data.get("client_executable"), "")
        settings.emergency_hotkey = _str(
            data.get("emergency_hotkey"), DEFAULT_EMERGENCY_HOTKEY
        )
        settings.cancel_hotkey = _str(data.get("cancel_hotkey"), DEFAULT_CANCEL_HOTKEY)
        settings.wheel_debounce_ms = clamp_ms(
            data.get("wheel_debounce_ms"), DEFAULT_WHEEL_DEBOUNCE_MS
        )
        settings.require_game_focus = bool(data.get("require_game_focus", True))
        settings.chat_key = _str(data.get("chat_key"), DEFAULT_CHAT_KEY)
        settings.chat_confirm_key = _str(data.get("chat_confirm_key"), "enter")
        settings.chat_close_key = _str(data.get("chat_close_key"), DEFAULT_CHAT_CLOSE_KEY)
        settings.chat_close_pause_ms = clamp_ms(
            data.get("chat_close_pause_ms"), CHAT_CLOSE_PAUSE_MS
        )
        settings.type_delay_ms = clamp_ms(
            data.get("type_delay_ms"), DEFAULT_TYPE_DELAY_MS
        )
        settings.chat_open_pause_ms = clamp_ms(
            data.get("chat_open_pause_ms"), CHAT_OPEN_PAUSE_MS
        )
        settings.chat_send_pause_ms = clamp_ms(
            data.get("chat_send_pause_ms"), CHAT_SEND_PAUSE_MS
        )
        settings.suppress_hotkeys = bool(data.get("suppress_hotkeys", True))
        settings.autostart_hotkeys = bool(data.get("autostart_hotkeys", False))
        settings.always_on_top = bool(data.get("always_on_top", False))
        appearance = _str(data.get("appearance"), "dark").lower()
        settings.appearance = appearance if appearance in ("dark", "light", "system") else "dark"
        settings.window = WindowState.from_dict(data.get("window"))
        return settings

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_profile": self.active_profile,
            "game_settings": self.game_settings,
            "client_executable": self.client_executable,
            "emergency_hotkey": self.emergency_hotkey,
            "cancel_hotkey": self.cancel_hotkey,
            "wheel_debounce_ms": self.wheel_debounce_ms,
            "require_game_focus": self.require_game_focus,
            "chat_key": self.chat_key,
            "chat_confirm_key": self.chat_confirm_key,
            "chat_close_key": self.chat_close_key,
            "chat_close_pause_ms": self.chat_close_pause_ms,
            "type_delay_ms": self.type_delay_ms,
            "chat_open_pause_ms": self.chat_open_pause_ms,
            "chat_send_pause_ms": self.chat_send_pause_ms,
            "suppress_hotkeys": self.suppress_hotkeys,
            "autostart_hotkeys": self.autostart_hotkeys,
            "always_on_top": self.always_on_top,
            "appearance": self.appearance,
            "window": self.window.to_dict(),
        }


def _str(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _opt_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
