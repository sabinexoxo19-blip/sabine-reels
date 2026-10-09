"""Image Pinterest (1000 x 1500, format 2:3) : en haut le hook et une phrase qui tient seule (la légende) sur le papier crème,
en bas la photo du livre en main (titre bien lisible).

Essai :  python3 pin.py sortie.jpg
"""
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import generar as g                      # noqa: E402

PW, PH = 1000, 1500
HAUT_PHOTO = 740                         # bande photo en bas
FONDU = 60                               # transition douce papier → photo
PHOTO = os.path.join(AQUI, "libro_1.jpg")
CADRAGE = (0, 250, 1080, 1049)           # zone de libro_1.jpg où le titre du livre est entier


def _reglages():
    """Adapte la mise en page de generar.py au format Pinterest (le temps du dessin)."""
    anciens = {k: getattr(g, k) for k in ("W", "H", "X_MIN", "X_MAX", "CENTRO_HOOK",
                                            "ZONA_TEXTO", "Y_ETIQUETA")}
    g.W, g.H = PW, PH
    g.X_MIN, g.X_MAX = 90, 910
    g.CENTRO_HOOK = 315
    g.ZONA_TEXTO = (590, 720)
    g.Y_ETIQUETA = 110
    return anciens


def generar_pin(hook_txt, phrase, destino, numero=None, seed=1):
    anciens = _reglages()
    try:
        from PIL import ImageDraw
        d = ImageDraw.Draw(Image.new("L", (1, 1)))
        img = g.papel(seed)
        m_h, m_hk, *_ = g.hook(hook_txt, d)
        piezas, _ = g.cuerpo([phrase], d)
        m_t, m_k, _, _ = piezas[0]
        m_e = g.etiqueta(numero, d)
        poner = lambda im, a, col: im * (1 - a[..., None] * 0.96) + np.array(col, np.float32) * a[..., None] * 0.96
        img = poner(img, m_e, g.TERRA)
        img = poner(img, m_h, g.VERDE)
        img = poner(img, m_hk, g.ROJO)
        img = poner(img, m_t, g.TINTA)
        img = poner(img, m_k, g.ROJO)
    finally:
        for k, v in anciens.items():
            setattr(g, k, v)

    photo = Image.open(PHOTO).convert("RGB").crop(CADRAGE).resize((PW, HAUT_PHOTO), Image.LANCZOS)
    ph = np.asarray(photo, dtype=np.float32)
    y0 = PH - HAUT_PHOTO
    alpha = np.ones((HAUT_PHOTO, 1, 1), np.float32)
    alpha[:FONDU, 0, 0] = np.linspace(0, 1, FONDU) ** 1.5
    img[y0:] = img[y0:] * (1 - alpha) + ph * alpha
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(destino, "JPEG", quality=90, optimize=True)


if __name__ == "__main__":
    from frases import FRASES
    from pines import sans_emoji
    f = FRASES[8]
    generar_pin(f["hook"], sans_emoji(f["leyenda"]), sys.argv[1] if len(sys.argv) > 1 else "pin_test.jpg",
                numero=f["n"], seed=3)
