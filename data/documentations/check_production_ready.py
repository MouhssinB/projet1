#!/usr/bin/env python3
"""
Script de vérification pré-déploiement pour la production

Ce script vérifie que toutes les configurations de sécurité
sont correctes avant le déploiement en production.

Usage:
    python check_production_ready.py
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv


class Colors:
    """Codes couleur pour l'affichage"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(message):
    """Affiche un en-tête"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_check(message, status, details=None):
    """Affiche un résultat de vérification"""
    if status == "OK":
        symbol = "✅"
        color = Colors.GREEN
    elif status == "WARNING":
        symbol = "⚠️"
        color = Colors.YELLOW
    else:  # ERROR
        symbol = "❌"
        color = Colors.RED
    
    print(f"{color}{symbol} {message}{Colors.END}")
    if details:
        print(f"   {details}")


def check_secret_key(env_file):
    """Vérifie la SECRET_KEY"""
    print_header("Vérification SECRET_KEY")
    
    load_dotenv(env_file)
    secret_key = os.getenv('SECRET_KEY')
    
    if not secret_key:
        print_check("SECRET_KEY présente", "ERROR", "SECRET_KEY manquante !")
        return False
    
    if len(secret_key) < 32:
        print_check(
            "SECRET_KEY longueur",
            "ERROR",
            f"Longueur: {len(secret_key)} caractères (minimum 32 requis)"
        )
        return False
    
    if len(secret_key) < 64:
        print_check(
            "SECRET_KEY longueur",
            "WARNING",
            f"Longueur: {len(secret_key)} caractères (64+ recommandé)"
        )
    else:
        print_check(
            "SECRET_KEY longueur",
            "OK",
            f"Longueur: {len(secret_key)} caractères"
        )
    
    # Vérifier les valeurs par défaut
    forbidden_values = ['dev', 'development', 'test', 'changeme', 'your_secret_key_here']
    if secret_key.lower() in forbidden_values:
        print_check(
            "SECRET_KEY sécurité",
            "ERROR",
            "SECRET_KEY par défaut détectée ! Générez une nouvelle clé."
        )
        return False
    
    # Vérifier l'entropie
    if re.match(r'^[a-z]+$', secret_key.lower()):
        print_check(
            "SECRET_KEY entropie",
            "WARNING",
            "SECRET_KEY semble avoir une faible entropie"
        )
    else:
        print_check("SECRET_KEY entropie", "OK", "Entropie suffisante")
    
    return True


def check_oauth_config(env_file):
    """Vérifie la configuration OAuth"""
    print_header("Vérification Configuration OAuth")
    
    load_dotenv(env_file)
    
    required_vars = {
        'GAUTHIQ_CLIENT_ID': 'Client ID',
        'GAUTHIQ_CLIENT_SECRET': 'Client Secret',
        'GAUTHIQ_DISCOVERY_URL': 'Discovery URL',
        'GAUTHIQ_REDIRECT_URI': 'Redirect URI'
    }
    
    all_ok = True
    
    for var, name in required_vars.items():
        value = os.getenv(var)
        if not value:
            print_check(f"{name}", "ERROR", f"{var} manquante")
            all_ok = False
        else:
            print_check(f"{name}", "OK", f"{var} configurée")
    
    # Vérifier que REDIRECT_URI est en HTTPS
    redirect_uri = os.getenv('GAUTHIQ_REDIRECT_URI', '')
    if redirect_uri:
        if not redirect_uri.startswith('https://'):
            print_check(
                "REDIRECT_URI protocole",
                "ERROR",
                "REDIRECT_URI doit utiliser HTTPS en production"
            )
            all_ok = False
        else:
            print_check("REDIRECT_URI protocole", "OK", "HTTPS activé")
    
    return all_ok


def check_ssl_config(env_file):
    """Vérifie la configuration SSL"""
    print_header("Vérification Configuration SSL")
    
    load_dotenv(env_file)
    
    ssl_verify = os.getenv('GAUTHIQ_SSL_VERIFY', 'False').lower() in ('true', '1', 't')
    
    if not ssl_verify:
        print_check(
            "SSL Verify",
            "ERROR",
            "GAUTHIQ_SSL_VERIFY doit être True en production"
        )
        return False
    else:
        print_check("SSL Verify", "OK", "SSL activé")
        return True


def check_cookie_config(env_file):
    """Vérifie la configuration des cookies"""
    print_header("Vérification Configuration Cookies")
    
    load_dotenv(env_file)
    
    all_ok = True
    
    # SameSite
    samesite = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    if samesite != 'None':
        print_check(
            "SESSION_COOKIE_SAMESITE",
            "WARNING",
            f"Valeur: {samesite}. 'None' recommandé pour OAuth cross-domain"
        )
    else:
        print_check("SESSION_COOKIE_SAMESITE", "OK", f"Valeur: {samesite}")
    
    # Secure
    secure = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    if not secure:
        print_check(
            "SESSION_COOKIE_SECURE",
            "ERROR",
            "SESSION_COOKIE_SECURE doit être True en production"
        )
        all_ok = False
    else:
        print_check("SESSION_COOKIE_SECURE", "OK", "Cookies sécurisés")
    
    # HttpOnly
    httponly = os.getenv('SESSION_COOKIE_HTTPONLY', 'False').lower() in ('true', '1', 't')
    if not httponly:
        print_check(
            "SESSION_COOKIE_HTTPONLY",
            "WARNING",
            "SESSION_COOKIE_HTTPONLY recommandé"
        )
    else:
        print_check("SESSION_COOKIE_HTTPONLY", "OK", "Protection XSS activée")
    
    return all_ok


def check_habilitations_config(env_file):
    """Vérifie la configuration des habilitations"""
    print_header("Vérification Configuration Habilitations")
    
    load_dotenv(env_file)
    
    all_ok = True
    
    habilitation_url = os.getenv('GAUTHIQ_HABILITATION')
    if not habilitation_url:
        print_check(
            "GAUTHIQ_HABILITATION",
            "WARNING",
            "URL habilitations non configurée"
        )
        all_ok = False
    else:
        print_check("GAUTHIQ_HABILITATION", "OK", "URL configurée")
    
    filtre = os.getenv('GAUTHIQ_HABILITATION_FILTRE')
    if not filtre:
        print_check(
            "GAUTHIQ_HABILITATION_FILTRE",
            "WARNING",
            "Filtres non configurés"
        )
        all_ok = False
    else:
        print_check(
            "GAUTHIQ_HABILITATION_FILTRE",
            "OK",
            f"Filtres: {filtre}"
        )
    
    return all_ok


def check_admin_config(env_file):
    """Vérifie la liste des administrateurs"""
    print_header("Vérification Liste Administrateurs")
    
    load_dotenv(env_file)
    
    admins = os.getenv('LISTE_ADMINS', '').split(',')
    admins = [a.strip() for a in admins if a.strip()]
    
    if not admins:
        print_check(
            "LISTE_ADMINS",
            "WARNING",
            "Aucun administrateur configuré"
        )
        return False
    else:
        print_check(
            "LISTE_ADMINS",
            "OK",
            f"{len(admins)} administrateur(s) configuré(s)"
        )
        for admin in admins:
            print(f"   • {admin}")
        return True


def check_files_exist():
    """Vérifie que les fichiers nécessaires existent"""
    print_header("Vérification Fichiers")
    
    required_files = [
        'auth/gauthiq_p.py',
        'app.py',
        'requirements.txt'
    ]
    
    all_ok = True
    
    for file in required_files:
        if os.path.exists(file):
            print_check(file, "OK", "Fichier présent")
        else:
            print_check(file, "ERROR", "Fichier manquant")
            all_ok = False
    
    return all_ok


def check_python_version():
    """Vérifie la version Python"""
    print_header("Vérification Version Python")
    
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_check(
            "Version Python",
            "ERROR",
            f"Python {version.major}.{version.minor} (minimum 3.8 requis)"
        )
        return False
    else:
        print_check(
            "Version Python",
            "OK",
            f"Python {version.major}.{version.minor}.{version.micro}"
        )
        return True


def check_dependencies():
    """Vérifie les dépendances"""
    print_header("Vérification Dépendances")
    
    required_packages = [
        'flask',
        'authlib',
        'requests',
        'python-dotenv',
        'flask-session'
    ]
    
    all_ok = True
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_check(package, "OK", "Package installé")
        except ImportError:
            print_check(package, "ERROR", "Package manquant")
            all_ok = False
    
    return all_ok


def generate_report(results):
    """Génère un rapport final"""
    print_header("RAPPORT FINAL")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"Total de vérifications : {total}")
    print(f"{Colors.GREEN}✅ Réussies : {passed}{Colors.END}")
    
    if failed > 0:
        print(f"{Colors.RED}❌ Échouées : {failed}{Colors.END}")
        print(f"\n{Colors.RED}{Colors.BOLD}🛑 L'application N'EST PAS prête pour la production{Colors.END}")
        print(f"\n{Colors.YELLOW}Actions requises :{Colors.END}")
        
        for check, status in results.items():
            if not status:
                print(f"  • Corriger : {check}")
        
        return False
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ L'application EST prête pour la production{Colors.END}")
        return True


def main():
    """Fonction principale"""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}VÉRIFICATION PRÉ-DÉPLOIEMENT PRODUCTION{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
    
    # Détecter le fichier .env
    env_file = '.env.production'
    if not os.path.exists(env_file):
        env_file = '.env'
        print(f"\n{Colors.YELLOW}⚠️ Fichier .env.production non trouvé, utilisation de .env{Colors.END}")
    
    if not os.path.exists(env_file):
        print(f"\n{Colors.RED}❌ Aucun fichier .env trouvé !{Colors.END}")
        return False
    
    print(f"\n{Colors.BLUE}Fichier de configuration : {env_file}{Colors.END}")
    
    # Exécuter les vérifications
    results = {
        'Python Version': check_python_version(),
        'Dépendances': check_dependencies(),
        'Fichiers': check_files_exist(),
        'SECRET_KEY': check_secret_key(env_file),
        'Configuration OAuth': check_oauth_config(env_file),
        'Configuration SSL': check_ssl_config(env_file),
        'Configuration Cookies': check_cookie_config(env_file),
        'Configuration Habilitations': check_habilitations_config(env_file),
        'Liste Admins': check_admin_config(env_file)
    }
    
    # Générer le rapport
    return generate_report(results)


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Vérification interrompue{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Erreur : {str(e)}{Colors.END}")
        sys.exit(1)
