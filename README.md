# Veille news

Récupère les news des X derniers jours depuis une liste de flux RSS et des recherches Google News, les dédoublonne dans une base SQLite locale et génère un rapport Markdown par thème.

## Installation (sur n'importe quel PC)

Prérequis : [git](https://git-scm.com/) et [uv](https://docs.astral.sh/uv/getting-started/installation/) (uv installe Python tout seul si besoin).

```bash
git clone <url-du-repo>
cd projet_news
uv sync
cp config.example.yaml config.yaml   # puis édite config.yaml
```

## Utilisation

```bash
uv run veille              # utilise config.yaml
uv run veille -j 3         # seulement les 3 derniers jours
uv run veille -c autre.yaml
```

Le rapport est écrit dans `rapports/veille_AAAA-MM-JJ.md`.

## Config

Voir `config.example.yaml`. Chaque thème contient :

- `sites` : URLs de flux RSS/Atom (cherche « RSS » en bas de page du site, ou essaie `/feed`, `/rss`)
- `recherches` : requêtes envoyées à Google News (la syntaxe Google marche : `"phrase exacte"`, `-exclure`, `site:lemonde.fr`)

`config.yaml`, la base `data/` et les `rapports/` ne sont pas versionnés.
