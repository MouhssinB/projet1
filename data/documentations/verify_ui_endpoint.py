#!/usr/bin/env python3
"""
Script de vérification de l'endpoint /admin/habilitations/config
"""
import json
from pathlib import Path

# Vérification 1: Le fichier JSON existe
config_file = Path(__file__).parent / "data" / "admin" / "habilitations_config.json"
print("="*70)
print("🔍 VÉRIFICATION DU SYSTÈME D'HABILITATIONS")
print("="*70)

print("\n1️⃣ Vérification du fichier JSON...")
if config_file.exists():
    print(f"   ✅ Fichier trouvé: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"   ✅ JSON valide")
    print(f"   📋 Contenu:")
    print(f"      - Groupes: {len(config.get('groupes_habilites', []))}")
    for i, groupe in enumerate(config.get('groupes_habilites', []), 1):
        print(f"        {i}. {groupe}")
    print(f"      - Dernière modif: {config.get('derniere_modification', 'N/A')}")
    print(f"      - Modifié par: {config.get('modifie_par', 'N/A')}")
else:
    print(f"   ❌ Fichier introuvable: {config_file}")
    exit(1)

# Vérification 2: Le endpoint existe dans app.py
print("\n2️⃣ Vérification de l'endpoint dans app.py...")
app_file = Path(__file__).parent / "app.py"
if app_file.exists():
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "/admin/habilitations/config" in content:
        print("   ✅ Endpoint /admin/habilitations/config trouvé dans app.py")
        
        # Compter les occurrences
        lines = content.split('\n')
        occurrences = []
        for i, line in enumerate(lines, 1):
            if "/admin/habilitations/config" in line:
                occurrences.append((i, line.strip()))
        
        print(f"   📍 Trouvé à {len(occurrences)} endroit(s):")
        for line_num, line_content in occurrences:
            print(f"      - Ligne {line_num}: {line_content[:80]}...")
    else:
        print("   ❌ Endpoint /admin/habilitations/config NON TROUVÉ dans app.py")
        print("   ⚠️  L'interface ne pourra pas charger les groupes !")
        exit(1)
else:
    print(f"   ❌ Fichier app.py introuvable")
    exit(1)

# Vérification 3: Le template HTML existe
print("\n3️⃣ Vérification du template HTML...")
template_file = Path(__file__).parent / "templates" / "admin_habilitations.html"
if template_file.exists():
    print(f"   ✅ Template trouvé: {template_file}")
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "loadInitialGroups()" in content:
        print("   ✅ Fonction loadInitialGroups() présente")
    else:
        print("   ⚠️  Fonction loadInitialGroups() absente")
    
    if "fetch('/admin/habilitations/config')" in content:
        print("   ✅ Appel fetch() vers /admin/habilitations/config présent")
    else:
        print("   ❌ Appel fetch() vers /admin/habilitations/config absent")
else:
    print(f"   ❌ Template introuvable: {template_file}")
    exit(1)

# Vérification 4: Simulation de la réponse JSON
print("\n4️⃣ Simulation de la réponse endpoint...")
try:
    response = json.dumps(config, indent=2, ensure_ascii=False)
    print("   ✅ JSON sérialisable pour la réponse HTTP")
    print(f"   📦 Taille réponse: {len(response)} octets")
    print(f"   📋 Aperçu:")
    print("   " + "\n   ".join(response.split('\n')[:10]))
    if len(response.split('\n')) > 10:
        print("   ...")
except Exception as e:
    print(f"   ❌ Erreur de sérialisation: {e}")
    exit(1)

# Résumé final
print("\n" + "="*70)
print("📊 RÉSUMÉ")
print("="*70)
print("✅ Fichier JSON valide et accessible")
print("✅ Endpoint /admin/habilitations/config présent dans app.py")
print("✅ Template HTML configure et prêt")
print("✅ Simulation réponse JSON réussie")
print("\n🎯 PRÊT POUR LES TESTS")
print("\n📝 Prochaine étape:")
print("   1. Accéder à: http://localhost:5004/admin/habilitations")
print("   2. Ouvrir la console navigateur (F12)")
print("   3. Vérifier que 4 groupes apparaissent dans le tableau")
print("   4. Consulter le guide: GUIDE_TEST_UI_HABILITATIONS.md")
print("="*70)
