import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from veille.collecte import Article

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url       TEXT PRIMARY KEY,
    theme     TEXT NOT NULL,
    source    TEXT,
    titre     TEXT,
    date      TEXT,
    resume    TEXT,
    vu_le     TEXT NOT NULL,
    image     TEXT,
    site      TEXT
)
"""

# Colonnes ajoutées après la première version : migrées sur les bases existantes
COLONNES_AJOUTEES = {"image": "TEXT", "site": "TEXT"}


def ouvrir(chemin: Path) -> sqlite3.Connection:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(chemin)
    db.row_factory = sqlite3.Row
    db.execute(SCHEMA)
    existantes = {ligne["name"] for ligne in db.execute("PRAGMA table_info(articles)")}
    for nom, type_ in COLONNES_AJOUTEES.items():
        if nom not in existantes:
            db.execute(f"ALTER TABLE articles ADD COLUMN {nom} {type_}")
    return db


def _compter(db: sqlite3.Connection) -> int:
    return db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]


def enregistrer(db: sqlite3.Connection, articles: list[Article]) -> int:
    """Insère les articles inconnus (et complète l'image des déjà connus), retourne le nombre de nouveaux."""
    maintenant = datetime.now(timezone.utc).isoformat()
    avant = _compter(db)
    db.executemany(
        "INSERT INTO articles (url, theme, source, titre, date, resume, vu_le, image, site) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(url) DO UPDATE SET "
        "image = COALESCE(articles.image, excluded.image), site = COALESCE(articles.site, excluded.site)",
        [
            (
                a.url, a.theme, a.source, a.titre, a.date.isoformat() if a.date else None,
                a.resume, maintenant, a.image, a.site,
            )
            for a in articles
            if a.url
        ],
    )
    db.commit()
    return _compter(db) - avant


def _cle_titre(titre: str | None) -> str:
    return re.sub(r"\W+", "", (titre or "").lower())


def articles_depuis(db: sqlite3.Connection, depuis: datetime) -> list[sqlite3.Row]:
    """Articles de la période. Un même titre vu via plusieurs sources (Google + Bing...) n'est gardé
    qu'une fois par thème, en préférant la version avec image."""
    lignes = db.execute(
        "SELECT * FROM articles WHERE COALESCE(date, vu_le) >= ? "
        "ORDER BY theme, (image IS NULL), COALESCE(date, vu_le) DESC",
        (depuis.isoformat(),),
    ).fetchall()
    vus = set()
    resultat = []
    for ligne in lignes:
        cle = (ligne["theme"], _cle_titre(ligne["titre"]))
        if cle not in vus:
            vus.add(cle)
            resultat.append(ligne)
    resultat.sort(key=lambda a: (a["theme"], a["date"] or a["vu_le"]), reverse=True)
    resultat.sort(key=lambda a: a["theme"])
    return resultat
