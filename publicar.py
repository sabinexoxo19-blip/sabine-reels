"""Publie sur Instagram le Reel suivant de cola.json.

Variables de entorno:
  IG_TOKEN        token de larga duración (API de Instagram con inicio de sesión de Instagram)
  BASE_URL        dirección pública de la web del repositorio (por defecto: https://<usuario>.github.io/<repo>)
  DRY_RUN=1       no publica nada, solo muestra lo que haría
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://graph.instagram.com"
RAIZ = os.path.dirname(os.path.abspath(__file__))
COLA = os.path.join(RAIZ, "cola.json")
AVISO_COLA_BAJA = 12          # moins de 3 jours de Reels à 4 par jour

# Créneaux de publication, heure de Paris. Le robot est réveillé toutes les 30 minutes par GitHub
# (dont les horaires programmés peuvent avoir des heures de retard) et ne publie que si un créneau
# est passé depuis la dernière publication.
PARIS = ZoneInfo("Europe/Paris")
CRENEAUX = [(8, 12), (13, 12), (19, 12), (21, 42)]
RETARD_MAX = timedelta(hours=2)     # créneau manqué depuis plus longtemps : on attend le suivant
ECART_MIN = timedelta(hours=2)      # jamais deux Reels à moins de 2 h d'écart


def creneau_courant(maintenant):
    """Dernier créneau passé (heure de Paris) avant « maintenant »."""
    m = maintenant.astimezone(PARIS)
    for jour in (m, m - timedelta(days=1)):
        passes = [jour.replace(hour=h, minute=mi, second=0, microsecond=0) for h, mi in CRENEAUX]
        passes = [c for c in passes if c <= m]
        if passes:
            return passes[-1]


def faut_il_publier(cola, maintenant):
    """(True/False, raison) pour un réveil automatique."""
    dates = [datetime.strptime(p["publicado"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
             for p in cola if p.get("publicado")]
    derniere = max(dates) if dates else None
    creneau = creneau_courant(maintenant)
    if derniere and derniere >= creneau:
        return False, f"le créneau de {creneau:%H:%M} est déjà servi"
    if maintenant - creneau > RETARD_MAX:
        return False, f"créneau de {creneau:%H:%M} trop ancien, on attend le suivant"
    if derniere and maintenant - derniere < ECART_MIN:
        return False, "dernière publication il y a moins de 2 h"
    return True, f"créneau de {creneau:%H:%M}"


def llamar(metodo, ruta, **params):
    url = f"{API}/{ruta}"
    datos = urllib.parse.urlencode(params).encode()
    if metodo == "GET":
        req = urllib.request.Request(url + "?" + datos.decode())
    else:
        req = urllib.request.Request(url, data=datos, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode(errors="replace")
        sys.exit(f"ERROR API {metodo} {ruta}: {e.code} {cuerpo}")


def base_url():
    if os.environ.get("BASE_URL"):
        return os.environ["BASE_URL"].rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        sys.exit("Il manque BASE_URL (ou lancer depuis GitHub Actions).")
    usuario, nombre = repo.split("/")
    return f"https://{usuario.lower()}.github.io/{nombre}"


def comprobar_url(url):
    """Comprueba que el vídeo es accesible públicamente antes de pedírselo a Instagram."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def marcar(cola, post, media_id):
    post["publicado"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    post["media_id"] = media_id
    with open(COLA, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)


def main():
    if not os.path.exists(COLA):
        print("Pas encore de Reels : lance d'abord « Fabriquer les Reels » dans l'onglet Actions.")
        return
    with open(COLA, encoding="utf-8") as f:
        cola = json.load(f)

    pendientes = [p for p in cola if not p.get("publicado")]
    if os.environ.get("AUTO") == "1":
        ok, raison = faut_il_publier(cola, datetime.now(timezone.utc))
        print(f"Réveil automatique : {raison}.")
        if not ok:
            return
    if not pendientes:
        sys.exit("La file est vide : plus rien à publier. Il faut ajouter de nouveaux Reels.")
    post = pendientes[0]
    url_video = f"{base_url()}/posts/{post['archivo']}"
    dry = os.environ.get("DRY_RUN") == "1"

    print(f"Suivant : {post['archivo']} ({len(pendientes)} en attente)")
    print(f"Vidéo : {url_video}")
    print("Légende :\n" + post["leyenda"])
    if not comprobar_url(url_video):
        sys.exit("La vidéo n'est pas accessible à cette adresse. GitHub Pages est-il activé (Settings → Pages) ?")
    print("La vidéo est accessible publiquement ✔")
    if dry:
        print("ESSAI : rien n'est publié.")
        return

    token = os.environ["IG_TOKEN"]
    yo = llamar("GET", "me", fields="user_id,username", access_token=token)
    ig_id = yo.get("user_id") or yo["id"]

    # anti-duplicado: si una publicación reciente ya tiene esta leyenda, solo se marca
    recientes = llamar("GET", f"{ig_id}/media", fields="id,caption", limit=3, access_token=token)
    for m in recientes.get("data", []):
        if (m.get("caption") or "").strip() == post["leyenda"].strip():
            print("Déjà publié (anti-doublon) : on le note et on s'arrête.")
            marcar(cola, post, m["id"])
            return

    # 1. contenedor del Reel
    cont = llamar("POST", f"{ig_id}/media", media_type="REELS", video_url=url_video,
                  caption=post["leyenda"], share_to_feed="true",
                  thumb_offset=str(post.get("portada_ms", 0)), access_token=token)
    cid = cont["id"]

    # 2. esperar a que Instagram procese el vídeo (hasta 10 minutos)
    for _ in range(60):
        estado = llamar("GET", cid, fields="status_code,status", access_token=token)
        codigo = estado.get("status_code")
        if codigo == "FINISHED":
            break
        if codigo in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram n'a pas pu traiter la vidéo : {estado}")
        time.sleep(10)
    else:
        sys.exit(f"La vidéo {cid} n'a pas fini d'être traitée à temps.")

    # 3. publicar
    pub = llamar("POST", f"{ig_id}/media_publish", creation_id=cid, access_token=token)
    print(f"Publié sur @{yo.get('username')} : media {pub['id']}")
    marcar(cola, post, pub["id"])

    if len(pendientes) - 1 < AVISO_COLA_BAJA:
        print(f"::warning::Il reste {len(pendientes) - 1} Reels dans la file.")


if __name__ == "__main__":
    main()
