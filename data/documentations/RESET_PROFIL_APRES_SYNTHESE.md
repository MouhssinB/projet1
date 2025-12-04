# Réinitialisation automatique du profil après synthèse

## 📋 Modifications apportées

### 1. Backend (`app.py`) - Route `/synthetiser`

**Ligne ~766-820** : Ajout de la réinitialisation automatique du profil après synthèse

#### Fonctionnalités ajoutées :
- ✅ Sélection aléatoire d'un nouveau profil parmi les profils disponibles
- ✅ Création d'un nouveau `ProfilManager` avec le profil sélectionné
- ✅ Sauvegarde du nouveau profil en session
- ✅ Récupération des détails de la nouvelle personne (nom, caractéristiques)
- ✅ Gestion des erreurs avec fallback
- ✅ Logging détaillé de toutes les opérations

#### Code ajouté :
```python
# Réinitialiser le profil avec un nouveau profil aléatoire
try:
    import random
    
    # Sélectionner un profil aléatoire parmi les profils disponibles
    available_profiles = [p['profile'] for p in dico_profil]
    new_profile = random.choice(available_profiles)
    
    async_logger.info("Generating new random profile after synthesis",
                     new_profile=new_profile,
                     available_profiles=available_profiles)
    
    # Créer un nouveau ProfilManager avec le profil sélectionné
    new_pm = ProfilManager(type_personne=new_profile)
    save_profil_manager_to_session(new_pm)
    
    # Récupérer les détails de la nouvelle personne
    person_details = new_pm.get_person_details()
    person_name = person_details.get("Nom", "Inconnu")
    
    async_logger.info("New profile initialized successfully after synthesis",
                     profile=new_profile,
                     person_name=person_name,
                     person_details=person_details)
    
    profile_reset_success = True
    profile_reset_message = f"Nouveau profil : {new_profile} - {person_name}"
    new_profile_data = {
        "type": new_profile,
        "name": person_name,
        "details": person_details
    }
    
except Exception as profile_error:
    async_logger.warning("Profile reset failed after synthesis", error=str(profile_error))
    profile_reset_success = False
    profile_reset_message = f"Erreur lors de la réinitialisation du profil: {str(profile_error)}"
    new_profile_data = None
```

#### Réponse JSON enrichie :
```json
{
    "success": true,
    "filepath": "...",
    "filename": "...",
    "message": "Synthèse terminée, conversation réinitialisée et nouveau profil généré",
    "reset_performed": true,
    "conversation_cleared": true,
    "profile_reset": true,
    "profile_message": "Nouveau profil : Particulier - Marie Dupont",
    "new_profile": {
        "type": "Particulier",
        "name": "Marie Dupont",
        "details": { /* détails complets */ }
    }
}
```

### 2. Frontend (`templates/index.html`) - Gestionnaire de synthèse

**Ligne ~1440** : Ajout de la notification du nouveau profil

#### Modifications :
- ✅ Détection du nouveau profil dans la réponse
- ✅ Affichage d'une alerte informative avec les détails du profil
- ✅ Logging console des informations du profil
- ✅ Délai de 500ms avant redirection (temps de lire le message)

#### Code ajouté :
```javascript
// Afficher un message de notification si un nouveau profil a été généré
if (data.profile_reset && data.new_profile) {
  const profileInfo = data.new_profile;
  const profileMessage = `✅ Analyse terminée !\n\n🔄 Nouveau profil généré :\n📋 Type : ${profileInfo.type}\n👤 Nom : ${profileInfo.name}\n\nRedirection vers le tableau de bord...`;
  alert(profileMessage);
  console.log('✅ Nouveau profil après synthèse:', profileInfo);
} else if (data.reset_performed) {
  console.log('✅ Conversation réinitialisée après synthèse');
}
```

## 🔄 Flux de travail complet

1. **Utilisateur termine une conversation** avec le profil actuel (ex: "Agriculteur - Jean Martin")
2. **Clic sur "Analyser"** → Synthèse de la conversation en cours
3. **Backend génère la synthèse** → Sauvegarde HTML + JSON
4. **Reset automatique** :
   - ✅ Compteur remis à 0
   - ✅ Historique de conversation vidé
   - ✅ **NOUVEAU** : Profil aléatoire sélectionné (ex: "Particulier - Sophie Leroy")
5. **Frontend affiche** :
   ```
   ✅ Analyse terminée !
   
   🔄 Nouveau profil généré :
   📋 Type : Particulier
   👤 Nom : Sophie Leroy
   
   Redirection vers le tableau de bord...
   ```
6. **Redirection** vers `/suivi_syntheses` avec le rapport en surbrillance
7. **Utilisateur peut commencer** une nouvelle conversation avec le nouveau profil

## 📊 Profils disponibles

Les profils sont définis dans `app.py` (ligne ~223) :
```python
dico_profil = [
    {"profile": "Particulier", "label": "Particulier"},
    {"profile": "ACPS", "label": "ACPS"},
    {"profile": "Agriculteur", "label": "Agriculteur"}
]
```

Le système sélectionne **aléatoirement** un profil parmi ces 3 options après chaque synthèse.

## 🔍 Logging

Tous les événements sont loggés dans le système de logging asynchrone :
- `"Generating new random profile after synthesis"` → Profil sélectionné
- `"New profile initialized successfully after synthesis"` → Profil créé avec succès
- `"Profile reset failed after synthesis"` → Erreur lors de la réinitialisation
- `"Conversation and profile reset successfully after synthesis"` → Tout s'est bien passé

## ⚠️ Gestion des erreurs

Si la réinitialisation du profil échoue :
- ✅ La synthèse est quand même sauvegardée
- ✅ La conversation est vidée
- ⚠️ Le profil reste inchangé
- 📝 L'erreur est loggée
- 📨 Le frontend reçoit `"profile_reset": false` dans la réponse

## 🎯 Avantages

1. **Expérience utilisateur fluide** : Pas besoin de changer manuellement le profil entre chaque conversation
2. **Variété des tests** : Chaque nouvelle conversation démarre avec un profil différent
3. **Traçabilité** : Tous les changements de profil sont loggés
4. **Robustesse** : Gestion complète des erreurs avec fallback
5. **Transparence** : L'utilisateur est informé du nouveau profil avant la redirection

## 🔧 Test

Pour tester la fonctionnalité :

1. Démarrer l'application Flask
2. Se connecter et démarrer une conversation
3. Échanger au moins 6 messages
4. Cliquer sur "Analyser"
5. Observer :
   - ✅ Le message de confirmation avec le nouveau profil
   - ✅ La conversation vidée
   - ✅ La redirection vers le tableau de bord
   - ✅ Les logs dans la console serveur

## 📝 Notes techniques

- Le module `random` est importé localement dans le try/except pour éviter tout impact sur les performances
- La fonction `save_profil_manager_to_session()` est réutilisée (même logique que `set_profile()`)
- Le frontend utilise `alert()` pour une notification immédiate et visible
- Un délai de 500ms permet à l'utilisateur de lire le message avant la redirection
