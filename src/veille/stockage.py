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
    vu_le     TEXT NOT NULL
)
"""


def ouvrir(chemin: Path) -> sqlite3.Connection:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(chemin)
    db.row_factory = sqlite3.Row
    db.execute(SCHEMA)
    return db


def enregistrer(db: sqlite3.Connection, articles: list[Article]) -> int:
    """Insère les articles inconnus, retourne le nombre de nouveaux."""
    maintenant = datetime.now(timezone.utc).isoformat()
    avant = db.total_changes
    db.executemany(
        "INSERT OR IGNORE INTO articles (url, theme, source, titre, date, resume, vu_le) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (a.url, a.theme, a.source, a.titre, a.date.isoformat() if a.date else None, a.resume, maintenant)
            for a in articles
            if a.url
        ],
    )
    db.commit()
    return db.total_changes - avant


def articles_depuis(db: sqlite3.Connection, depuis: datetime) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT * FROM articles WHERE COALESCE(date, vu_le) >= ? ORDER BY theme, COALESCE(date, vu_le) DESC",
        (depuis.isoformat(),),
    ).fetchall()
