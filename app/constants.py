"""Constantes centralizadas da aplicacao."""

from __future__ import annotations

from typing import Final

APP_NAME: Final = "PokeAlliance Hotkeys"
APP_TITLE: Final = "PKA / PXG Hotkeys"

# O cliente expoe ACTION_1..ACTION_12; ha Pokemon com ate 11 golpes ativos.
SKILL_COUNT: Final = 12

# Limites de seguranca para qualquer valor de tempo vindo do JSON/GUI.
MIN_DELAY_MS: Final = 0
MAX_DELAY_MS: Final = 60_000
DEFAULT_HOLD_MS: Final = 30
DEFAULT_STEP_DELAY_MS: Final = 40
DEFAULT_TYPE_DELAY_MS: Final = 3

# O proprio cliente impoe 30 ms entre acionamentos de hotkey (hotkeyDelay).
# Enviar mais rapido que isso faz o jogo engolir eventos.
MIN_STEP_DELAY_MS: Final = 30

# Pausas fixas da sequencia "abrir chat -> digitar -> enter -> fechar".
CHAT_OPEN_PAUSE_MS: Final = 40
CHAT_SEND_PAUSE_MS: Final = 20
CHAT_CLOSE_PAUSE_MS: Final = 30

# Depois de enviar, o cliente pode deixar o campo de chat com o foco. Nesse
# estado a proxima tecla da macro vira texto digitado em vez de comandar o
# jogo. Esta tecla devolve o chat ao estado travado entre as etapas.
#
# Padrao ctrl+e: e a acao CLOSE_CHAT registrada no proprio cliente. Foi
# preferida a "esc" por dois motivos concretos: esc colide com a hotkey de
# cancelar macro (o app cancelaria a propria sequencia) e, no cliente, esc
# tambem interrompe ataque/seguir.
DEFAULT_CHAT_CLOSE_KEY: Final = "ctrl+e"

# Modos de execucao de uma acao.
ACTION_MODE_KEY: Final = "key"
ACTION_MODE_COMMAND: Final = "command"
ACTION_MODES: Final = (ACTION_MODE_KEY, ACTION_MODE_COMMAND)

# Tipos de passo dentro de uma macro.
STEP_SKILL: Final = "skill"
STEP_KEY: Final = "key"
STEP_COMMAND: Final = "command"
STEP_TYPES: Final = (STEP_SKILL, STEP_KEY, STEP_COMMAND)

# Clique do mouse numa posicao gravada. NAO entra em STEP_TYPES: o editor de
# macros nao oferece esse tipo, ele existe so para a rotacao de Pokemon, que
# precisa clicar no retrato do Pokemon que saiu antes de aplicar o revive.
STEP_CLICK: Final = "click"

# Devolve o ponteiro ao lugar de origem, no fim da rotacao.
STEP_POINTER_HOME: Final = "pointer_home"

# O cliente precisa de um instante entre o ponteiro chegar e o botao descer,
# e de outro antes de o ponteiro voltar — senao o clique se perde.
CLICK_SETTLE_MS: Final = 40

STEP_LABELS: Final = {
    STEP_SKILL: "Skill",
    STEP_KEY: "Tecla",
    STEP_COMMAND: "Comando",
}

# Gatilhos do mouse (usados no lugar de uma hotkey de teclado).
#
# O Windows so tem cinco botoes de mouse: esquerdo, direito, meio, X1 e X2.
# Mouses de 12 botoes laterais (Naga, G600) mandam os extras COMO TECLAS de
# teclado — esses ja caem no sistema de hotkeys normal, nao entram aqui.
#
# Esquerdo e direito ficam de fora: o hook do mouse nao suprime o evento, e um
# macro no botao esquerdo dispararia a cada clique na interface e no jogo.
WHEEL_UP: Final = "wheel_up"
WHEEL_DOWN: Final = "wheel_down"
MOUSE_MIDDLE: Final = "mouse_middle"
MOUSE_X1: Final = "mouse_x1"
MOUSE_X2: Final = "mouse_x2"

WHEEL_TRIGGERS: Final = (WHEEL_UP, WHEEL_DOWN)
MOUSE_BUTTONS: Final = (MOUSE_MIDDLE, MOUSE_X1, MOUSE_X2)
MOUSE_TRIGGERS: Final = WHEEL_TRIGGERS + MOUSE_BUTTONS

MOUSE_LABELS: Final = {
    WHEEL_UP: "Roda do mouse para cima",
    WHEEL_DOWN: "Roda do mouse para baixo",
    MOUSE_MIDDLE: "Botao do meio",
    MOUSE_X1: "Botao lateral 1 (voltar)",
    MOUSE_X2: "Botao lateral 2 (avancar)",
}
# Compatibilidade com a pagina de combos existente.
WHEEL_LABELS: Final = MOUSE_LABELS
# Nomes curtos para caber nos botoes da interface.
MOUSE_SHORT_LABELS: Final = {
    WHEEL_UP: "Roda p/ cima",
    WHEEL_DOWN: "Roda p/ baixo",
    MOUSE_MIDDLE: "Botao do meio",
    MOUSE_X1: "Lateral 1",
    MOUSE_X2: "Lateral 2",
}
# Um giro da roda gera varios eventos; so o primeiro dentro da janela conta.
# Vale tambem para os botoes: protege de repique do firmware.
DEFAULT_WHEEL_DEBOUNCE_MS: Final = 80

# Indicador visual de modo (nunca lido do jogo, so reflete a ultima acao enviada).
MODE_NONE: Final = "---"
MODE_OFFENSIVE: Final = "OFFENSIVE"
MODE_DEFENSIVE: Final = "DEFENSIVE"

DEFAULT_EMERGENCY_HOTKEY: Final = "pause"
DEFAULT_CANCEL_HOTKEY: Final = "esc"
DEFAULT_CHAT_KEY: Final = "enter"
DEFAULT_PROFILE_NAME: Final = "Padrao"

MAX_MACROS: Final = 12
MAX_LOG_LINES: Final = 500
