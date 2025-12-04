#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration centralisée pour le système de logging
"""

import logging
import logging.config
import os
from pathlib import Path

def get_logging_config():
    """
    Retourne la configuration complète du système de logging
    """
    
    # Créer le dossier de logs
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "application.log"
    
    # Configuration dictionnaire pour le logging
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(funcName)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'access': {
                'format': '%(asctime)s - ACCESS - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_file),
                'maxBytes': 50 * 1024 * 1024,  # 50MB
                'backupCount': 10,
                'encoding': 'utf-8',
                'formatter': 'detailed',
                'level': 'DEBUG'
            },
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            # Logger principal de l'application
            '': {  # Root logger
                'handlers': ['file', 'console'],
                'level': 'DEBUG',
                'propagate': False
            },
            # Loggers spécifiques
            'app': {
                'handlers': ['file', 'console'],
                'level': 'DEBUG',
                'propagate': False
            },
            'synthetiser': {
                'handlers': ['file', 'console'],
                'level': 'DEBUG',
                'propagate': False
            },
            'http_access': {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False
            },
            # Loggers pour les bibliothèques externes
            'werkzeug': {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False
            },
            'urllib3': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False
            },
            'azure': {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False
            },
            'openai': {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False
            },
            'requests': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False
            }
        }
    }
    
    return config

def setup_logging_from_config():
    """
    Configure le système de logging à partir de la configuration
    """
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Log de confirmation
    logger = logging.getLogger('app')
    logger.info("=" * 80)
    logger.info("SYSTÈME DE LOGGING CONFIGURÉ VIA DICTCONFIG")
    logger.info(f"Fichier de logs: {Path('log') / 'application.log'}")
    logger.info("=" * 80)
    
    return logger
