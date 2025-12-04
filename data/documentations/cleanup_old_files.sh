#!/bin/bash

# Script de nettoyage des fichiers obsolètes après migration
# À exécuter APRÈS avoir testé que tout fonctionne correctement

echo "=========================================="
echo "🧹 NETTOYAGE FICHIERS OBSOLÈTES"
echo "=========================================="
echo ""

# Répertoire de travail
cd /home/gs8678/projet/simsan/infra/src

echo "Fichiers à supprimer :"
echo ""

# 1. Système de synchronisation (obsolète)
if [ -f "core/azure_sync.py" ]; then
    echo "  ✅ core/azure_sync.py (système de synchronisation obsolète)"
else
    echo "  ⚠️  core/azure_sync.py (déjà supprimé)"
fi

# 2. Backups de fonctions_fileshare
if [ -f "core/fonctions_fileshare.py.old" ]; then
    echo "  ✅ core/fonctions_fileshare.py.old (backup ancien système)"
else
    echo "  ⚠️  core/fonctions_fileshare.py.old (déjà supprimé)"
fi

if [ -f "core/fonctions_fileshare_backup.py" ]; then
    echo "  ✅ core/fonctions_fileshare_backup.py (backup ancien système)"
else
    echo "  ⚠️  core/fonctions_fileshare_backup.py (déjà supprimé)"
fi

echo ""
echo "=========================================="
read -p "Voulez-vous supprimer ces fichiers ? (o/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo ""
    echo "🗑️  Suppression en cours..."
    
    # Supprimer les fichiers
    [ -f "core/azure_sync.py" ] && rm "core/azure_sync.py" && echo "  ✓ core/azure_sync.py supprimé"
    [ -f "core/azure_sync.pyc" ] && rm "core/azure_sync.pyc" && echo "  ✓ core/azure_sync.pyc supprimé"
    [ -f "core/fonctions_fileshare.py.old" ] && rm "core/fonctions_fileshare.py.old" && echo "  ✓ core/fonctions_fileshare.py.old supprimé"
    [ -f "core/fonctions_fileshare_backup.py" ] && rm "core/fonctions_fileshare_backup.py" && echo "  ✓ core/fonctions_fileshare_backup.py supprimé"
    
    # Nettoyer les caches Python
    if [ -d "core/__pycache__" ]; then
        rm -f "core/__pycache__/azure_sync.*.pyc"
        rm -f "core/__pycache__/fonctions_fileshare.*.pyc"
        echo "  ✓ Caches Python nettoyés"
    fi
    
    echo ""
    echo "✅ Nettoyage terminé !"
else
    echo ""
    echo "⚠️  Nettoyage annulé. Les fichiers sont conservés."
fi

echo ""
echo "=========================================="
echo "📋 RÉSUMÉ"
echo "=========================================="
echo ""
echo "Fichiers actifs (nouveau système) :"
echo "  ✅ core/storage_manager.py"
echo "  ✅ core/fonctions_fileshare.py (nouvelle version)"
echo "  ✅ core/fonctions.py (adapté)"
echo "  ✅ core/async_logger.py (adapté)"
echo "  ✅ app.py (adapté)"
echo ""
echo "Documentation :"
echo "  📖 STORAGE_DIRECT.md - Guide complet"
echo "  📖 MODIFICATIONS_SUMMARY.md - Résumé des modifications"
echo "  📖 MIGRATION_COMPLETE.md - Statut de la migration"
echo ""
