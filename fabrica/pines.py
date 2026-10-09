"""Fabrique les épingles Pinterest (pines/NNNN.jpg) et les fichiers CSV d'import en bloc
(Pinterest → Créer → Créer des épingles en bloc).

Usage :  python3 pines.py --base https://utilisateur.github.io/depot [--inicio 2026-10-10] [--prueba]
         --prueba : 3 épingles seulement, dans pinterest_prueba.csv
"""
import argparse
import csv
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from multiprocessing import Pool
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from frases import FRASES          # noqa: E402

RAIZ = os.path.dirname(AQUI)
DOSSIER = os.path.join(RAIZ, "pines")
LIEN = "https://www.amazon.fr/dp/B0H8PYJKFB"
LIVRE = "« 101 vérités que ton hypersensibilité essaie de te dire » de Sabine Mercier"
PARIS = ZoneInfo("Europe/Paris")
HEURES = [(12, 15), (20, 45)]       # heure de Paris ; le passage à l'heure d'hiver est calculé
PAR_CSV = 56                        # 28 jours par fichier (Pinterest programme 30 jours à l’avance au maximum)

# (tableau, préfixe du titre, mots-clés)
TABLEAUX = {
    "hyper": ("Hypersensibilité : citations et conseils", "Hypersensibilité",
              "hypersensibilité, hypersensible, haute sensibilité, citation hypersensibilité"),
    "anxiete": ("Anxiété et émotions", "Anxiété",
                "anxiété, gestion des émotions, stress, apaiser son anxiété"),
    "quotidien": ("Hypersensible au quotidien", "Hypersensible",
                  "hypersensible, fatigue émotionnelle, besoin de calme, introverti"),
    "citations": ("Citations bienveillance et développement personnel", "Citation",
                  "citation développement personnel, citations bienveillance, phrase inspirante"),
}
MOTS_ANXIETE = re.compile(r"anxi|angoiss|stress|panique|crise|alarme|inqui|peur|pire", re.I)
MOTS_QUOTIDIEN = re.compile(r"soirée|bruit|lampe|café|néon|fatigu|épuis|solitude|repos|lumi|nuit|soir", re.I)


def sans_emoji(t):
    t = "".join(c for c in t if unicodedata.category(c) not in ("So", "Sk", "Cs", "Mn") or c in "’«»")
    t = t.replace("️", "")
    return re.sub(r"\s+", " ", t).strip()


def propre(t):
    return re.sub(r"\s+", " ", t.replace("*", "").replace("\n", " ")).strip()


def tableau(i, f):
    txt = f["hook"] + " " + " ".join(f["texto"])
    if MOTS_ANXIETE.search(f["hook"]):
        return "anxiete"
    if MOTS_QUOTIDIEN.search(f["hook"]):
        return "quotidien"
    if MOTS_ANXIETE.search(txt) and i % 2:
        return "anxiete"
    return ["hyper", "citations"][i % 2]


def titre(f, cle):
    h = propre(f["hook"]).rstrip(".")
    k = next((j for j, c in enumerate(h) if c.isalpha()), 0)
    if not h[k:].startswith(("J’", "J'", "« ")) and not h[k:k + 2].isupper():
        h = h[:k] + h[k].lower() + h[k + 1:]
    t = f"{TABLEAUX[cle][1]} : {h}".replace("'", "’")
    return t if len(t) <= 100 else t[:97].rsplit(" ", 1)[0] + "…"


def description(f):
    d = (f"{propre(f['hook'])} {sans_emoji(f['leyenda'])} "
         f"Une vérité du livre {LIVRE}, pour celles et ceux qu’on a toujours trouvés « trop ». "
         f"Enregistre-la pour les jours où tu en as besoin.")
    return d.replace("'", "’")[:500]


def tache(i):
    from pin import generar_pin
    f = FRASES[i]
    generar_pin(f["hook"], sans_emoji(f["leyenda"]), os.path.join(DOSSIER, f"{i + 1:04d}.jpg"),
                numero=f["n"], seed=2000 + i)
    return i


def date_utc(jour, h, m):
    local = datetime(jour.year, jour.month, jour.day, h, m, tzinfo=PARIS)
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--inicio", default="")
    ap.add_argument("--prueba", action="store_true")
    a = ap.parse_args()
    debut = date.fromisoformat(a.inicio) if a.inicio else date.today() + timedelta(days=1)

    os.makedirs(DOSSIER, exist_ok=True)
    indices = list(range(3)) if a.prueba else list(range(len(FRASES)))
    a_faire = [i for i in indices if a.prueba or not os.path.exists(os.path.join(DOSSIER, f"{i + 1:04d}.jpg"))]
    with Pool(os.cpu_count() or 2) as p:
        for i in p.imap_unordered(tache, a_faire):
            print(f"épingle {i + 1:04d}", flush=True)

    lignes = []
    for n, i in enumerate(indices):
        f = FRASES[i]
        cle = tableau(i, f)
        jour = debut + timedelta(days=n // len(HEURES))
        h, m = HEURES[n % len(HEURES)]
        lignes.append({
            "Title": titre(f, cle),
            "Media URL": f"{a.base.rstrip('/')}/pines/{i + 1:04d}.jpg",
            "Pinterest board": TABLEAUX[cle][0],
            "Thumbnail": "",
            "Description": description(f),
            "Link": f"{LIEN}/ref=pin_{i + 1:04d}",       # un lien différent par épingle
            "Publish date": date_utc(jour, h, m),
            "Keywords": TABLEAUX[cle][2],
        })

    groupes = [lignes] if a.prueba else [lignes[k:k + PAR_CSV] for k in range(0, len(lignes), PAR_CSV)]
    for g_i, groupe in enumerate(groupes, start=1):
        nom = "pinterest_prueba.csv" if a.prueba else f"pinterest_mois{g_i}.csv"
        with open(os.path.join(RAIZ, nom), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(groupe[0].keys()))
            w.writeheader()
            w.writerows(groupe)
        print(nom, len(groupe), "épingles, du", groupe[0]["Publish date"], "au", groupe[-1]["Publish date"], "(UTC)")


if __name__ == "__main__":
    main()
