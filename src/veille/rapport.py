import sqlite3
from datetime import datetime
from itertools import groupby
from pathlib import Path

LONGUEUR_RESUME = 300


def generer(articles: list[sqlite3.Row], dossier: Path, periode_jours: int) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    aujourdhui = datetime.now().strftime("%Y-%m-%d")
    chemin = dossier / f"veille_{aujourdhui}.md"

    lignes = [f"# Veille du {aujourdhui}", "", f"{len(articles)} article(s) sur les {periode_jours} derniers jours.", ""]
    for theme, groupe in groupby(articles, key=lambda a: a["theme"]):
        groupe = list(groupe)
        lignes += [f"## {theme} ({len(groupe)})", ""]
        for a in groupe:
            date = (a["date"] or a["vu_le"])[:10]
            lignes.append(f"### [{a['titre']}]({a['url']})")
            lignes.append(f"*{a['source']} — {date}*")
            if a["resume"]:
                resume = a["resume"].replace("\n", " ")
                if len(resume) > LONGUEUR_RESUME:
                    resume = resume[:LONGUEUR_RESUME].rsplit(" ", 1)[0] + "…"
                lignes += ["", resume]
            lignes.append("")

    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin
