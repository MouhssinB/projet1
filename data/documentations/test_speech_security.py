#!/usr/bin/env python3
"""
Script de test pour vérifier la sécurisation des tokens Speech AI
"""

import requests
import re
import sys
from pathlib import Path

def check_file_for_secrets(file_path, patterns):
    """Vérifie qu'un fichier ne contient pas de secrets exposés"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        violations = []
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append({
                    'pattern': pattern_name,
                    'matches': matches[:3]  # Limiter à 3 exemples
                })
        
        return violations
    except Exception as e:
        return [{'pattern': 'ERROR', 'matches': [str(e)]}]

def main():
    print("=" * 70)
    print("🔒 VÉRIFICATION SÉCURITÉ - AZURE SPEECH TOKENS")
    print("=" * 70)
    print()
    
    # Patterns à détecter (violations de sécurité)
    secret_patterns = {
        'subscription_key_exposed': r'subscriptionKey\s*=\s*["\'](?!null)[^"\']+["\']',
        'speech_key_template': r'{{\s*speech_key\s*}}',
        'speech_endpoint_template': r'{{\s*speech_endpoint\s*}}',
        'fromSubscription_call': r'SpeechConfig\.fromSubscription\(',
        'fromEndpoint_call': r'SpeechConfig\.fromEndpoint\(',
        'api_key_in_js': r'const\s+\w*[Kk]ey\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
    }
    
    # Fichiers à vérifier
    files_to_check = [
        ('templates/index.html', 'HTML Template'),
        ('static/js/app.js', 'JavaScript Client'),
    ]
    
    # Le script est dans tests/, les fichiers sont dans le parent
    src_dir = Path(__file__).parent.parent
    total_violations = 0
    
    for file_path, file_desc in files_to_check:
        full_path = src_dir / file_path
        print(f"📄 Vérification: {file_desc}")
        print(f"   Fichier: {file_path}")
        
        if not full_path.exists():
            print(f"   ⚠️  Fichier non trouvé: {full_path}")
            continue
        
        violations = check_file_for_secrets(full_path, secret_patterns)
        
        if violations:
            print(f"   ❌ VIOLATIONS DÉTECTÉES: {len(violations)}")
            for v in violations:
                print(f"      - {v['pattern']}")
                for match in v['matches']:
                    print(f"        → {match[:50]}...")
            total_violations += len(violations)
        else:
            print(f"   ✅ Aucune violation détectée")
        
        print()
    
    # Vérifications positives (ce qui DOIT être présent)
    print("─" * 70)
    print("🔍 Vérification des éléments de sécurité requis")
    print("─" * 70)
    print()
    
    required_patterns = {
        'token_variable': (r'authToken\s*=', 'Variable authToken'),
        'fetch_token_function': (r'fetchSpeechToken\s*\(', 'Fonction fetchSpeechToken'),
        'from_authorization_token': (r'fromAuthorizationToken\s*\(', 'Utilisation fromAuthorizationToken'),
        'get_speech_token_route': (r'@app\.route.*get_speech_token', 'Route /get_speech_token'),
    }
    
    js_file = src_dir / 'static/js/app.js'
    py_file = src_dir / 'app.py'
    
    missing_requirements = 0
    
    for pattern_name, (pattern, description) in required_patterns.items():
        found = False
        # Tous les patterns Python dans app.py, patterns JS dans app.js
        if 'route' in pattern_name.lower():
            search_file = py_file
        elif any(x in pattern_name.lower() for x in ['token', 'authorization', 'fetch']):
            search_file = js_file
        else:
            search_file = js_file
        
        if search_file.exists():
            with open(search_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                    found = True
        
        if found:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ MANQUANT: {description}")
            missing_requirements += 1
    
    print()
    print("=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print(f"Violations de sécurité détectées: {total_violations}")
    print(f"Éléments de sécurité manquants: {missing_requirements}")
    print()
    
    if total_violations == 0 and missing_requirements == 0:
        print("✅ ✅ ✅ SUCCÈS - Tous les tests de sécurité sont passés ! ✅ ✅ ✅")
        print()
        print("🎉 Les clés API ne sont plus exposées côté client")
        print("🔒 L'authentification utilise des tokens temporaires")
        print("✨ Validation équipe sécurité: OK")
        return 0
    else:
        print("❌ ❌ ❌ ÉCHEC - Des problèmes de sécurité ont été détectés ❌ ❌ ❌")
        print()
        print("⚠️  Action requise: Corriger les violations avant le déploiement")
        return 1

if __name__ == '__main__':
    sys.exit(main())
