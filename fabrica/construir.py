"""Fabrique tous les Reels (posts/*.mp4), leurs vignettes (portadas/*.jpg) et la file (cola.json).

Usage :  python3 construir.py              -> tout fabriquer (refuse si cola.json existe déjà)
         python3 construir.py --reanudar   -> reprendre : garde les vidéos déjà finies
         python3 construir.py --forzar     -> tout refaire (efface le registre de ce qui est publié)
         python3 construir.py --sin-voz    -> essai sans voix (aucune clé Azure nécessaire)
         python3 construir.py --solo 1,4   -> ne fabriquer que ces posts (essai)
"""
import json
import os
import subprocess
import sys
from multiprocessing import Pool

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(AQUI))
from frases import FRASES          # noqa: E402
from generar import generar, tipografia        # noqa: E402

RAIZ = os.path.dirname(AQUI)
POSTS = os.path.join(RAIZ, "posts")
PORTADAS = os.path.join(RAIZ, "portadas")
COLA = os.path.join(RAIZ, "cola.json")

TITRE = "« 101 vérités que ton hypersensibilité essaie de te dire »"
CTA_VERITE = f"Cette vérité vient de mon livre {TITRE}. Le lien est dans mon profil 📖"
CTA_TEXTE = f"Ce texte vient de mon livre {TITRE}. Le lien est dans mon profil 📖"
PARTAGE = [
    "Envoie-le à quelqu'un qui a besoin de le lire aujourd'hui.",
    "Partage-le avec quelqu'un qu'on a déjà trouvé « trop ».",
    "Enregistre-le pour le jour où tu l'oublieras.",
]
VOIX = "(voix de synthèse)"
IA = "(visuel créé par IA)"
HASHTAG_FIXE = "#hypersensibilite"
HASHTAGS = ["#hypersensible", "#hautesensibilite", "#sensibilite", "#anxiete",
            "#emotions", "#bienveillance", "#developpementpersonnel"]

# Photo du livre en main, ajoutée à la fin des Reels dont la légende renvoie au livre.
FIN_LIVRE = "libro_1.jpg"


def hashtags(k):
    tours = [HASHTAGS[(k + j) % len(HASHTAGS)] for j in range(4)]
    return " ".join([HASHTAG_FIXE] + tours)


