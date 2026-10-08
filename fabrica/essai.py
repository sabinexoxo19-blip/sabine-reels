"""Essai du format B : fabrique quelques Reels dans essais/ pour une publication à la main.

Usage : python3 essai.py 9,90,115
Les numéros sont ceux de la file (posts/NNNN.mp4). Les Reels pas encore publiés sont marqués
« publié à la main » dans cola.json, pour que le robot ne les publie pas une deuxième fois.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(AQUI))
from frases import FRASES              # noqa: E402
from generar_b import generar          # noqa: E402
from construir import legende, FIN_LIVRE   # noqa: E402
import voz                             # noqa: E402
import poner_musica                    # noqa: E402

RAIZ = os.path.dirname(AQUI)
SORTIE = os.path.join(RAIZ, "essais")
COLA = os.path.join(RAIZ, "cola.json")


def main():
    numeros = [int(x) for x in sys.argv[1].replace(" ", "").split(",") if x]
    os.makedirs(SORTIE, exist_ok=True)
    with open(COLA, encoding="utf-8") as fh:
        cola = json.load(fh)
    pistas = poner_musica.musiques()
    for k, n in enumerate(numeros):
        f = FRASES[n - 1]
        voces = [voz.lire(f["hook"], "+0%")] + [voz.lire(p, "-8%") for p in f["texto"]]
        mp4 = os.path.join(SORTIE, f"{n:04d}.mp4")
        jpg = os.path.join(SORTIE, f"{n:04d}.jpg")
        fin = os.path.join(AQUI, FIN_LIVRE) if n % 4 == 0 else None
        dur, _ = generar(f["hook"], f["texto"], mp4, jpg, seed=999 + n, numero=f["n"], voces=voces, fin_livre=fin)
        if pistas:
            poner_musica.mezclar(mp4, pistas[(n + k) % len(pistas)], dur, avec_voix=True)
        with open(os.path.join(SORTIE, f"{n:04d}.txt"), "w", encoding="utf-8") as fh:
            fh.write(legende(n - 1, f) + "\n")
        post = cola[n - 1]
        if not post.get("publicado"):
            post["publicado"] = "2000-01-01T00:00:00Z"     # date fictive : publié à la main
            post["media_id"] = "manuel-essai-B"
        print(f"essais/{n:04d}.mp4 prêt ({dur:.1f} s)", flush=True)
    with open(COLA, "w", encoding="utf-8") as fh:
        json.dump(cola, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
