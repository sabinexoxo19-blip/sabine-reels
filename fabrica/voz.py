"""Voix de synthèse (Azure Speech) : un MP3 par morceau de texte (hook, puis chaque paragraphe).

Variables d'environnement (secrets GitHub) :
  AZURE_SPEECH_KEY      clé de la ressource Azure Speech
  AZURE_SPEECH_REGION   région de la ressource, par exemple « westeurope »

Les MP3 sont gardés dans .voz_cache/ (jamais publiés) : relancer la fabrication ne repaie pas
les caractères déjà lus. Le palier gratuit F0 accepte 20 requêtes par minute : on en envoie
au plus une toutes les 3,2 secondes et on attend puis réessaie en cas de refus (429).
"""
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

VOIX = "fr-FR-VivienneMultilingualNeural"
DEBIT = "-14%"                       # Vivienne ralentie (validée)
FORMAT = "audio-48khz-192kbitrate-mono-mp3"
PAUSE_MIN = 3.2                      # secondes entre deux requêtes (F0 : 20 par minute)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RAIZ, ".voz_cache")
_derniere = [0.0]


def texte_parle(t):
    """Texte tel qu'il doit être lu : sans retours à la ligne ni astérisques."""
    t = t.replace("*", "").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def ssml(t, debit=DEBIT):
    return ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='fr-FR'>"
            f"<voice name='{VOIX}'><prosody rate='{debit}'>"
            f"{escape(texte_parle(t))}</prosody></voice></speak>")


def _url():
    if os.environ.get("AZURE_SPEECH_ENDPOINT"):          # seulement pour les essais
        return os.environ["AZURE_SPEECH_ENDPOINT"]
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip().lower()
    if not region:
        sys.exit("Il manque le secret AZURE_SPEECH_REGION (ici swedencentral).")
    return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


def lire(texte, debit=DEBIT):
    """Renvoie le chemin d'un MP3 où Vivienne lit ce texte (le crée si besoin)."""
    os.makedirs(CACHE, exist_ok=True)
    cle_cache = hashlib.sha1(f"{VOIX}|{debit}|{texte_parle(texte)}".encode()).hexdigest()[:16]
    chemin = os.path.join(CACHE, cle_cache + ".mp3")
    if os.path.exists(chemin) and os.path.getsize(chemin) > 1000:
        return chemin

    cle = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    if not cle:
        sys.exit("Il manque le secret AZURE_SPEECH_KEY : la voix ne peut pas être fabriquée.")
    corps = ssml(texte, debit).encode("utf-8")
    for essai in range(8):
        attente = PAUSE_MIN - (time.time() - _derniere[0])
        if attente > 0:
            time.sleep(attente)
        _derniere[0] = time.time()
        req = urllib.request.Request(_url(), data=corps, method="POST", headers={
            "Ocp-Apim-Subscription-Key": cle,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": FORMAT,
            "User-Agent": "sabine-reels",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                audio = r.read()
            if len(audio) < 1000:
                raise RuntimeError("réponse audio vide")
            with open(chemin + ".tmp", "wb") as f:
                f.write(audio)
            os.replace(chemin + ".tmp", chemin)
            return chemin
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                sys.exit("Azure refuse la clé (erreur %d). Vérifie AZURE_SPEECH_KEY et AZURE_SPEECH_REGION "
                         "(la région doit être celle de la ressource)." % e.code)
            if e.code == 400:
                sys.exit("Azure refuse la demande (erreur 400) pour le texte : " + texte_parle(texte))
            pause = int(e.headers.get("Retry-After") or 0) or 20 * (essai + 1)
            print(f"Azure occupé (erreur {e.code}), nouvel essai dans {pause} s", flush=True)
            time.sleep(pause)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
            print(f"Problème réseau ({e}), nouvel essai", flush=True)
            time.sleep(10 * (essai + 1))
    sys.exit("Azure n'a pas répondu après plusieurs essais. Relance « Fabricar los Reels » plus tard : "
             "ce qui est déjà fait est gardé.")


def lire_reel(hook, paragraphes):
    """Un MP3 pour le hook, puis un par paragraphe."""
    return [lire(hook)] + [lire(p) for p in paragraphes]


def caracteres(hook, paragraphes):
    return sum(len(texte_parle(t)) for t in [hook, *paragraphes])
