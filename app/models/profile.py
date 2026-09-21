"""Modelo de perfil de Pokemon (skills, acoes e combo)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.constants import (
    ACTION_MODE_COMMAND,
    ACTION_MODE_KEY,
    ACTION_MODES,
    DEFAULT_HOLD_MS,
    DEFAULT_PROFILE_NAME,
    DEFAULT_STEP_DELAY_MS,
    MAX_DELAY_MS,
    MAX_MACROS,
    MIN_DELAY_MS,
    SKILL_COUNT,
    STEP_COMMAND,
    STEP_KEY,
    STEP_SKILL,
    STEP_TYPES,
    MOUSE_TRIGGERS,
    WHEEL_DOWN,
    WHEEL_UP,
)


def clamp_ms(value: Any, default: int = 0) -> int:
    """Converte para int e limita ao intervalo permitido (nunca negativo)."""
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(MIN_DELAY_MS, min(MAX_DELAY_MS, number))


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) else default


def _team_slots(value: Any) -> list[tuple[int, int] | None]:
    """Le as seis posicoes da barra do time, tolerando lixo e ausencia.

    Perfil antigo nao tem o campo; perfil editado a mao pode ter qualquer
    coisa. Em qualquer duvida a posicao vira None, que a rotacao trata como
    "ainda nao gravada" em vez de clicar num lugar errado da tela.
    """
    slots: list[tuple[int, int] | None] = [None] * 6
    if not isinstance(value, list):
        return slots
    for index, item in enumerate(value[:6]):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        try:
            slots[index] = (int(item[0]), int(item[1]))
        except (TypeError, ValueError):
            continue
    return slots


def _mouse_trigger(value: Any, default: str = WHEEL_DOWN) -> str:
    """Aceita so um gatilho de mouse conhecido; qualquer outro vira o padrao.

    Perfil vindo de versao antiga nao tem o campo, e um perfil editado a mao
    pode ter qualquer coisa — nos dois casos o gatilho tem de continuar valido.
    """
    text = _text(value).lower()
    return text if text in MOUSE_TRIGGERS else default


@dataclass
class SkillConfig:
    """Uma skill: qual tecla mandar para o jogo e qual hotkey dispara isso."""

    name: str = "Skill"
    key: str = ""
    hotkey: str = ""
    hold_ms: int = DEFAULT_HOLD_MS
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Any, index: int) -> SkillConfig:
        fallback = f"Skill {index + 1}"
        if not isinstance(data, dict):
            return cls(name=fallback)
        return cls(
            name=_text(data.get("name"), fallback) or fallback,
            key=_text(data.get("key")),
            hotkey=_text(data.get("hotkey")),
            hold_ms=clamp_ms(data.get("hold_ms"), DEFAULT_HOLD_MS),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "key": self.key,
            "hotkey": self.hotkey,
            "hold_ms": self.hold_ms,
            "enabled": self.enabled,
        }


@dataclass
class ActionConfig:
    """Acao simples (Revive / Offensive / Defensive).

    mode="key"     -> pressiona uma tecla no jogo.
    mode="command" -> abre o chat, digita o comando e da Enter.
    """

    label: str = "Acao"
    hotkey: str = ""
    mode: str = ACTION_MODE_KEY
    key: str = ""
    command: str = ""
    hold_ms: int = DEFAULT_HOLD_MS
    enabled: bool = True

    @classmethod
    def from_dict(
        cls, data: Any, label: str, default_mode: str = ACTION_MODE_KEY
    ) -> ActionConfig:
        if not isinstance(data, dict):
            return cls(label=label, mode=default_mode)
        mode = _text(data.get("mode"), default_mode).lower()
        if mode not in ACTION_MODES:
            mode = default_mode
        return cls(
            label=label,
            hotkey=_text(data.get("hotkey")),
            mode=mode,
            key=_text(data.get("key")),
            command=_text(data.get("command")),
            hold_ms=clamp_ms(data.get("hold_ms"), DEFAULT_HOLD_MS),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hotkey": self.hotkey,
            "mode": self.mode,
            "key": self.key,
            "command": self.command,
            "hold_ms": self.hold_ms,
            "enabled": self.enabled,
        }

    def is_runnable(self) -> bool:
        if self.mode == ACTION_MODE_COMMAND:
            return bool(self.command)
        return bool(self.key)


@dataclass
class MacroStep:
    """Uma etapa de macro.

    type="skill"   -> usa o slot de skill do perfil (envia a tecla dele)
    type="key"     -> envia uma tecla avulsa (ex.: item da barra de acao)
    type="command" -> abre o chat, digita o comando e da Enter
    """

    type: str = STEP_SKILL
    skill: int = 1
    key: str = ""
    command: str = ""
    delay_ms: int = DEFAULT_STEP_DELAY_MS

    @classmethod
    def from_dict(cls, data: Any) -> MacroStep:
        if not isinstance(data, dict):
            return cls()
        step_type = _text(data.get("type"), STEP_SKILL).lower()
        if step_type not in STEP_TYPES:
            step_type = STEP_SKILL
        try:
            skill = int(data.get("skill", 1))
        except (TypeError, ValueError):
            skill = 1
        return cls(
            type=step_type,
            skill=max(1, min(SKILL_COUNT, skill)),
            key=_text(data.get("key")),
            command=_text(data.get("command")),
            delay_ms=clamp_ms(data.get("delay_ms"), DEFAULT_STEP_DELAY_MS),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "skill": self.skill,
            "key": self.key,
            "command": self.command,
            "delay_ms": self.delay_ms,
        }

    def describe(self, profile: "Profile | None" = None) -> str:
        """Texto curto da etapa, para log e para a interface."""
        if self.type == STEP_COMMAND:
            return self.command or "(comando vazio)"
        if self.type == STEP_KEY:
            return f"tecla {self.key}" if self.key else "(tecla vazia)"
        if profile is not None:
            skill = profile.skill(self.skill)
            if skill is not None:
                return skill.name or f"Skill {self.skill}"
        return f"Skill {self.skill}"


@dataclass
class Macro:
    """Sequencia nomeada, disparada por uma hotkey ou pela roda do mouse."""

    name: str = "Macro"
    hotkey: str = ""
    enabled: bool = True
    steps: list[MacroStep] = field(default_factory=list)
    rotation: bool = False
    # So avanca para o proximo Pokemon (Ctrl+1..6), sem reviver. As etapas
    # ficam ignoradas: quem monta a sequencia e o controller, porque o slot
    # muda a cada acionamento.
    switch: bool = False

    @classmethod
    def from_dict(cls, data: Any) -> Macro:
        if not isinstance(data, dict):
            return cls()
        raw_steps = data.get("steps")
        steps = (
            [MacroStep.from_dict(item) for item in raw_steps]
            if isinstance(raw_steps, list)
            else []
        )
        return cls(
            name=_text(data.get("name"), "Macro") or "Macro",
            hotkey=_text(data.get("hotkey")),
            enabled=bool(data.get("enabled", True)),
            steps=steps,
            rotation=bool(data.get("rotation", False)),
            switch=bool(data.get("switch", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "hotkey": self.hotkey,
            "enabled": self.enabled,
            "steps": [step.to_dict() for step in self.steps],
            "rotation": self.rotation,
            "switch": self.switch,
        }


@dataclass
class Profile:
    """Perfil completo de um Pokemon. Nada aqui e fixo no codigo."""

    name: str = DEFAULT_PROFILE_NAME
    game: str = "PKA"
    skills: list[SkillConfig] = field(default_factory=list)
    revive: ActionConfig = field(default_factory=lambda: ActionConfig(label="Revive"))
    offensive: ActionConfig = field(
        default_factory=lambda: ActionConfig(label="Offensive", mode=ACTION_MODE_COMMAND)
    )
    defensive: ActionConfig = field(
        default_factory=lambda: ActionConfig(label="Defensive", mode=ACTION_MODE_COMMAND)
    )
    macros: list[Macro] = field(default_factory=list)
    rotation_enabled: bool = False
    rotation_delay_ms: int = 300
    rotation_trigger: str = WHEEL_DOWN
    # Posicao do retrato de cada Pokemon na barra do time, em pixels a partir
    # do canto da area util do jogo. Seis entradas; None = ainda nao gravada.
    # Relativo e nao absoluto para a janela do jogo poder ser movida.
    team_slots: list[tuple[int, int] | None] = field(
        default_factory=lambda: [None] * 6
    )

    def __post_init__(self) -> None:
        self._normalize_skills()
        del self.macros[MAX_MACROS:]

    def _normalize_skills(self) -> None:
        while len(self.skills) < SKILL_COUNT:
            index = len(self.skills)
            self.skills.append(SkillConfig(name=f"Skill {index + 1}"))
        del self.skills[SKILL_COUNT:]

    def skill(self, number: int) -> SkillConfig | None:
        """Skill pelo numero exibido na interface (1..6)."""
        if 1 <= number <= len(self.skills):
            return self.skills[number - 1]
        return None

    @classmethod
    def from_dict(cls, data: Any) -> Profile:
        if not isinstance(data, dict):
            data = {}
        raw_skills = data.get("skills")
        skills = (
            [SkillConfig.from_dict(item, i) for i, item in enumerate(raw_skills)]
            if isinstance(raw_skills, list)
            else []
        )
        return cls(
            name=_text(data.get("name"), DEFAULT_PROFILE_NAME) or DEFAULT_PROFILE_NAME,
            game="PXG" if data.get("game") == "PXG" else "PKA",
            skills=skills,
            revive=ActionConfig.from_dict(data.get("revive"), "Revive", ACTION_MODE_KEY),
            offensive=ActionConfig.from_dict(
                data.get("offensive"), "Offensive", ACTION_MODE_COMMAND
            ),
            defensive=ActionConfig.from_dict(
                data.get("defensive"), "Defensive", ACTION_MODE_COMMAND
            ),
            macros=_macros_from_dict(data),
            rotation_enabled=bool(data.get("rotation_enabled", False)),
            rotation_delay_ms=clamp_ms(data.get("rotation_delay_ms"), 300),
            rotation_trigger=_mouse_trigger(data.get("rotation_trigger")),
            team_slots=_team_slots(data.get("team_slots")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "skills": [skill.to_dict() for skill in self.skills],
            "game": self.game,
            "revive": self.revive.to_dict(),
            "offensive": self.offensive.to_dict(),
            "defensive": self.defensive.to_dict(),
            "macros": [macro.to_dict() for macro in self.macros],
            "rotation_enabled": self.rotation_enabled,
            "rotation_delay_ms": self.rotation_delay_ms,
            "rotation_trigger": self.rotation_trigger,
            "team_slots": [
                list(slot) if slot is not None else None for slot in self.team_slots
            ],
        }

    def macro(self, name: str) -> Macro | None:
        for macro in self.macros:
            if macro.name == name:
                return macro
        return None

    def clone(self, new_name: str) -> Profile:
        copy = Profile.from_dict(self.to_dict())
        copy.name = new_name
        return copy


def _macros_from_dict(data: dict[str, Any]) -> list[Macro]:
    """Le as macros, aceitando o formato antigo de combo unico."""
    raw = data.get("macros")
    if isinstance(raw, list):
        return [Macro.from_dict(item) for item in raw]

    legacy = data.get("combo")
    if not isinstance(legacy, dict):
        return []
    raw_steps = legacy.get("steps")
    steps = (
        [MacroStep.from_dict({**item, "type": STEP_SKILL}) for item in raw_steps if isinstance(item, dict)]
        if isinstance(raw_steps, list)
        else []
    )
    if not steps and not legacy.get("hotkey"):
        return []
    return [
        Macro(
            name="Combo",
            hotkey=_text(legacy.get("hotkey")),
            steps=steps,
        )
    ]


def default_profile(name: str = DEFAULT_PROFILE_NAME, game: str = "PKA") -> Profile:
    """Perfil inicial de exemplo (F1..F6 enviam as teclas 1..6)."""
    profile = Profile(name=name, game=game)
    if game == "PXG":
        return profile
    # A tecla enviada ao jogo e F1..F12 (ACTION_1..ACTION_12 do cliente).
    # A hotkey do app fica VAZIA de proposito: as skills ja funcionam
    # nativamente no jogo, e mapear F1 -> F1 so criaria uma ponte inutil
    # que ainda rouba a tecla do cliente. Preencha apenas se quiser
    # disparar a skill por outra tecla.
    for index, skill in enumerate(profile.skills, start=1):
        skill.name = f"Skill {index}"
        skill.key = f"f{index}"
        skill.hotkey = ""

    # As acoes usam as teclas que o JOGO ja tem configuradas na barra de acao,
    # em vez de digitar no chat. E mais rapido (uma tecla em vez de ~6 eventos),
    # nao deixa rastro no historico de conversa e nao depende do estado do chat.
    # O modo "comando" continua disponivel para quem nao tiver a barra montada.
    profile.revive = ActionConfig(
        label="Revive", hotkey="", mode=ACTION_MODE_KEY, key="q"
    )
    profile.offensive = ActionConfig(
        label="Offensive", hotkey="", mode=ACTION_MODE_KEY, key="r", command="!offensive"
    )
    profile.defensive = ActionConfig(
        label="Defensive", hotkey="", mode=ACTION_MODE_KEY, key="e", command="!defensive"
    )
    # Macros na roda do mouse: cima = atacar, baixo = recuperar.
    #
    # Todas as etapas sao TECLAS que o jogo ja reconhece na barra de acao:
    #   R = !offensive   T = !autocombo   E = !defensive   Q = item de revive
    # Nenhuma passa pelo chat. Se as suas teclas forem outras, troque na aba
    # Combo — o botao "Gravar" captura a tecla que voce apertar.
    profile.macros = [
        Macro(
            name="Ofensiva",
            hotkey=WHEEL_UP,
            steps=[
                MacroStep(type=STEP_KEY, key="r", delay_ms=200),
                MacroStep(type=STEP_KEY, key="t", delay_ms=0),
            ],
        ),
        Macro(
            name="Defensiva",
            hotkey=WHEEL_DOWN,
            steps=[
                MacroStep(type=STEP_KEY, key="q", delay_ms=200),
                MacroStep(type=STEP_KEY, key="e", delay_ms=0),
            ],
        ),
    ]
    return profile
