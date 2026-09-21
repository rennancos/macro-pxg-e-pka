"""Teste de fumaca da interface: monta a janela e exercita a edicao.

Complementa o selfcheck.py, que cobre so a logica sem GUI. Aqui o objetivo e
pegar erro em callback de widget — o tipo de falha que o Tkinter engole e que,
num build --windowed, se manifesta apenas como "o botao parou de responder".

Rode com:  python smoketest.py

Nao envia teclas ao sistema e NAO grava no config: trabalha sobre uma copia do
perfil em memoria.
"""

from __future__ import annotations

import sys
import traceback
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.constants import (  # noqa: E402
    STEP_COMMAND,
    STEP_KEY,
    STEP_LABELS,
    STEP_SKILL,
    WHEEL_UP,
)
from app.gui.main_window import MainWindow  # noqa: E402
from app.models.profile import default_profile  # noqa: E402
from app.services.controller import AppController  # noqa: E402

falhas: list[str] = []


def checar(nome: str, funcao) -> None:
    try:
        funcao()
    except Exception:  # noqa: BLE001
        falhas.append(f"{nome}\n{traceback.format_exc()}")
        print(f"FALHOU  {nome}")
    else:
        print(f"ok      {nome}")


def _run() -> int:
    controller = AppController()
    # Copia de fabrica em memoria: o teste nunca toca no perfil salvo.
    controller.profile.macros = default_profile("ref").macros
    controller.profile.skills = default_profile("ref").skills

    janela = MainWindow(controller)
    janela.update()

    for nome in janela.page_titles:
        checar(
            f"pagina {nome}",
            lambda n=nome: (janela.show_page(n), janela.update()),
        )

    janela.show_page("Combo")
    pagina = janela.pages["Combo"]
    janela.update()

    def trocar_tipo(tipo: str) -> None:
        """Troca o tipo da ultima etapa pelo menu, como o usuario faria."""
        ultimo = len(pagina._current.steps) - 1
        pagina._step_widgets[ultimo]["type"].set(STEP_LABELS[tipo])
        pagina._on_step_type(ultimo)
        janela.update()
        obtido = pagina._current.steps[-1].type
        assert obtido == tipo, f"esperado {tipo}, veio {obtido}"

    checar("adicionar etapa", lambda: (pagina._add_step(), janela.update()))
    checar("etapa -> Comando", lambda: trocar_tipo(STEP_COMMAND))
    checar("etapa -> Tecla", lambda: trocar_tipo(STEP_KEY))
    checar("etapa -> Skill", lambda: trocar_tipo(STEP_SKILL))

    def reordenar() -> None:
        antes = [s.type for s in pagina._current.steps]
        pagina._move_step(len(antes) - 1, -1)
        janela.update()
        depois = [s.type for s in pagina._current.steps]
        assert depois != antes or len(antes) < 2, f"ordem nao mudou: {depois}"

    checar("reordenar etapa", reordenar)
    checar(
        "remover etapa",
        lambda: (pagina._remove_step(len(pagina._current.steps) - 1), janela.update()),
    )
    checar("nova macro", lambda: (pagina._add_macro(), janela.update()))
    checar("trocar de macro", lambda: (pagina._select(0), janela.update()))

    def cache_de_etapas() -> None:
        """Trocar de macro e voltar tem de reusar o quadro, nao remontar.

        Sem isto a aba volta a gastar ~2 s por troca num macro de 11 etapas.
        """
        pagina._select(0)
        janela.update()
        quadro = pagina._step_cache[0][1]
        pagina._select(1)
        janela.update()
        pagina._select(0)
        janela.update()
        assert pagina._step_cache[0][1] is quadro, "o quadro foi remontado"
        assert pagina._shown_steps is quadro, "quadro errado na tela"

    checar("reaproveitar etapas ao trocar de macro", cache_de_etapas)

    def gatilho_roda() -> None:
        pagina._select(0)
        assert pagina._current.hotkey == WHEEL_UP, pagina._current.hotkey

    checar("gatilho da roda preservado", gatilho_roda)

    def descartar_edicao() -> None:
        """Trocar de aba preserva o que foi digitado; Descartar joga fora.

        A troca de aba reaproveita as etapas ja desenhadas (senao cada troca
        recria dezenas de widgets do CTk). Descartar precisa furar esse
        reaproveitamento, ou o botao nao descarta nada.
        """
        # Parte de um estado conhecido: os testes acima deixaram a macro de
        # trabalho diferente da salva no perfil.
        pagina._selected = 0
        pagina.discard()
        janela.update()

        campo = pagina._step_widgets[0]["delay"]
        salvo = campo.get()
        campo.delete(0, "end")
        campo.insert(0, "9999")
        janela.update()

        janela.show_page("Skills")
        janela.show_page("Combo")
        janela.update()
        assert campo.get() == "9999", f"troca de aba perdeu a edicao: {campo.get()}"

        pagina.discard()
        janela.update()
        atual = pagina._step_widgets[0]["delay"].get()
        assert atual == salvo, f"Descartar nao restaurou: {atual} != {salvo}"

    checar("descartar edicao nao salva", descartar_edicao)

    checar("skills", lambda: (janela.page("Skills").on_show(), janela.update()))
    checar("perfis", lambda: (janela.page("Pokemon").on_show(), janela.update()))
    checar("hotkeys", lambda: (janela.page("Hotkeys").on_show(), janela.update()))
    checar(
        "configuracoes",
        lambda: (janela.page("Configuracoes").on_show(), janela.update()),
    )

    controller.combo.cancel()
    controller.hotkeys.shutdown()
    controller.wheel.unbind_all()
    janela.destroy()

    if falhas:
        print("\n=== FALHAS ===")
        for item in falhas:
            print(item)
        return 1
    print("\nSMOKE OK - nada foi gravado em disco")
    return 0


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        profiles = root / "profiles"
        profiles.mkdir()
        with (
            patch("app.services.profile_manager.PROFILES_DIR", profiles),
            patch("app.services.profile_manager.ensure_dirs"),
            patch("app.services.settings_manager.SETTINGS_FILE", root / "settings.json"),
            patch("app.services.settings_manager.ensure_dirs"),
        ):
            return _run()


if __name__ == "__main__":
    raise SystemExit(main())
