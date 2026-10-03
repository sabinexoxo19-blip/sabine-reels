"""Glisse une musique douce SOUS la voix des Reels pas encore publiés.

Les musiques sont les .mp3 / .m4a / .wav / .aac du dossier musica/, distribuées à tour de rôle.
La voix reste devant : chaque musique est d'abord mise au même niveau, puis jouée 15 dB sous la voix
(qui est à -16 LUFS). Sous les Reels photo du livre, sans voix, elle est jouée à -18 LUFS.
Les Reels déjà publiés et ceux qui ont déjà leur musique ne sont pas touchés.
Seul le son est refait : l'image est copiée telle quelle.
"""
import glob
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
COLA = os.path.join(RAIZ, "cola.json")
LUFS_SOUS_VOIX = -31
LUFS_SANS_VOIX = -18


def musiques():
    return sorted(p for ext in ("mp3", "m4a", "wav", "aac")
                  for p in glob.glob(os.path.join(RAIZ, "musica", f"*.{ext}")))


def mezclar(mp4, pista, duracion, avec_voix=True):
    """Remplace le son de mp4 par : voix d'origine + musique en fond."""
    lufs = LUFS_SOUS_VOIX if avec_voix else LUFS_SANS_VOIX
    dur = float(duracion)
    filtre = (f"[1:a]atrim=0:{dur:.3f},asetpts=N/SR/TB,loudnorm=I={lufs}:TP=-2:LRA=11,"
              f"aresample=48000,aformat=channel_layouts=stereo,"
              f"afade=t=in:d=1,afade=t=out:st={max(0.5, dur - 2):.3f}:d=2[m];"
              f"[0:a]aresample=48000,aformat=channel_layouts=stereo[v];"
              f"[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    tmp = mp4 + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-stream_loop", "-1", "-i", pista,
                    "-filter_complex", filtre, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-t", f"{dur:.3f}",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, mp4)


def main():
    pistas = musiques()
    if not pistas:
        print("Pas de musique dans le dossier musica/ : rien à faire.")
        return
    if not os.path.exists(COLA):
        print("Les Reels ne sont pas encore fabriqués : la musique sera ajoutée pendant la fabrication.")
        return
    with open(COLA, encoding="utf-8") as f:
        cola = json.load(f)

    noms = {os.path.basename(p) for p in pistas}
    faits = 0
    a_faire = [p for p in cola if not p.get("publicado") and p.get("musica") not in noms]
    for i, post in enumerate(a_faire):
        pista = pistas[i % len(pistas)]
        mp4 = os.path.join(RAIZ, "posts", post["archivo"])
        if post.get("musica"):
            print(f"{post['archivo']} a déjà une musique qui n'est plus dans musica/ : on la laisse.")
            continue
        mezclar(mp4, pista, post.get("duracion") or 10, avec_voix=post.get("tipo") != "libro")
        post["musica"] = os.path.basename(pista)
        faits += 1
        print(f"{post['archivo']} ← {post['musica']}", flush=True)

    with open(COLA, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)
    print(f"Musique ajoutée à {faits} Reels.")


if __name__ == "__main__":
    sys.exit(main())
