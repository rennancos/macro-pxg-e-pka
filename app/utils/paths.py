"""Resolucao de caminhos (funciona em dev e dentro do PyInstaller --onefile)."""

from __future__ import annotations

import sys
from pathlib import Path


def base_dir() -> Path:
    """Pasta onde ficam config/ e logs/.

    Em desenvolvimento e a raiz do projeto; congelado, e a pasta do .exe
    (nunca a pasta temporaria _MEIPASS, que some ao fechar o programa).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_dir() -> Path:
    """Pasta de recursos somente-leitura embutidos no executavel."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return base_dir()


CONFIG_DIR: Path = base_dir() / "config"
PROFILES_DIR: Path = CONFIG_DIR / "profiles"
LOGS_DIR: Path = base_dir() / "logs"
ASSETS_DIR: Path = resource_dir() / "assets"

SETTINGS_FILE: Path = CONFIG_DIR / "settings.json"
LOG_FILE: Path = LOGS_DIR / "app.log"


def ensure_dirs() -> None:
    for directory in (CONFIG_DIR, PROFILES_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
