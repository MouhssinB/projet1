#!/usr/bin/env python3
"""
Script rapide pour activer/désactiver l'accès universel via GR_SIMSAN_ALL

Usage:
    python3 toggle_acces_universel.py on   # Activer l'accès universel
    python3 toggle_acces_universel.py off  # Désactiver l'accès universel (sécurité normale)
    python3 toggle_acces_universel.py status  # Afficher le statut actuel
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.habilitations_manager import get_habilitations_manager


def afficher_status():
    """Affiche le statut actuel de la configuration"""
    hab = get_habilitations_manager()
    groupes = hab.get_groupes_habilites()
    
    print("\n" + "=" * 80)
    print("📋 STATUT ACTUEL DES HABILITATIONS")
    print("=" * 80)
    print(f"\nGroupes autorisés: {len(groupes)} groupe(s)")
    
    if 'GR_SIMSAN_ALL' in groupes:
        print("\n🌐 ACCÈS UNIVERSEL ACTIVÉ")
        print("   ✅ Tous les utilisateurs peuvent se connecter")
        print("   ⚠️  La sécurité basée sur les groupes est désactivée")
    else:
        print("\n🔒 SÉCURITÉ NORMALE ACTIVÉE")
        print("   ✅ Seuls les utilisateurs avec groupes valides peuvent se connecter")
        print("   ✅ Validation par préfixe GR/GF active")
    
    print(f"\nGroupes configurés:")
    for idx, groupe in enumerate(groupes, 1):
        emoji = "⭐" if groupe == "GR_SIMSAN_ALL" else "•"
        print(f"   {emoji} {groupe}")
    
    print("\n" + "=" * 80)


def activer_acces_universel():
    """Active l'accès universel en ajoutant GR_SIMSAN_ALL"""
    hab = get_habilitations_manager()
    groupes = hab.get_groupes_habilites()
    
    if 'GR_SIMSAN_ALL' in groupes:
        print("\n✅ L'accès universel est déjà activé!")
        afficher_status()
        return True
    
    print("\n" + "=" * 80)
    print("🔧 ACTIVATION DE L'ACCÈS UNIVERSEL")
    print("=" * 80)
    
    # Ajouter GR_SIMSAN_ALL aux groupes existants
    nouveaux_groupes = ['GR_SIMSAN_ALL'] + groupes
    
    success, message = hab.update_habilitations(nouveaux_groupes, 'script_toggle')
    
    if success:
        print("\n✅ ACCÈS UNIVERSEL ACTIVÉ AVEC SUCCÈS!")
        print("\n💡 Tous les utilisateurs peuvent maintenant se connecter")
        print("   → Même sans groupes d'habilitation")
        print("   → Même avec des groupes invalides")
        afficher_status()
        return True
    else:
        print(f"\n❌ ERREUR: {message}")
        return False


def desactiver_acces_universel():
    """Désactive l'accès universel en retirant GR_SIMSAN_ALL"""
    hab = get_habilitations_manager()
    groupes = hab.get_groupes_habilites()
    
    if 'GR_SIMSAN_ALL' not in groupes:
        print("\n✅ L'accès universel est déjà désactivé!")
        afficher_status()
        return True
    
    print("\n" + "=" * 80)
    print("🔒 DÉSACTIVATION DE L'ACCÈS UNIVERSEL")
    print("=" * 80)
    
    # Retirer GR_SIMSAN_ALL des groupes existants
    nouveaux_groupes = [g for g in groupes if g != 'GR_SIMSAN_ALL']
    
    if not nouveaux_groupes:
        print("\n⚠️  ATTENTION: Aucun autre groupe configuré!")
        print("   Si vous désactivez GR_SIMSAN_ALL, PERSONNE ne pourra se connecter.")
        print("\n💡 Options:")
        print("   1. Annuler (Ctrl+C)")
        print("   2. Continuer et configurer les groupes via l'interface admin")
        
        reponse = input("\nContinuer? (oui/non): ").strip().lower()
        if reponse not in ['oui', 'o', 'yes', 'y']:
            print("\n❌ Opération annulée")
            return False
    
    success, message = hab.update_habilitations(nouveaux_groupes, 'script_toggle')
    
    if success:
        print("\n✅ ACCÈS UNIVERSEL DÉSACTIVÉ AVEC SUCCÈS!")
        print("\n🔒 Sécurité normale rétablie")
        print("   → Validation par groupes GR/GF active")
        print("   → Seuls les utilisateurs avec groupes valides peuvent se connecter")
        
        if not nouveaux_groupes:
            print("\n⚠️  ATTENTION: Aucun groupe configuré!")
            print("   → Configurez les groupes via l'interface admin")
        
        afficher_status()
        return True
    else:
        print(f"\n❌ ERREUR: {message}")
        return False


def afficher_aide():
    """Affiche l'aide du script"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    GESTION DE L'ACCÈS UNIVERSEL                            ║
║                         GR_SIMSAN_ALL                                      ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage:
    python3 toggle_acces_universel.py [commande]

Commandes:
    on      Activer l'accès universel (tous les utilisateurs autorisés)
    off     Désactiver l'accès universel (sécurité normale)
    status  Afficher le statut actuel de la configuration

Exemples:
    # Activer l'accès pour une démo
    python3 toggle_acces_universel.py on
    
    # Vérifier le statut
    python3 toggle_acces_universel.py status
    
    # Rétablir la sécurité normale
    python3 toggle_acces_universel.py off

Documentation:
    Voir GROUPE_SPECIAL_ALL.md pour plus de détails

⚠️  ATTENTION:
    - L'accès universel désactive la sécurité basée sur les groupes
    - À utiliser avec précaution en environnement de production
    - Recommandé uniquement pour dev/test/démo
""")


def main():
    if len(sys.argv) < 2:
        afficher_aide()
        sys.exit(1)
    
    commande = sys.argv[1].lower()
    
    try:
        if commande in ['on', 'activer', 'enable']:
            success = activer_acces_universel()
        elif commande in ['off', 'desactiver', 'disable']:
            success = desactiver_acces_universel()
        elif commande in ['status', 'statut', 'info']:
            afficher_status()
            success = True
        elif commande in ['help', 'aide', '-h', '--help']:
            afficher_aide()
            success = True
        else:
            print(f"\n❌ Commande inconnue: {commande}")
            afficher_aide()
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n❌ Opération annulée par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
