"""Logging da aplicacao: arquivo rotativo + buffer em memoria para a GUI."""

from __future__ import annotations

import logging
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import Callable

from app.constants import MAX_LOG_LINES
from app.utils.paths import LOG_FILE, ensure_dirs

_FORMAT = "[%(asctime)s.%(msecs)03d] %(message)s"
_DATEFMT = "%H:%M:%S"


class MemoryLogHandler(logging.Handler):
    """Guarda as ultimas linhas formatadas e notifica a GUI."""

    def __init__(self, capacity: int = MAX_LOG_LINES) -> None:
        super().__init__()
        self.records: deque[str] = deque(maxlen=capacity)
        self._listener: Callable[[str], None] | None = None

    def set_listener(self, listener: Callable[[str], None] | None) -> None:
        self._listener = listener

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:  # noqa: BLE001 - log nunca pode derrubar a app
            return
        self.records.append(line)
        listener = self._listener
        if listener is not None:
            try:
                listener(line)
            except Exception:  # noqa: BLE001
                pass

    def dump(self) -> str:
        return "\n".join(self.records)

    def clear(self) -> None:
        self.records.clear()


memory_handler = MemoryLogHandler()


def setup_logging(debug: bool = False) -> logging.Logger:
    ensure_dirs()
    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=512_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        pass  # sem permissao de escrita: segue so com log em memoria

    memory_handler.setFormatter(formatter)
    root.addHandler(memory_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    return logging.getLogger("pokealliance")