def legende(i, f):
    """Légende du Reel n° i (0 = premier) de la banque."""
    blocs = [f["leyenda"]]
    if (i + 1) % 4 == 0:
        blocs.append(CTA_VERITE if f["n"] else CTA_TEXTE)
    elif (i + 1) % 4 == 2:
        blocs.append(PARTAGE[(i // 4) % len(PARTAGE)])
    blocs.append(VOIX)
    blocs.append(hashtags(i))
    return tipografia("\n\n".join(blocs))


def duree_valide(mp4):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                           capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:
        return None


def tache(t):
    numero, tipo, datos = t
    mp4 = os.path.join(POSTS, f"{numero:04d}.mp4")
    jpg = os.path.join(PORTADAS, f"{numero:04d}.jpg")
    f, voces, seed, fin = datos
    dur, portada = generar(f["hook"], f["texto"], mp4, jpg, seed=seed, numero=f["n"], voces=voces,
                           fin_livre=os.path.join(AQUI, FIN_LIVRE) if fin else None)
    print(f"{numero:04d} fabriqué ({dur:.1f} s)", flush=True)
    return numero, dur, portada


def main():
    args = sys.argv[1:]
    reprendre, forcer, sans_voix = "--reanudar" in args, "--forzar" in args, "--sin-voz" in args
    solo = None
    if "--solo" in args:
        solo = {int(x) for x in args[args.index("--solo") + 1].split(",")}
    if os.path.exists(COLA) and not (forcer or reprendre or solo):
        sys.exit("cola.json existe déjà : tout refaire effacerait le registre de ce qui est publié. "
                 "Utilise --reanudar pour reprendre, ou --forzar si c'est voulu.")
    os.makedirs(POSTS, exist_ok=True)
    os.makedirs(PORTADAS, exist_ok=True)

    ancienne = {}
    if reprendre and os.path.exists(COLA):
        with open(COLA, encoding="utf-8") as fh:
            ancienne = {p["archivo"]: p for p in json.load(fh)}

    # 1. la file, dans l'ordre de publication
    cola, travaux = [], []
    for i, f in enumerate(FRASES):
        n = i + 1
        fin = (i + 1) % 4 == 0                      # mêmes Reels que ceux dont la légende cite le livre
        cola.append({"archivo": f"{n:04d}.mp4", "leyenda": legende(i, f), "tipo": "frase",
                     "verite": f["n"], "hook": f["hook"].replace("*", ""), "fin_livre": fin,
                     "publicado": None})
        travaux.append((n, "frase", (f, None, 1000 + i, fin)))

    if solo:
        travaux = [t for t in travaux if t[0] in solo]
    else:                                           # vidéos d'une ancienne file qui n'existent plus
        noms = {p["archivo"] for p in cola}
        for nom in sorted(os.listdir(POSTS)):
            if nom.endswith(".mp4") and nom not in noms:
                os.remove(os.path.join(POSTS, nom))
                print(f"{nom} supprimé (n'est plus dans la file)", flush=True)

    # 2. reprise : on garde les vidéos complètes déjà fabriquées
    resultats = {}
    if reprendre:
        restants = []
        for t in travaux:
            nom = f"{t[0]:04d}.mp4"
            d = duree_valide(os.path.join(POSTS, nom))
            a = ancienne.get(nom)
            nouveau = cola[t[0] - 1]
            meme = (a is None and not ancienne) or (
                a is not None and a.get("hook") == nouveau["hook"]
                and bool(a.get("fin_livre")) == nouveau["fin_livre"])
            if d and meme:
                a = a or {}
                resultats[t[0]] = (a.get("duracion") or d, 1500)
                for cle in ("publicado", "media_id", "musica"):
                    if a.get(cle):
                        cola[t[0] - 1][cle] = a[cle]
            else:
                restants.append(t)
        print(f"Reprise : {len(resultats)} déjà faits, {len(restants)} à fabriquer.", flush=True)
        travaux = restants

    # 3. les voix (une requête Azure à la fois, à cause de la limite du palier gratuit)
    if not sans_voix:
        import voz
        total = sum(voz.caracteres(t[2][0]["hook"], t[2][0]["texto"]) for t in travaux if t[1] == "frase")
        print(f"Voix : {total} caractères à lire.", flush=True)
        prets = []
        for k, t in enumerate(travaux):
            if t[1] == "frase":
                f, _, seed, fin = t[2]
                t = (t[0], "frase", (f, voz.lire_reel(f["hook"], f["texto"]), seed, fin))
                print(f"voix {k + 1}/{len(travaux)}", flush=True)
            prets.append(t)
        travaux = prets

    # 4. les vidéos, sur tous les processeurs
    with Pool(os.cpu_count() or 2) as p:
        for n, d, c in p.imap_unordered(tache, travaux):
            resultats[n] = (d, c)
            cola[n - 1]["musica"] = None

    # 5. la musique, si des morceaux sont déjà dans musica/
    import poner_musica
    pistas = poner_musica.musiques()
    k = 0
    for post in cola:
        n = int(post["archivo"][:4])
        if n in resultats:
            post["duracion"] = round(resultats[n][0], 2)
            post["portada_ms"] = resultats[n][1]
    for post in cola:
        if int(post["archivo"][:4]) not in resultats:
            continue
        if pistas and not post.get("musica") and not post.get("publicado"):
            pista = pistas[k % len(pistas)]
            poner_musica.mezclar(os.path.join(POSTS, post["archivo"]), pista, post["duracion"],
                                 avec_voix=post["tipo"] != "libro" and not sans_voix)
            post["musica"] = os.path.basename(pista)
            k += 1
            if not solo:
                with open(COLA, "w", encoding="utf-8") as fh:        # noté au fur et à mesure
                    json.dump(cola, fh, ensure_ascii=False, indent=2)
        post.setdefault("musica", None)

    if solo:
        print("Essai --solo : cola.json n'est pas écrit.")
        return
    with open(COLA, "w", encoding="utf-8") as fh:
        json.dump(cola, fh, ensure_ascii=False, indent=2)
    print("total", len(cola))


if __name__ == "__main__":
    main()
