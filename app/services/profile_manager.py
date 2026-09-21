"""CRUD de perfis em config/profiles/*.json."""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

from app.constants import DEFAULT_PROFILE_NAME
from app.models.profile import Profile, default_profile
from app.utils.jsonio import read_json, write_json
from app.utils.paths import PROFILES_DIR, ensure_dirs

log = logging.getLogger(__name__)

_SLUG_INVALID = re.compile(r"[^a-z0-9_-]+")


def slugify(name: str) -> str:
    """Nome de arquivo seguro derivado do nome do perfil."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower().strip()
    slug = _SLUG_INVALID.sub("-", ascii_only).strip("-")
    return slug or "perfil"


class ProfileError(Exception):
    """Erro previsivel de perfil, exibido ao usuario."""


class ProfileManager:
    """Mantem os perfis em memoria; o disco e a fonte da verdade ao iniciar."""

    def __init__(self) -> None:
        ensure_dirs()
        self._profiles: dict[str, Profile] = {}
        self._files: dict[str, Path] = {}
        self.active_name: str = ""

    # ---------------------------------------------------------------- leitura

    @property
    def names(self) -> list[str]:
        return sorted(self._profiles, key=str.lower)

    @property
    def active(self) -> Profile:
        profile = self._profiles.get(self.active_name)
        if profile is None:
            profile = self._ensure_any_profile()
        return profile

    def get(self, name: str) -> Profile | None:
        return self._profiles.get(name)

    def load_all(self, preferred: str = "") -> Profile:
        """Le todos os perfis do disco e ativa o preferido (ou o primeiro)."""
        self._profiles.clear()
        self._files.clear()

        for path in sorted(PROFILES_DIR.glob("*.json")):
            data = read_json(path)
            if data is None:
                log.warning("Perfil ignorado (arquivo invalido): %s", path.name)
                continue
            profile = Profile.from_dict(data)
            if profile.name in self._profiles:
                profile.name = f"{profile.name} ({path.stem})"
            self._profiles[profile.name] = profile
            self._files[profile.name] = path

        if not self._profiles:
            profile = default_profile(DEFAULT_PROFILE_NAME)
            self._register(profile)
            self.save(profile.name)
            log.info("Nenhum perfil encontrado - perfil padrao criado")

        self.active_name = preferred if preferred in self._profiles else self.names[0]
        if not any(profile.game == "PXG" for profile in self._profiles.values()):
            name = "PXG"
            while name in self._profiles:
                name += " novo"
            self.create(name, "PXG")
        return self.active

    # ---------------------------------------------------------------- escrita

    def set_active(self, name: str) -> Profile:
        if name not in self._profiles:
            raise ProfileError(f"Perfil inexistente: {name}")
        self.active_name = name
        return self._profiles[name]

    def create(self, name: str, game: str = "PKA") -> Profile:
        name = self._validate_name(name)
        profile = default_profile(name, game)
        self._register(profile)
        self.save(name)
        return profile

    def duplicate(self, source_name: str, new_name: str) -> Profile:
        source = self._profiles.get(source_name)
        if source is None:
            raise ProfileError(f"Perfil inexistente: {source_name}")
        new_name = self._validate_name(new_name)
        copy = source.clone(new_name)
        self._register(copy)
        self.save(new_name)
        return copy

    def rename(self, old_name: str, new_name: str) -> Profile:
        profile = self._profiles.get(old_name)
        if profile is None:
            raise ProfileError(f"Perfil inexistente: {old_name}")
        if new_name == old_name:
            return profile
        new_name = self._validate_name(new_name)

        old_path = self._files.pop(old_name, None)
        del self._profiles[old_name]
        profile.name = new_name
        self._register(profile)
        self.save(new_name)
        if old_path is not None and old_path != self._files.get(new_name):
            try:
                old_path.unlink(missing_ok=True)
            except OSError as exc:
                log.warning("Nao foi possivel remover %s: %s", old_path.name, exc)
        if self.active_name == old_name:
            self.active_name = new_name
        return profile

    def delete(self, name: str) -> None:
        if name not in self._profiles:
            raise ProfileError(f"Perfil inexistente: {name}")
        if len(self._profiles) == 1:
            raise ProfileError("E preciso manter pelo menos um perfil.")
        path = self._files.pop(name, None)
        del self._profiles[name]
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                log.warning("Nao foi possivel excluir %s: %s", path.name, exc)
        if self.active_name == name:
            self.active_name = self.names[0]

    def save(self, name: str = "") -> bool:
        target = name or self.active_name
        profile = self._profiles.get(target)
        if profile is None:
            return False
        path = self._files.get(target)
        if path is None:
            path = self._unique_path(target)
            self._files[target] = path
        return write_json(path, profile.to_dict())

    def save_all(self) -> None:
        for name in list(self._profiles):
            self.save(name)

    # ---------------------------------------------------------------- helpers

    def _register(self, profile: Profile) -> None:
        self._profiles[profile.name] = profile
        self._files.setdefault(profile.name, self._unique_path(profile.name))

    def _unique_path(self, name: str) -> Path:
        slug = slugify(name)
        path = PROFILES_DIR / f"{slug}.json"
        taken = set(self._files.values())
        counter = 2
        while path in taken:
            path = PROFILES_DIR / f"{slug}-{counter}.json"
            counter += 1
        return path

    def _validate_name(self, name: str) -> str:
        name = (name or "").strip()
        if not name:
            raise ProfileError("O nome do perfil nao pode ficar vazio.")
        if len(name) > 40:
            raise ProfileError("O nome do perfil deve ter ate 40 caracteres.")
        if name in self._profiles:
            raise ProfileError(f'Ja existe um perfil chamado "{name}".')
        return name

    def _ensure_any_profile(self) -> Profile:
        if not self._profiles:
            profile = default_profile(DEFAULT_PROFILE_NAME)
            self._register(profile)
            self.save(profile.name)
        self.active_name = self.names[0]
        return self._profiles[self.active_name]
