#!/usr/bin/env python3
"""
Test du groupe spécial GR_SIMSAN_ALL
Ce groupe permet l'accès à TOUS les utilisateurs, même sans groupes d'habilitation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.habilitations_manager import get_habilitations_manager

def test_groupe_special_all():
    """Test que GR_SIMSAN_ALL autorise tous les utilisateurs"""
    
    print("=" * 80)
    print("TEST DU GROUPE SPÉCIAL GR_SIMSAN_ALL")
    print("=" * 80)
    
    hab = get_habilitations_manager()
    
    # Test 1: Utilisateur AVEC des groupes d'habilitation
    print("\n" + "=" * 80)
    print("TEST 1: Utilisateur avec groupes d'habilitation + GR_SIMSAN_ALL configuré")
    print("=" * 80)
    
    success, msg = hab.update_habilitations(['GR_SIMSAN_ALL'], 'test_auto')
    if not success:
        print(f"❌ ERREUR lors de la configuration: {msg}")
        return False
    
    user_hab_avec_groupes = {
        'roles': {
            'GR_QUELCONQUE_GROUPE': ['role1', 'role2'],
            'GF_AUTRE_GROUPE': ['role3']
        }
    }
    
    has_access, message = hab.user_has_access(user_hab_avec_groupes)
    print(f"\nRésultat: {message}")
    
    if has_access:
        print("✅ TEST 1 RÉUSSI: Utilisateur avec groupes autorisé via GR_SIMSAN_ALL")
    else:
        print("❌ TEST 1 ÉCHOUÉ: Devrait être autorisé avec GR_SIMSAN_ALL")
        return False
    
    # Test 2: Utilisateur SANS groupes d'habilitation
    print("\n" + "=" * 80)
    print("TEST 2: Utilisateur SANS groupes d'habilitation + GR_SIMSAN_ALL configuré")
    print("=" * 80)
    
    user_hab_sans_groupes = {
        'roles': {}
    }
    
    has_access, message = hab.user_has_access(user_hab_sans_groupes)
    print(f"\nRésultat: {message}")
    
    if has_access:
        print("✅ TEST 2 RÉUSSI: Utilisateur SANS groupes autorisé via GR_SIMSAN_ALL")
    else:
        print("❌ TEST 2 ÉCHOUÉ: Devrait être autorisé avec GR_SIMSAN_ALL")
        return False
    
    # Test 3: Utilisateur avec groupes invalides (ne commencent pas par GR/GF)
    print("\n" + "=" * 80)
    print("TEST 3: Utilisateur avec groupes invalides + GR_SIMSAN_ALL configuré")
    print("=" * 80)
    
    user_hab_groupes_invalides = {
        'roles': {
            'ADMIN': ['role1'],
            'TEST_GROUP': ['role2'],
            'GA_AUTRE': ['role3']
        }
    }
    
    has_access, message = hab.user_has_access(user_hab_groupes_invalides)
    print(f"\nRésultat: {message}")
    
    if has_access:
        print("✅ TEST 3 RÉUSSI: Utilisateur avec groupes invalides autorisé via GR_SIMSAN_ALL")
    else:
        print("❌ TEST 3 ÉCHOUÉ: Devrait être autorisé avec GR_SIMSAN_ALL")
        return False
    
    # Test 4: Sans GR_SIMSAN_ALL, utilisateur sans groupes valides refusé
    print("\n" + "=" * 80)
    print("TEST 4: Utilisateur SANS groupes valides + GR_SIMSAN_ALL NON configuré")
    print("=" * 80)
    
    success, msg = hab.update_habilitations(['GR_SMS', 'GF_ADMIN'], 'test_auto')
    if not success:
        print(f"❌ ERREUR lors de la configuration: {msg}")
        return False
    
    user_hab_sans_groupes_valides = {
        'roles': {
            'ADMIN': ['role1'],
            'TEST': ['role2']
        }
    }
    
    has_access, message = hab.user_has_access(user_hab_sans_groupes_valides)
    print(f"\nRésultat: {message}")
    
    if not has_access:
        print("✅ TEST 4 RÉUSSI: Utilisateur sans groupes valides correctement refusé")
    else:
        print("❌ TEST 4 ÉCHOUÉ: Devrait être refusé sans GR_SIMSAN_ALL")
        return False
    
    # Test 5: Avec GR_SIMSAN_ALL + autres groupes, tout le monde passe
    print("\n" + "=" * 80)
    print("TEST 5: Configuration mixte (GR_SIMSAN_ALL + autres groupes)")
    print("=" * 80)
    
    success, msg = hab.update_habilitations(['GR_SIMSAN_ALL', 'GR_SMS', 'GF_ADMIN'], 'test_auto')
    if not success:
        print(f"❌ ERREUR lors de la configuration: {msg}")
        return False
    
    has_access, message = hab.user_has_access(user_hab_sans_groupes_valides)
    print(f"\nRésultat: {message}")
    
    if has_access:
        print("✅ TEST 5 RÉUSSI: GR_SIMSAN_ALL prend la priorité sur les autres règles")
    else:
        print("❌ TEST 5 ÉCHOUÉ: GR_SIMSAN_ALL devrait autoriser même avec d'autres règles")
        return False
    
    print("\n" + "=" * 80)
    print("🎉 TOUS LES TESTS ONT RÉUSSI!")
    print("=" * 80)
    print("\nRésumé:")
    print("✅ GR_SIMSAN_ALL autorise les utilisateurs avec groupes")
    print("✅ GR_SIMSAN_ALL autorise les utilisateurs sans groupes")
    print("✅ GR_SIMSAN_ALL autorise les utilisateurs avec groupes invalides")
    print("✅ Sans GR_SIMSAN_ALL, la validation normale fonctionne")
    print("✅ GR_SIMSAN_ALL prioritaire en configuration mixte")
    print("\n💡 Pour activer l'accès universel, ajoutez 'GR_SIMSAN_ALL' dans les groupes autorisés")
    
    return True


if __name__ == '__main__':
    try:
        success = test_groupe_special_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
