# ChopeTheNews

Outil de veille d'actualités en ligne de commande. Il récupère toutes les news des **X derniers jours** sur une liste de sites et sur des recherches Google News, les classe **par thème**, supprime les doublons et génère un **rapport Markdown** lisible.

Aucun serveur, aucun compte, aucune clé API : tout tourne en local depuis un simple `git clone`.

---

## Sommaire

- [Comment ça marche](#comment-ça-marche)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Le rapport](#le-rapport)
- [Astuces](#astuces)
- [Structure du projet](#structure-du-projet)
- [Limites connues](#limites-connues)

---

## Comment ça marche

```
config.yaml
   │
   ├─ sites (flux RSS) ───────┐
   │                          ├─► collecte ─► filtre par date ─► base SQLite ─► rapport Markdown
   └─ recherches (Google News)┘                                 (dédoublonnage)   rapports/veille_AAAA-MM-JJ.md
```

1. **Collecte** : pour chaque thème, l'app lit les flux RSS des sites listés et lance les recherches sur Google News (via son flux RSS public, `news.google.com/rss/search`). Tout est récupéré en parallèle.
2. **Filtre** : seuls les articles publiés pendant la période demandée (`periode_jours`) sont gardés.
3. **Stockage** : les articles sont enregistrés dans une base SQLite locale (`data/veille.db`). Un article déjà vu (même URL) n'est pas ajouté une deuxième fois, donc tu peux lancer l'outil plusieurs fois par jour sans créer de doublons.
4. **Rapport** : un fichier Markdown est généré avec tous les articles de la période, groupés par thème et triés du plus récent au plus ancien.

---

## Installation

### Prérequis

Il faut deux outils, à installer une seule fois par ordinateur :

| Outil | Rôle | Installation |
|---|---|---|
| **git** | Récupérer le projet depuis GitHub | https://git-scm.com/downloads |
| **uv** | Gérer Python et les dépendances | voir ci-dessous |

Pour installer **uv** :

- **Windows** (PowerShell) :
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **macOS / Linux** :
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

Inutile d'installer Python à part : uv télécharge automatiquement la bonne version s'il n'en trouve pas.

> Si uv a été installé avec `pip install uv`, la commande `uv` n'est peut-être pas dans le PATH. Dans ce cas, remplace `uv` par `python -m uv` dans toutes les commandes ci-dessous.

### Récupérer le projet

```bash
git clone https://github.com/Benjamin-Schacher/ChopeTheNews.git
cd ChopeTheNews
uv sync
```

`uv sync` crée un environnement isolé (`.venv/`) dans le dossier du projet et y installe les dépendances. Rien n'est installé ailleurs sur la machine.

### Créer sa config perso

```bash
cp config.example.yaml config.yaml
```

Sous Windows : `copy config.example.yaml config.yaml`

Ensuite, édite `config.yaml` (voir [Configuration](#configuration)). Ce fichier **n'est pas envoyé sur GitHub** : chacun garde sa propre config sur sa machine.

---

## Configuration

Toute la configuration est dans `config.yaml`. Exemple commenté :

```yaml
# Nombre de jours en arrière à couvrir
periode_jours: 7

# Langue et pays des résultats Google News
google_news:
  langue: fr      # en, de, es...
  pays: FR        # US, BE, CH, CA...

# true = télécharge chaque article pour récupérer son texte complet (plus lent)
# false = garde le résumé fourni par le flux RSS
extraire_contenu: false

# Où écrire les rapports et la base de données
dossier_rapports: rapports
base_de_donnees: data/veille.db

# Tes thèmes de veille : autant que tu veux, avec le nom que tu veux
themes:
  tech:
    sites:                      # URLs de flux RSS / Atom
      - https://www.numerama.com/feed/
      - https://www.lemonde.fr/pixels/rss_full.xml
    recherches:                 # requêtes envoyées à Google News
      - '"intelligence artificielle"'
      - cybersécurité

  energie:
    sites:
      - https://www.connaissancedesenergies.org/rss.xml
    recherches:
      - '"hydrogène vert"'
```

| Clé | Obligatoire | Défaut | Description |
|---|---|---|---|
| `periode_jours` | non | `7` | Nombre de jours couverts par la veille |
| `google_news.langue` | non | `fr` | Langue des résultats Google News |
| `google_news.pays` | non | `FR` | Pays des résultats Google News |
| `extraire_contenu` | non | `false` | Récupère le texte complet des articles |
| `dossier_rapports` | non | `rapports` | Dossier de sortie des rapports |
| `base_de_donnees` | non | `data/veille.db` | Fichier de la base SQLite |
| `themes` | **oui** | | Dictionnaire `nom_du_theme: { sites, recherches }` |

Un thème peut ne contenir que des `sites`, que des `recherches`, ou les deux.

---

## Utilisation

Depuis le dossier du projet :

```bash
uv run veille
```

Options :

| Option | Effet | Exemple |
|---|---|---|
| `-j N`, `--jours N` | Remplace `periode_jours` pour cette exécution | `uv run veille -j 1` |
| `-c FICHIER`, `--config FICHIER` | Utilise un autre fichier de config | `uv run veille -c config_boulot.yaml` |
| `-h` | Affiche l'aide | `uv run veille -h` |

Exemple de sortie :

```
Collecte sur 3 jour(s)...
  Numerama : 15 article(s)
  Pixels : Toute l'actualité sur Le Monde.fr. : 12 article(s)
  "cybersécurité when:3d" - Google Actualités : 100 article(s)
  ...
273 article(s) trouvé(s), dont 271 nouveau(x).
Rapport : rapports/veille_2026-10-25.md
```

> Plusieurs configs : tu peux avoir un fichier par usage (`config_perso.yaml`, `config_boulot.yaml`...) et choisir avec `-c`. Pense à les ajouter au `.gitignore` si tu ne veux pas les publier.

---

## Le rapport

Chaque exécution écrit (ou réécrit) le fichier `rapports/veille_AAAA-MM-JJ.md` :

```markdown
# Veille du 2026-10-25

271 article(s) sur les 3 derniers jours.

## tech (227)

### [Titre de l'article](https://lien-vers-l-article)
*Numerama — 2026-10-25*

Début du résumé de l'article…
```

Le Markdown s'ouvre dans n'importe quel éditeur (VS Code, Obsidian, Notepad++...) et s'affiche bien sur GitHub.

La base `data/veille.db` garde l'historique de tous les articles déjà vus. Elle s'ouvre avec n'importe quel outil SQLite, par exemple [DB Browser for SQLite](https://sqlitebrowser.org/). Pour repartir de zéro, il suffit de supprimer le dossier `data/`.

---

## Astuces

### Trouver le flux RSS d'un site

- Cherche une icône RSS ou un lien « RSS » / « Flux », souvent en bas de page.
- Essaie d'ajouter `/feed`, `/rss`, `/rss.xml` ou `/feed.xml` à l'adresse du site.
- Les sites WordPress ont presque toujours `https://site.com/feed/`.
- Beaucoup de sites proposent un flux par rubrique (par exemple Le Monde : `https://www.lemonde.fr/<rubrique>/rss_full.xml`).

### Bien écrire ses recherches Google News

La syntaxe de recherche Google fonctionne :

| Syntaxe | Effet | Exemple |
|---|---|---|
| `"..."` | Expression exacte | `'"hydrogène vert"'` |
| `-mot` | Exclure un mot | `'cybersécurité -formation'` |
| `OR` | L'un ou l'autre | `'"voiture électrique" OR "véhicule électrique"'` |
| `site:` | Limiter à un site | `'IA site:lesechos.fr'` |
| `intitle:` | Le mot doit être dans le titre | `'intitle:nucléaire'` |

⚠️ Sans guillemets, Google interprète la requête très librement. Mets les expressions de plusieurs mots entre guillemets, et entoure toute la ligne d'apostrophes en YAML : `'"hydrogène vert"'`.

### Lancer la veille automatiquement

- **Windows** : Planificateur de tâches, avec une tâche qui exécute `uv run veille` dans le dossier du projet.
- **macOS / Linux** : une ligne `cron`, par exemple `0 8 * * * cd ~/ChopeTheNews && uv run veille`.

---

## Structure du projet

```
ChopeTheNews/
├── config.example.yaml   # modèle de config (versionné)
├── config.yaml           # ta config perso (NON versionnée)
├── pyproject.toml        # dépendances et commande `veille`
├── uv.lock               # versions exactes des dépendances
├── src/veille/
│   ├── cli.py            # point d'entrée : options et enchaînement des étapes
│   ├── config.py         # lecture et validation de config.yaml
│   ├── collecte.py       # lecture des flux RSS et Google News
│   ├── stockage.py       # base SQLite et dédoublonnage
│   └── rapport.py        # génération du rapport Markdown
├── data/                 # base SQLite (NON versionnée)
└── rapports/             # rapports générés (NON versionnés)
```

Dépendances principales : [feedparser](https://feedparser.readthedocs.io/) (flux RSS), [httpx](https://www.python-httpx.org/) (requêtes HTTP), [trafilatura](https://trafilatura.readthedocs.io/) (extraction de texte), [pydantic](https://docs.pydantic.dev/) et [PyYAML](https://pyyaml.org/) (config).

---

## Limites connues

- **Google News renvoie au maximum 100 résultats par recherche.** Pour une période longue ou un sujet très couvert, découpe-le en plusieurs recherches plus précises.
- **Les liens Google News passent par une redirection** (`news.google.com/rss/articles/...`) : avec `extraire_contenu: true`, seul le texte des articles venant des flux RSS des sites est récupéré.
- **Seuls les sites avec un flux RSS/Atom sont pris en charge.** Un site sans flux peut quand même être suivi avec une recherche `site:` dans Google News.
- Un article sans date de publication est toujours gardé, et daté du jour où il a été vu pour la première fois.
