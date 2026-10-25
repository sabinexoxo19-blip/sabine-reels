"""Publie sur YouTube (Shorts) la vidéo suivante de cola_youtube.json.

Même réveil que les Reels (toutes les 30 min) ; ne publie qu'aux créneaux ci-dessous (heure de Paris).
Secrets GitHub : YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
DRY_RUN=1 : essai sans rien publier.  AUTO=1 : réveil automatique (respecte les créneaux).
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

RAIZ = os.path.dirname(os.path.abspath(__file__))
COLA = os.path.join(RAIZ, "cola_youtube.json")
PARIS = ZoneInfo("Europe/Paris")
CRENEAUX = [(13, 12), (19, 42)]          # 2 Shorts par jour
RETARD_MAX = timedelta(hours=2)
ECART_MIN = timedelta(hours=3)


def creneau_courant(m):
    m = m.astimezone(PARIS)
    for jour in (m, m - timedelta(days=1)):
        c = [jour.replace(hour=h, minute=mi, second=0, microsecond=0) for h, mi in CRENEAUX]
        c = [x for x in c if x <= m]
        if c:
            return c[-1]


def faut_il(cola, maintenant):
    dates = [datetime.strptime(p["publie"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
             for p in cola if p.get("publie")]
    derniere = max(dates) if dates else None
    c = creneau_courant(maintenant)
    if derniere and derniere >= c:
        return False, f"créneau de {c:%H:%M} déjà servi"
    if maintenant - c > RETARD_MAX:
        return False, f"créneau de {c:%H:%M} trop ancien, on attend le suivant"
    if derniere and maintenant - derniere < ECART_MIN:
        return False, "dernière vidéo il y a moins de 3 h"
    return True, f"créneau de {c:%H:%M}"


def http(req):
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.headers, r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ERREUR YouTube {e.code} : {e.read().decode(errors='replace')}")


def jeton():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    _, corps = http(urllib.request.Request("https://oauth2.googleapis.com/token", data=data))
    return json.loads(corps)["access_token"]


def main():
    if not os.path.exists(COLA):
        print("YouTube : pas de file cola_youtube.json, rien à faire.")
        return
    cola = json.load(open(COLA, encoding="utf-8"))
    attente = [p for p in cola if not p.get("publie")]
    if os.environ.get("AUTO") == "1":
        ok, raison = faut_il(cola, datetime.now(timezone.utc))
        print(f"YouTube — réveil automatique : {raison}.")
        if not ok:
            return
    if not attente:
        print("::warning::YouTube : toutes les vidéos sont publiées.")
        return
    post = attente[0]
    chemin = os.path.join(RAIZ, "posts", post["archivo"])
    if not os.path.exists(chemin):
        sys.exit(f"Vidéo introuvable : posts/{post['archivo']}")
    print(f"YouTube — suivante : {post['archivo']} ({len(attente)} en attente)\nTitre : {post['titre']}")
    if not os.environ.get("YT_REFRESH_TOKEN"):
        print("::warning::YouTube : les clés YT_… ne sont pas encore installées, on passe.")
        return
    acces = jeton()                      # vérifie aussi que les 3 clés sont bonnes
    if os.environ.get("DRY_RUN") == "1":
        print("Clés YouTube valides ✔\nESSAI YouTube : rien n'est publié.")
        return

    meta = {"snippet": {"title": post["titre"], "description": post["description"], "tags": post["tags"],
                        "categoryId": "22", "defaultLanguage": "fr", "defaultAudioLanguage": "fr"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True}}
    taille = os.path.getsize(chemin)
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(), method="POST",
        headers={"Authorization": f"Bearer {acces}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(taille)})
    entetes, _ = http(req)
    with open(chemin, "rb") as f:
        req = urllib.request.Request(entetes["Location"], data=f.read(), method="PUT",
                                     headers={"Content-Type": "video/mp4", "Content-Length": str(taille)})
    _, corps = http(req)
    vid = json.loads(corps)["id"]
    print(f"Publié sur YouTube : https://youtube.com/shorts/{vid}")
    post["publie"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    post["video_id"] = vid
    json.dump(cola, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
