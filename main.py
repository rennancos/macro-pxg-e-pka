"""Ponto de entrada do PokeAlliance Hotkeys.

Gerenciador local de hotkeys: toda acao parte de uma tecla pressionada pelo
usuario. O programa nao le a memoria do jogo, nao analisa a tela e nao executa
ciclos automaticos.
"""

from __future__ import annotations

import logging
import sys
import traceback
from tkinter import messagebox

from app.constants import APP_TITLE
from app.utils.logger import setup_logging
from app.utils.paths import ensure_dirs


def _fatal(message: str) -> int:
    logging.getLogger(__name__).critical(message)
    try:
        messagebox.showerror(APP_TITLE, message)
    except Exception:  # noqa: BLE001 - sem display disponivel
        print(message, file=sys.stderr)
    return 1


def _check_elevation(window: object, log: logging.Logger) -> None:
    """Avisa quando o app nao esta elevado e oferece reabrir como admin.

    Se o PokeAlliance roda como administrador e o app nao, o Windows bloqueia
    as teclas enviadas — sem erro, sem aviso. O sintoma e o app parecer morto.
    """
    from app.utils.elevation import is_elevated, relaunch_as_admin

    if is_elevated():
        log.info("Executando como administrador")
        return

    log.warning("Executando SEM privilegio de administrador")
    reabrir = messagebox.askyesno(
        APP_TITLE,
        "O programa nao esta rodando como administrador.\n\n"
        "Se o PokeAlliance abrir como administrador, o Windows vai bloquear as "
        "teclas enviadas por este programa — ele parecera nao funcionar, sem "
        "mostrar nenhum erro.\n\n"
        "Reabrir como administrador agora?",
        icon="warning",
    )
    if not reabrir:
        log.info("Usuario optou por continuar sem privilegio de administrador")
        return

    if relaunch_as_admin():
        log.info("Reaberto como administrador; encerrando esta instancia")
        try:
            window.destroy()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        raise SystemExit(0)

    messagebox.showwarning(
        APP_TITLE,
        "Nao foi possivel reabrir como administrador.\n\n"
        "Feche o programa e use: clique direito no executavel > "
        "Executar como administrador.",
    )


def main() -> int:
    ensure_dirs()
    log = setup_logging(debug="--debug" in sys.argv)
    log.info("%s iniciado", APP_TITLE)

    if sys.platform != "win32":
        log.warning("Este programa foi feito para Windows; o envio de teclas pode falhar.")

    try:
        import customtkinter  # noqa: F401 - checagem de dependencia
    except ImportError:
        return _fatal(
            "CustomTkinter nao esta instalado.\n\n"
            "Ative o ambiente virtual e rode:\n    pip install -r requirements.txt"
        )

    from app.gui.main_window import MainWindow
    from app.services.controller import AppController
    from app.services.hotkey_manager import KEYBOARD_AVAILABLE

    try:
        controller = AppController()
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha ao iniciar")
        return _fatal(f"Falha ao iniciar a aplicacao:\n\n{exc}")

    window = MainWindow(controller)

    _check_elevation(window, log)

    if not KEYBOARD_AVAILABLE:
        messagebox.showwarning(
            APP_TITLE,
            "A biblioteca 'keyboard' nao pode ser carregada.\n\n"
            "Instale com 'pip install keyboard'. Em alguns sistemas e preciso "
            "executar o programa como administrador.",
        )
    else:
        if not controller.setup_emergency():
            log.warning("Hotkey de emergencia nao registrada")
        if controller.settings.autostart_hotkeys:
            try:
                controller.enable_hotkeys()
            except RuntimeError as exc:
                log.error("Nao foi possivel ativar as hotkeys ao iniciar: %s", exc)

    try:
        window.mainloop()
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuario")
    except Exception:  # noqa: BLE001
        log.critical("Erro nao tratado:\n%s", traceback.format_exc())
        return _fatal("Erro inesperado. Detalhes em logs/app.log")
    finally:
        try:
            controller.shutdown()
        except Exception:  # noqa: BLE001
            log.exception("Falha ao encerrar")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
