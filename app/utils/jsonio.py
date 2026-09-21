"""Leitura/escrita de JSON tolerante a arquivo corrompido."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def read_json(path: Path) -> dict[str, Any] | None:
    """Retorna o dicionario do arquivo ou None se ausente/invalido/corrompido."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        log.error("Falha ao ler %s: %s", path.name, exc)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("JSON invalido em %s (%s) - usando padroes", path.name, exc)
        _quarantine(path)
        return None

    if not isinstance(data, dict):
        log.error("JSON de %s nao e um objeto - usando padroes", path.name)
        _quarantine(path)
        return None
    return data


def write_json(path: Path, data: dict[str, Any]) -> bool:
    """Escrita atomica: grava em .tmp e so entao substitui o arquivo real."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as handle:
            tmp_name = handle.name
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        return True
    except OSError as exc:
        log.error("Falha ao salvar %s: %s", path.name, exc)
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)
        return False


def _quarantine(path: Path) -> None:
    """Move o arquivo quebrado para .bak para nao sobrescrever dados do usuario."""
    try:
        path.replace(path.with_suffix(path.suffix + ".bak"))
    except OSError:
        pass
