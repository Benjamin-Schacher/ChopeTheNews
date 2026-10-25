from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class Theme(BaseModel):
    sites: list[str] = Field(default_factory=list)
    recherches: list[str] = Field(default_factory=list)


class GoogleNews(BaseModel):
    langue: str = "fr"
    pays: str = "FR"


class Config(BaseModel):
    periode_jours: int = 7
    google_news: GoogleNews = Field(default_factory=GoogleNews)
    moteurs: list[Literal["google_news", "bing_news"]] = ["google_news", "bing_news"]
    extraire_contenu: bool = False
    recuperer_images: bool = True
    ouvrir_navigateur: bool = True
    dossier_rapports: Path = Path("rapports")
    base_de_donnees: Path = Path("data/veille.db")
    themes: dict[str, Theme]


def charger_config(chemin: Path) -> Config:
    if not chemin.exists():
        raise SystemExit(
            f"Config introuvable : {chemin}\n"
            "Copie config.example.yaml en config.yaml puis adapte-le."
        )
    with chemin.open(encoding="utf-8") as f:
        return Config.model_validate(yaml.safe_load(f))
