"""Le a barra do time do PXG na tela: qual retrato pequeno esta desmaiado.

A ordem dos retratos pequenos muda a cada troca, entao o desmaiado nao tem
lugar fixo. A barra de vida verde ao lado de cada retrato denuncia: a vazia
e a dele. So ctypes (GDI): nada de dependencia nova para ler uns pixels.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from typing import Callable, Sequence

log = logging.getLogger(__name__)

# Regiao da barra de vida em relacao ao centro do retrato pequeno (pixels).
# Botoes de calibragem: medidos nos prints do usuario em 26/09/2026.
HP_DX, HP_DY, HP_W, HP_H = 22, -18, 60, 22
# Abaixo disto a barra conta como vazia; acima de HP_ALIVE, como viva.
HP_EMPTY, HP_ALIVE = 8, 40

Grab = Callable[[int, int, int, int], bytes]


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def grab_screen(left: int, top: int, width: int, height: int) -> bytes:
    """Pixels BGRA de um retangulo da tela, linha a linha de cima para baixo."""
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    for fn in (gdi32.CreateCompatibleDC, gdi32.CreateCompatibleBitmap, gdi32.SelectObject):
        fn.restype = wintypes.HANDLE
    user32.GetDC.restype = wintypes.HANDLE
    screen = user32.GetDC(None)
    memory = gdi32.CreateCompatibleDC(wintypes.HANDLE(screen))
    bitmap = gdi32.CreateCompatibleBitmap(wintypes.HANDLE(screen), width, height)
    old = gdi32.SelectObject(wintypes.HANDLE(memory), wintypes.HANDLE(bitmap))
    try:
        gdi32.BitBlt(wintypes.HANDLE(memory), 0, 0, width, height,
                     wintypes.HANDLE(screen), left, top, 0x00CC0020)  # SRCCOPY
        header = _BitmapInfoHeader(ctypes.sizeof(_BitmapInfoHeader), width, -height, 1, 32)
        buffer = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(wintypes.HANDLE(memory), wintypes.HANDLE(bitmap), 0, height,
                        buffer, ctypes.byref(header), 0)
        return buffer.raw
    finally:
        gdi32.SelectObject(wintypes.HANDLE(memory), wintypes.HANDLE(old))
        gdi32.DeleteObject(wintypes.HANDLE(bitmap))
        gdi32.DeleteDC(wintypes.HANDLE(memory))
        user32.ReleaseDC(None, wintypes.HANDLE(screen))


def green_pixels(bgra: bytes) -> int:
    """Pixels do verde da barra de vida (o azul da barra de baixo nao conta).

    O verde do PXG e escuro: (48, 81, 45) a (57, 97, 54) nos prints.
    """
    return sum(
        1 for b, g, r in zip(bgra[0::4], bgra[1::4], bgra[2::4])
        if g > 60 and g - r > 25 and g - b > 25
    )


def find_fainted(portraits: Sequence[tuple[int, int]], grab: Grab = grab_screen) -> int | None:
    """Indice do retrato cuja barra de vida esta vazia, ou None.

    None tambem quando nada parece vivo (janela coberta, posicoes erradas):
    melhor nao clicar do que clicar no escuro.
    """
    counts = [
        green_pixels(grab(x + HP_DX, y + HP_DY, HP_W, HP_H)) for x, y in portraits
    ]
    log.info("Barras de vida (verde por retrato): %s", counts)
    if not counts or max(counts) < HP_ALIVE:
        return None
    lowest = min(range(len(counts)), key=counts.__getitem__)
    return lowest if counts[lowest] <= HP_EMPTY else None
