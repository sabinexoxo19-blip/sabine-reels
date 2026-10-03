# Robot Instagram — @sabine_hypersensible

Ce dossier contient un **robot** qui fabrique **123 Reels** (120 vérités lues par une voix + 3 photos du livre, environ 31 jours), puis **les publie tout seul, 4 fois par jour**. Ton ordinateur n'a pas besoin d'être allumé.

Livre : *101 vérités que ton hypersensibilité essaie de te dire* — https://www.amazon.fr/dp/B0H8PYJKFB

---

## Comment ça marche

1. **GitHub** (gratuit) garde le robot et le réveille aux bonnes heures.
2. **Azure** (Microsoft) prête sa voix « Vivienne » pour lire les textes. Le palier gratuit suffit : 120 Reels font environ 44 000 caractères, et le gratuit en donne 500 000 par mois.
3. Le robot fabrique toutes les vidéos une seule fois (1 à 3 heures), puis en donne une à Instagram à chaque réveil.

Publication : **8 h 12, 13 h 12, 19 h 12 et 21 h 42, heure de Paris** (le changement d'heure est géré tout seul).

---

## Les 4 clés secrètes (à mettre dans GitHub, jamais ailleurs)

| Nom | Ce que c'est | Où on la trouve |
|---|---|---|
| `AZURE_SPEECH_KEY` | la clé de la voix | portail Azure, ta ressource Speech, « Clés et point de terminaison », **CLÉ 1** |
| `AZURE_SPEECH_REGION` | la région de la voix | même page, champ **Emplacement/Région** (ici `swedencentral`) |
| `IG_TOKEN` | la clé Instagram | developers.facebook.com, ton app, « Générer un token » |
| `GH_PAT` | la clé qui permet au robot de prolonger la clé Instagram | GitHub, Settings, Developer settings, Fine-grained tokens |

Elles se rangent dans : ton dépôt, **Settings**, **Secrets and variables**, **Actions**, **New repository secret**.

---

## Les automatismes (onglet Actions)

| Nom | Quand | Rôle |
|---|---|---|
| **Fabriquer les Reels** | à la main, une fois | fabrique les vidéos (dossier `posts`) et la file `cola.json`. S'il s'arrête en route, on le relance : il reprend où il en était. |
| **Publier sur Instagram** | 4 fois par jour | publie le Reel suivant. À la main : **1** = essai sans rien publier, **0** = publier pour de vrai. |
| **Renouveler la clé Instagram** | chaque lundi | prolonge la clé Instagram de 60 jours. Ne marche que si la clé a plus de 24 heures. |
| **Ajouter la musique** | quand tu ajoutes des musiques | glisse une musique douce sous la voix des Reels pas encore publiés. |

---

## La musique (facultatif)

Instagram ne permet pas au robot d'utiliser les musiques à la mode de l'appli. On met donc des musiques libres :

1. Sur **pixabay.com/music**, cherche « soft piano », « calm acoustic » ou « lofi calm ».
2. Télécharge **3 à 5 morceaux doux** en MP3. Si la page d'un morceau parle de « Content ID », prends-en un autre.
3. Mets-les dans le dossier **musica**.

L'idéal est de les mettre **avant** la fabrication : la musique est alors mixée directement. Si tu les ajoutes après, le robot refait le son des Reels pas encore publiés (cela alourdit un peu le dépôt).

La musique est mise au même niveau pour tous les morceaux, puis jouée bien en dessous de la voix.

---

## Les mentions obligatoires

- Chaque Reel lu par Vivienne porte **(voix de synthèse)** dans la légende.
- Les Reels avec la photo du canapé portent **(visuel créé par IA)**.

Ne les retire pas : Meta demande de signaler les voix et les images réalistes créées par IA.

---

## Au quotidien

- **Rien à faire.** Tu peux répondre aux commentaires depuis ton téléphone comme d'habitude.
- Pour voir ce qui s'est passé : onglet **Actions**. ✅ vert = publié, ❌ rouge = problème (GitHub t'envoie aussi un e-mail).
- **Le compte Azure gratuit est désactivé au bout de 30 jours** si tu ne le passes pas en « paiement à l'utilisation ». La voix n'est utilisée qu'à la fabrication, donc ça ne gêne pas ce lot. Pour le lot suivant, il faudra faire ce passage : la ressource reste en palier **F0 gratuit**, donc 0 € tant qu'on reste sous 500 000 caractères par mois.
- Quand la file arrive au bout, **Publier sur Instagram** s'arrête en rouge avec « La file est vide ». Il faut alors un nouveau lot de Reels.

---

## En cas de problème

| Message dans Actions | Que faire |
|---|---|
| « Il manque le secret AZURE_SPEECH_KEY » ou « …REGION » | ajoute le secret qui manque, puis relance **Fabriquer les Reels** |
| « Azure refuse la clé (erreur 401) » | la clé ou la région est fausse : recopie-les depuis le portail Azure |
| « La vidéo n'est pas accessible à cette adresse » | GitHub Pages n'est pas activé, ou attend encore 2 minutes |
| « ERROR API … 190 » ou « … OAuthException » | la clé Instagram a expiré : refais-en une et remplace `IG_TOKEN` |
| « La file est vide » | il faut un nouveau lot de Reels |

---

Polices libres (licence SIL OFL, fichiers dans `fabrica/licences`) : DM Serif Display, EB Garamond, Caveat, Jost.
