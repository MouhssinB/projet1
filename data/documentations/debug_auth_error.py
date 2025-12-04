#!/usr/bin/env python3
"""
Script de diagnostic pour l'erreur d'authentification
"""

import sys
import json

def analyze_error():
    """Analyse l'erreur 'str' object has no attribute 'get'"""
    
    print("=" * 70)
    print("🔍 ANALYSE DE L'ERREUR D'AUTHENTIFICATION")
    print("=" * 70)
    print()
    
    print("📋 ERREUR RENCONTRÉE:")
    print("   ❌ 'str' object has no attribute 'get'")
    print()
    
    print("🔍 CAUSES POSSIBLES:")
    print()
    
    print("1️⃣  parse_id_token() retourne une chaîne au lieu d'un dict")
    print("   Cause: Le token ID peut être corrompu ou mal formé")
    print("   Solution: ✅ Ajout de validation isinstance(userinfo, dict)")
    print()
    
    print("2️⃣  userinfo est un JWT non décodé")
    print("   Cause: parse_id_token() n'a pas décodé le JWT")
    print("   Solution: ✅ Vérification du type et log du contenu")
    print()
    
    print("3️⃣  Token d'accès invalide ou expiré")
    print("   Cause: Le token OAuth a expiré ou est mal formé")
    print("   Solution: ✅ Validation de access_token avant utilisation")
    print()
    
    print("=" * 70)
    print("🔧 CORRECTIONS APPLIQUÉES:")
    print("=" * 70)
    print()
    
    corrections = [
        {
            "fichier": "auth/gauthiq_d.py",
            "ligne": "~268",
            "modification": "Ajout de validation isinstance(userinfo, dict)",
            "code": """
# Vérification que userinfo est bien un dictionnaire
if not isinstance(userinfo, dict):
    self.app.logger.error(f"❌ userinfo n'est pas un dictionnaire: type={type(userinfo)}")
    raise ValueError(f"userinfo doit être un dictionnaire, reçu: {type(userinfo)}")
            """
        },
        {
            "fichier": "auth/gauthiq_d.py",
            "ligne": "~108",
            "modification": "Validation des paramètres dans get_user_habilitations",
            "code": """
# Validation des paramètres
if not isinstance(userinfo, dict):
    self.app.logger.error(f"❌ userinfo doit être un dictionnaire, reçu {type(userinfo).__name__}")
    return {}

if not access_token:
    self.app.logger.error("❌ access_token manquant")
    return {}
            """
        },
        {
            "fichier": "auth/gauthiq_d.py",
            "ligne": "~332",
            "modification": "Amélioration du logging d'erreur",
            "code": """
except Exception as e:
    self.app.logger.error(f"❌ ERREUR D'AUTHENTIFICATION: {e}")
    self.app.logger.error(f"   Type d'erreur: {type(e).__name__}")
    
    # Afficher les variables locales pour le debug
    if 'userinfo' in locals():
        self.app.logger.error(f"   Userinfo type: {type(userinfo).__name__}")
        if isinstance(userinfo, str):
            self.app.logger.error(f"   Userinfo (JWT): {userinfo[:50]}")
    ...
            """
        }
    ]
    
    for idx, correction in enumerate(corrections, 1):
        print(f"{idx}. {correction['fichier']} (ligne {correction['ligne']})")
        print(f"   📝 {correction['modification']}")
        print(f"   Code:")
        for line in correction['code'].strip().split('\n'):
            print(f"      {line}")
        print()
    
    print("=" * 70)
    print("🧪 PROCHAINES ÉTAPES DE DIAGNOSTIC:")
    print("=" * 70)
    print()
    
    steps = [
        "1. Redémarrer l'application Flask",
        "2. Se connecter via /login",
        "3. Observer les logs détaillés dans le terminal",
        "4. Si l'erreur persiste, vérifier les logs pour:",
        "   • Le type exact de userinfo (str ou autre)",
        "   • Le contenu des 50 premiers caractères si c'est une chaîne",
        "   • Les clés présentes dans token",
        "5. Vérifier la configuration Gauthiq:",
        "   • GAUTHIQ_CLIENT_ID correct",
        "   • GAUTHIQ_CLIENT_SECRET correct",
        "   • GAUTHIQ_DISCOVERY_URL accessible",
        "6. Tester avec curl le endpoint de découverte:",
        "   curl https://authentification-interne-dev.../.well-known/openid-configuration"
    ]
    
    for step in steps:
        print(f"   {step}")
    print()
    
    print("=" * 70)
    print("📖 LOGS À SURVEILLER:")
    print("=" * 70)
    print()
    
    logs_to_watch = [
        ("✅ Normal", "userinfo type: dict", "L'authentification devrait réussir"),
        ("❌ Erreur", "userinfo type: str", "Le JWT n'a pas été décodé correctement"),
        ("❌ Erreur", "Token présent: Non", "Le token OAuth n'a pas été récupéré"),
        ("⚠️ Warning", "Userinfo (JWT): eyJ...", "Le token ID est retourné brut (non décodé)"),
    ]
    
    for status, log, description in logs_to_watch:
        print(f"   {status}")
        print(f"      Log attendu: {log}")
        print(f"      Signification: {description}")
        print()
    
    print("=" * 70)
    print("💡 RECOMMANDATIONS:")
    print("=" * 70)
    print()
    
    recommendations = [
        "✅ Les validations ont été ajoutées pour capturer l'erreur plus tôt",
        "✅ Les logs ont été améliorés pour diagnostiquer le problème",
        "⚠️  Si userinfo est une chaîne, c'est un JWT non décodé",
        "⚠️  Vérifier que authlib est installé et à jour (pip list | grep authlib)",
        "⚠️  Vérifier que les secrets OAuth sont corrects dans .env",
        "💡 En développement HTTP, désactiver SSL: GAUTHIQ_SSL_VERIFY=False",
        "💡 Vérifier que le redirect_uri correspond exactement (http://localhost:5003/oauth2callback)",
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    print()
    
    print("=" * 70)
    print("🔧 COMMANDES UTILES:")
    print("=" * 70)
    print()
    
    commands = [
        ("Vérifier authlib", "pip list | grep authlib"),
        ("Voir les logs en temps réel", "tail -f log/application.log"),
        ("Filtrer les erreurs", "grep 'ERREUR D.AUTHENTIFICATION' log/application.log"),
        ("Tester la config OAuth", "curl https://authentification-interne-dev.caas-nonprod.intra.groupama.fr/auth/realms/interne/.well-known/openid-configuration"),
    ]
    
    for desc, cmd in commands:
        print(f"   📝 {desc}:")
        print(f"      $ {cmd}")
        print()
    
    print("=" * 70)
    print("✅ Diagnostic terminé")
    print("=" * 70)
    print()

if __name__ == "__main__":
    analyze_error()
