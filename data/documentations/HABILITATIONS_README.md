# 🔐 Système de Gestion des Habilitations - SimSan

## Vue d'ensemble

Le système de gestion des habilitations contrôle l'accès à l'application SimSan en vérifiant que les utilisateurs appartiennent à au moins un groupe d'habilitation autorisé.

## Architecture

### Composants

1. **`core/habilitations_manager.py`** : Gestionnaire principal des habilitations
2. **`admin/habilitations_config.json`** : Fichier de configuration sur le FileShare
3. **`templates/admin_habilitations.html`** : Interface d'administration
4. **Routes dans `app.py`** :
   - `/admin/habilitations` : Page de gestion
   - `/admin/habilitations/update` : API de mise à jour

### Flux d'authentification

```
1. Utilisateur se connecte via OAuth2 (Gauthiq)
2. Récupération des habilitations depuis l'API Gauthiq
3. Vérification contre la liste des groupes autorisés
4. ✅ Accès autorisé OU ❌ Accès refusé (page unauthorized.html)
```

## Groupes d'habilitation disponibles

| Entité | Groupe d'Habilitation |
|--------|----------------------|
| PVL    | GR_SIMSAN_UTILISATEURS_PVL |
| LBR    | GR_SIMSAN_UTILISATEURS_LBR |
| GROM   | GR_SIMSAN_UTILISATEURS_GROM |
| GPJ    | GR_SIMSAN_UTILISATEURS_GPJ |
| GPAT   | GR_SIMSAN_UTILISATEURS_GPAT |
| GOC    | GR_SIMSAN_UTILISATEURS_GOC |
| GNC    | GR_SIMSAN_UTILISATEURS_GNC |
| GGBH   | GR_SIMSAN_UTILISATEURS_GGBH |
| GCM    | GR_SIMSAN_UTILISATEURS_GCM |
| GASM   | GR_SIMSAN_UTILISATEURS_GASM |
| GSP    | GR_SIMSAN_UTILISATEURS_GSP |
| GPF    | GR_SIMSAN_UTILISATEURS_GPF |
| GOI    | GR_SIMSAN_UTILISATEURS_GOI |
| GNE    | GR_SIMSAN_UTILISATEURS_GNE |
| GMED   | GR_SIMSAN_UTILISATEURS_GMED |
| GGBS   | GR_SIMSAN_UTILISATEURS_GGBS |
| GES    | GR_SIMSAN_UTILISATEURS_GES |
| GCA    | GR_SIMSAN_UTILISATEURS_GCA |
| GANAS  | GR_SIMSAN_UTILISATEURS_GANAS |
| GAC    | GR_SIMSAN_UTILISATEURS_GAC |
| MUT    | GR_SIMSAN_UTILISATEURS_MUT |
| GRA    | GR_SIMSAN_UTILISATEURS_GRA |
| GPREV  | GR_SIMSAN_UTILISATEURS_GPREV |
| GGE    | GR_SIMSAN_UTILISATEURS_GGE |
| GAA    | GR_SIMSAN_UTILISATEURS_GAA |

## Utilisation

### Pour les administrateurs

1. **Accéder à l'interface**
   - Connectez-vous en tant qu'administrateur
   - Accédez à `/admin_suivis`
   - Cliquez sur "Gestion des Habilitations"

2. **Gérer les groupes**
   - Cochez les groupes à autoriser
   - Utilisez la barre de recherche pour filtrer
   - Utilisez "Tout sélectionner" / "Tout désélectionner" pour actions rapides
   - Cliquez sur "Enregistrer" pour appliquer les modifications

3. **Statistiques**
   - Nombre total de groupes
   - Nombre de groupes habilités
   - Nombre de groupes désactivés

### Configuration initiale

Par défaut, **tous les groupes sont habilités** lors de la première initialisation.

## Fichier de configuration

### Emplacement
```
/mnt/storage/admin/habilitations_config.json
```
(ou `data/admin/habilitations_config.json` en développement local)

### Structure
```json
{
  "groupes_habilites": [
    "GR_SIMSAN_UTILISATEURS_PVL",
    "GR_SIMSAN_UTILISATEURS_GCM",
    ...
  ],
  "derniere_modification": "2025-10-16T10:30:00",
  "modifie_par": "admin@example.com"
}
```

