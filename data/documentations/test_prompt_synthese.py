#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour vérifier la refactorisation du module prompt_synthese
"""

import sys
import os

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.prompt_synthese import (
        get_format_json,
        get_mission_template,
        get_instructions_template,
        get_documents_reference_template,
        construire_prompt_synthese
    )
    
    print("✅ Import du module prompt_synthese réussi")
    
    # Test des templates de base
    format_json = get_format_json()
    print(f"✅ Template JSON - longueur: {len(format_json)} caractères")
    
    mission = get_mission_template()
    print(f"✅ Template mission - longueur: {len(mission)} caractères")
    
    instructions = get_instructions_template()
    print(f"✅ Template instructions - longueur: {len(instructions)} caractères")
    
    docs_ref = get_documents_reference_template()
    print(f"✅ Template documents - longueur: {len(docs_ref)} caractères")
    
    print("\n🎉 Tous les tests de base sont passés avec succès!")
    print("\nLa refactorisation du prompt de synthèse est opérationnelle.")
    
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur inattendue: {e}")
    sys.exit(1)
