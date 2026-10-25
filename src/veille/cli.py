import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from veille import collecte, rapport, stockage
from veille.config import charger_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille de news")
    parser.add_argument("-c", "--config", type=Path, default=Path("config.yaml"), help="fichier de config")
    parser.add_argument("-j", "--jours", type=int, help="remplace periode_jours de la config")
    args = parser.parse_args()

    config = charger_config(args.config)
    if args.jours:
        config.periode_jours = args.jours

    print(f"Collecte sur {config.periode_jours} jour(s)...")
    articles = collecte.collecter(config)

    db = stockage.ouvrir(config.base_de_donnees)
    nouveaux = stockage.enregistrer(db, articles)
    print(f"{len(articles)} article(s) trouvé(s), dont {nouveaux} nouveau(x).")

    depuis = datetime.now(timezone.utc) - timedelta(days=config.periode_jours)
    chemin = rapport.generer(stockage.articles_depuis(db, depuis), config.dossier_rapports, config.periode_jours)
    print(f"Rapport : {chemin}")
