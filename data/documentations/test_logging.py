#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour vérifier le système de logging centralisé
"""

import logging
import time
from pathlib import Path

def test_logging_system():
    """Test du système de logging"""
    
    # Créer le dossier de logs s'il n'existe pas
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    
    # Configuration similaire à celle de l'application
    log_file = log_dir / "application.log"
    
    # Handler principal
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Formateur détaillé
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Configurer le logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Test des différents niveaux
    logging.debug("Message de débogage")
    logging.info("Message d'information")
    logging.warning("Message d'avertissement")
    logging.error("Message d'erreur")
    logging.critical("Message critique")
    
    # Test avec des loggers spécifiques
    app_logger = logging.getLogger("app")
    app_logger.info("Log depuis le module app")
    
    synthetiser_logger = logging.getLogger("synthetiser")
    synthetiser_logger.info("Log depuis le module synthetiser")
    
    azure_logger = logging.getLogger("azure")
    azure_logger.debug("Log depuis le SDK Azure")
    
    print(f"Logs écrits dans: {log_file}")
    print("Vérifiez le contenu du fichier de log pour confirmer que tous les messages sont présents.")

if __name__ == "__main__":
    test_logging_system()
