"""Carga e persistencia de settings.json."""

from __future__ import annotations

import logging

from app.models.settings import Settings
from app.utils.jsonio import read_json, write_json
from app.utils.paths import SETTINGS_FILE, ensure_dirs

log = logging.getLogger(__name__)


class SettingsManager:
    def __init__(self) -> None:
        ensure_dirs()
        self.settings: Settings = Settings()

    def load(self) -> Settings:
        data = read_json(SETTINGS_FILE)
        self.settings = Settings.from_dict(data or {})
        if data is None:
            self.save()
        return self.settings

    def save(self) -> bool:
        ok = write_json(SETTINGS_FILE, self.settings.to_dict())
        if not ok:
            log.error("Nao foi possivel salvar as configuracoes")
        return ok
