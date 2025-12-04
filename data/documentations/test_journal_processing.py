#!/usr/bin/env python3
"""
Script de test pour la fonction process_journal_csv
"""

import sys
sys.path.insert(0, '/home/gs8678/projet/simsan/infra/src')

from core.azure_sync import AzureFileShareSync

# Contenu de test (comme dans le fichier journal.csv)
test_content = """user,mail,event,date_heure,note_user,duree_conversation,nombre_mots_total,nombre_mots_assistant,nombre_mots_vous,nombre_total_echanges
gs8678,Mouhssine.Benomar@groupama.com,connexion,2025/10/10 21:11:31,--,--,--,--,--,--
gs8678,Mouhssine.Benomar@groupama.com,note utilisateur,2025/10/10 21:21:24,5,--,--,--,--,--
gs8678,Mouhssine.Benomar@groupama.com,génération de synthèse,2025/10/10 21:21:42,--,00:00:00,1730,666,1064,66
"""

print("=" * 80)
print("TEST : Traitement du fichier journal.csv")
print("=" * 80)

print("\n📥 CONTENU AVANT TRAITEMENT:")
print("-" * 80)
print(test_content)
print("-" * 80)

# Créer une instance temporaire (sans connexion Azure nécessaire pour ce test)
sync = AzureFileShareSync(
    connection_string="",
    share_name="test",
    interval_minutes=10
)

# Appliquer le traitement
print("\n🔄 APPLICATION DU TRAITEMENT...")
print("-" * 80)
result = sync.process_journal_csv(test_content)
print("-" * 80)

print("\n📤 CONTENU APRÈS TRAITEMENT:")
print("-" * 80)
print(result)
print("-" * 80)

# Vérifier le résultat
lines = result.strip().split('\n')
print(f"\n✅ RÉSULTAT:")
print(f"   - Lignes avant: {len(test_content.strip().split(chr(10)))}")
print(f"   - Lignes après: {len(lines)}")
print(f"   - Réduction: {len(test_content.strip().split(chr(10))) - len(lines)} ligne(s)")

# Vérifier que la ligne de synthèse contient bien la note
for line in lines:
    if 'génération de synthèse' in line:
        cols = line.split(',')
        if len(cols) > 4:
            note = cols[4]
            print(f"   - Note dans la ligne de synthèse: {note}")
            if note == '5':
                print(f"   ✅ SUCCÈS : La note a bien été fusionnée !")
            else:
                print(f"   ❌ ÉCHEC : La note devrait être 5, mais c'est: {note}")

# Vérifier qu'il n'y a plus de ligne "note utilisateur"
has_note_line = any('note utilisateur' in line for line in lines[1:])  # Skip header
if has_note_line:
    print(f"   ❌ ÉCHEC : La ligne 'note utilisateur' n'a pas été supprimée")
else:
    print(f"   ✅ SUCCÈS : La ligne 'note utilisateur' a bien été supprimée")

print("\n" + "=" * 80)