## API Programmatique

### Obtenir le gestionnaire
```python
from core.habilitations_manager import get_habilitations_manager

hab_manager = get_habilitations_manager()
```

### Vérifier l'accès d'un utilisateur
```python
has_access, message = hab_manager.user_has_access(user_habilitations)

if has_access:
    print(f"Accès autorisé : {message}")
else:
    print(f"Accès refusé : {message}")
```

### Obtenir les groupes habilités
```python
groupes = hab_manager.get_groupes_habilites()
# Retourne: ['GR_SIMSAN_UTILISATEURS_PVL', 'GR_SIMSAN_UTILISATEURS_GCM', ...]
```

### Mettre à jour les habilitations
```python
success, message = hab_manager.update_habilitations(
    groupes_habilites=['GR_SIMSAN_UTILISATEURS_PVL'],
    modifie_par='admin@example.com'
)
```

## Sécurité

### Points de contrôle

1. **Au callback OAuth2** (`auth/gauthiq.py` et `auth/gauthiq_d.py`)
   - Vérification immédiate après l'authentification
   - Redirection vers `unauthorized.html` si refus

2. **Logging**
   - Toutes les tentatives d'accès sont loguées
   - Incluant les groupes de l'utilisateur et la décision

3. **Protection admin**
   - Seuls les administrateurs peuvent modifier les habilitations
   - Liste définie dans `LISTE_ADMINS`

### Recommandations

- ⚠️ **Ne jamais désactiver tous les groupes** (sinon personne ne peut se connecter)
- 🔒 Vérifier régulièrement les logs d'accès
- 📝 Documenter chaque modification importante
- 🔄 Sauvegarder le fichier de configuration avant modifications

## Dépannage

### Problème : Personne ne peut se connecter

**Cause** : Tous les groupes sont désactivés ou configuration corrompue

**Solution** :
1. Accéder au FileShare
2. Éditer `/admin/habilitations_config.json`
3. Ajouter au moins un groupe dans `groupes_habilites`

### Problème : Utilisateur légitime refusé

**Cause** : Son groupe n'est pas dans la liste des habilités

**Solution** :
1. Vérifier ses groupes Gauthiq dans les logs
2. Activer le groupe correspondant via l'interface admin

### Problème : Configuration non sauvegardée

**Cause** : Problème de permissions FileShare

**Solution** :
1. Vérifier les permissions du répertoire `/admin`
2. Vérifier les logs d'erreur
3. Tester en local avec `data/admin/`

## Logs

Les actions importantes sont loguées avec les préfixes suivants :

```
✓ Configuration habilitations sauvegardée
✓ Accès autorisé - Groupes communs: GR_SIMSAN_UTILISATEURS_PVL
✗ Accès refusé - Aucun groupe habilité trouvé
⚠️ Aucun groupe habilité configuré - accès refusé par défaut
```

## Tests

### Test manuel

1. Créer un utilisateur de test avec un groupe spécifique
2. Désactiver ce groupe dans l'interface
3. Tenter de se connecter → doit être refusé
4. Réactiver le groupe
5. Tenter de se connecter → doit réussir

### Test de la configuration

```python
from core.habilitations_manager import get_habilitations_manager

hab_manager = get_habilitations_manager()

# Test configuration
config = hab_manager.get_configuration_complete()
print(f"Groupes habilités : {len([g for g in config['groupes'] if g['habilite']])}")

# Test utilisateur
test_habs = {
    'groups': ['GR_SIMSAN_UTILISATEURS_PVL']
}
has_access, msg = hab_manager.user_has_access(test_habs)
print(f"Accès : {has_access} - {msg}")
```

## Évolutions futures

- [ ] Gestion des rôles (admin, utilisateur, lecteur)
- [ ] Historique des modifications
- [ ] Export/Import de configuration
- [ ] API REST complète
- [ ] Intégration avec Active Directory
- [ ] Gestion granulaire par fonctionnalité

---

**Version** : 1.0  
**Date** : 2025-10-16  
**Auteur** : Équipe Développement SimSan
