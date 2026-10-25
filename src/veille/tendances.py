"""Tendances X (ex-Twitter) par pays, lues sur trends24.in (X n'a plus d'API gratuite pour ça)."""

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from veille.collecte import USER_AGENT

# Nom dans la config -> (libellé affiché, chemin sur trends24.in)
LIEUX_CONNUS = {"monde": ("Monde", ""), "france": ("France", "france/")}
NB_TENDANCES = 30

RE_LISTE = re.compile(r'<h3 class=title data-timestamp=([\d.]+)>.*?<ol class=trend-card__list>(.*?)</ol>', re.DOTALL)
RE_TENDANCE = re.compile(r'<a href="[^"]*" class=trend-link>(.*?)</a><span class=tweet-count data-count="(\d*)"', re.DOTALL)


def _lieu(nom: str) -> tuple[str, str]:
    # Les autres pays suivent le nom de l'URL trends24 : "belgium", "canada", "united-states"...
    return LIEUX_CONNUS.get(nom, (nom.replace("-", " ").title(), f"{nom}/"))


def lire(client: httpx.Client, nom: str) -> dict | None:
    libelle, chemin = _lieu(nom)
    page = f"https://trends24.in/{chemin}"
    try:
        reponse = client.get(page)
        reponse.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [erreur] tendances X {libelle} : {e}")
        return None

    # La page contient une liste par heure : la première est la plus récente
    m = RE_LISTE.search(reponse.text)
    if not m:
        print(f"  [erreur] tendances X {libelle} : format de page inattendu")
        return None
    tendances = []
    for nom_brut, compte in RE_TENDANCE.findall(m.group(2))[:NB_TENDANCES]:
        sujet = html.unescape(nom_brut).strip()
        tendances.append({
            "nom": sujet,
            "url": f"https://x.com/search?q={quote(sujet)}",
            "posts": int(compte) if compte else None,
        })
    print(f"  Tendances X {libelle} : {len(tendances)}")
    return {
        "lieu": libelle,
        "page": page,
        "maj": datetime.fromtimestamp(float(m.group(1)), tz=timezone.utc).isoformat(),
        "tendances": tendances,
    }


def collecter(lieux: list[str]) -> list[dict]:
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
        return [t for nom in lieux if (t := lire(client, nom))]


def sauver(tendances: list[dict], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(tendances, ensure_ascii=False, indent=1), encoding="utf-8")


def charger(chemin: Path) -> list[dict]:
    """Dernières tendances enregistrées (utilisé avec --sans-collecte)."""
    if not chemin.exists():
        return []
    return json.loads(chemin.read_text(encoding="utf-8"))
