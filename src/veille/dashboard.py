import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

TEMPLATE = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")


def generer(
    articles: list[sqlite3.Row], dossier: Path, periode_jours: int, themes: list[str], tendances_x: list[dict]
) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    aujourdhui = datetime.now().strftime("%Y-%m-%d")
    chemin = dossier / f"veille_{aujourdhui}.html"

    # "Nouveau" = vu pour la première fois dans les dernières 24 h
    seuil_nouveau = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    donnees = {
        "genere_le": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "periode_jours": periode_jours,
        "themes": themes,
        "tendances_x": tendances_x,
        "articles": [
            {
                "theme": a["theme"],
                "titre": a["titre"],
                "url": a["url"],
                "source": a["source"],
                "site": a["site"],
                "date": a["date"] or a["vu_le"],
                "resume": a["resume"],
                "image": a["image"],
                "nouveau": a["vu_le"] >= seuil_nouveau,
            }
            for a in articles
        ],
    }
    # "</" échappé pour qu'un titre ne puisse pas fermer la balise <script>
    json_donnees = json.dumps(donnees, ensure_ascii=False).replace("</", "<\\/")
    chemin.write_text(TEMPLATE.replace("__DONNEES__", json_donnees), encoding="utf-8")
    return chemin
