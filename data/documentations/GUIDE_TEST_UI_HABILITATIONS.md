# 🧪 Guide de Test - Interface Éditable des Habilitations

## ✅ Prérequis
- ✓ Application démarrée (`uv run app.py`)
- ✓ Authentifié avec un compte admin (gs8678 dans LISTE_ADMINS)
- ✓ Endpoint `/admin/habilitations/config` ajouté (ligne 1144-1171 de app.py)

## 🎯 Test #1 : Chargement Initial des Groupes

### Objectif
Vérifier que l'interface charge correctement les 4 groupes depuis `habilitations_config.json`

### Étapes
1. **Accéder à la page** : http://localhost:5004/admin/habilitations
2. **Ouvrir la Console Développeur** : F12 → Onglet "Console"
3. **Vérifier la requête** :
   - Onglet "Network" → Chercher `/admin/habilitations/config`
   - Status attendu : **200 OK**
   - Réponse attendue :
     ```json
     {
       "groupes_habilites": [
         "GR_SIMSAN_UTILISATEURS_GGE",
         "GR_SIMSAN_UTILISATEURS_GAA", 
         "GR_SIMSAN_ADMIN",
         "GR"
       ],
       "derniere_modification": "2025-10-16T17:22:51.582805",
       "modifie_par": "gs8678"
     }
     ```

4. **Vérifier l'affichage** :
   - Tableau doit afficher **4 lignes**
   - Colonnes : Préfixe Groupe | Actions
   - Chaque ligne doit avoir un bouton 🗑️ (supprimer)
   - Chaque préfixe doit être éditable (clic pour modifier)

### ✅ Critères de Succès
- [x] 4 lignes visibles dans le tableau
- [x] Pas d'erreur JavaScript dans la console
- [x] Requête GET /admin/habilitations/config retourne 200
- [x] Statistiques affichent "4 groupes"

### ❌ En cas d'échec
- Si tableau vide : Vérifier console JavaScript pour erreurs
- Si 403 Forbidden : Vérifier que user est dans LISTE_ADMINS
- Si 404 : Vérifier que le endpoint existe (grep "/admin/habilitations/config" app.py)

---

## 🎯 Test #2 : Édition Inline d'un Groupe

### Objectif
Vérifier qu'on peut modifier un groupe existant

### Étapes
1. **Cliquer sur le préfixe** "GR" dans le tableau
2. **Vérifier** :
   - Le texte devient éditable (input field)
   - La ligne devient **orange** (classe `row-modified`)
3. **Modifier** : Remplacer "GR" par "GR_TEST"
4. **Cliquer ailleurs** pour valider
5. **Vérifier** :
   - La ligne reste orange
   - Le statut passe à "Modifié: 1"

### ✅ Critères de Succès
- [x] Ligne devient orange après modification
- [x] Nouveau texte "GR_TEST" visible
- [x] Compteur "Modifié: 1" affiché

### ⚠️ Contraintes
- **Préfixes dupliqués interdits** : Erreur si "GR_TEST" existe déjà
- **Validation stricte** : Pas d'espaces, pas de caractères spéciaux (sauf _ et -)

---

## 🎯 Test #3 : Ajout d'un Nouveau Groupe

### Objectif
Vérifier qu'on peut ajouter un nouveau groupe

### Étapes
1. **Cliquer** sur le bouton **➕ Ajouter un groupe**
2. **Vérifier** :
   - Une nouvelle ligne apparaît en haut du tableau
   - Ligne est **verte** (classe `row-new`)
   - Input field avec placeholder "Nouveau préfixe..."
3. **Saisir** : "GR_SIMSAN_TESTEUR"
4. **Cliquer ailleurs** pour valider
5. **Vérifier** :
   - La ligne reste verte
   - Le statut passe à "Nouveau: 1"
   - Le compteur total devient "5 groupes"

### ✅ Critères de Succès
- [x] Ligne verte ajoutée
- [x] Compteur "Nouveau: 1" affiché
- [x] Total passe à "5 groupes"

---

## 🎯 Test #4 : Suppression d'un Groupe

### Objectif
Vérifier qu'on peut supprimer un groupe

### Étapes
1. **Identifier** une ligne à supprimer (ex: "GR_SIMSAN_UTILISATEURS_GAA")
2. **Cliquer** sur le bouton **🗑️** de cette ligne
3. **Confirmer** la suppression dans l'alerte JavaScript
4. **Vérifier** :
   - La ligne disparaît immédiatement
   - Le statut passe à "Supprimé: 1"
   - Le compteur total diminue

### ✅ Critères de Succès
- [x] Ligne supprimée de l'interface
- [x] Compteur "Supprimé: 1" affiché
- [x] Total passe à "3 groupes" (si on supprime 1 sur 4)

---

## 🎯 Test #5 : Enregistrement des Modifications

### Objectif
**CRITIQUE** : Vérifier que les modifications sont sauvegardées en base et appliquées en temps réel

### Étapes
1. **Effectuer plusieurs modifications** :
   - Ajouter : "GR_SIMSAN_TESTEUR"
   - Modifier : "GR" → "GR_SIMSAN"
   - Supprimer : "GR_SIMSAN_UTILISATEURS_GAA"

2. **Cliquer** sur le bouton **💾 Enregistrer les modifications**

3. **Vérifier la requête POST** (Console → Network):
   ```
   POST /admin/habilitations/update
   Status: 200 OK
   Body envoyé : {"groupes_habilites": ["GR_SIMSAN_UTILISATEURS_GGE", "GR_SIMSAN_ADMIN", "GR_SIMSAN", "GR_SIMSAN_TESTEUR"]}
   ```

4. **Vérifier le fichier JSON** :
   ```bash
   cat /home/gs8678/projet/simsan/infra/src/data/admin/habilitations_config.json
   ```
   - Doit contenir les nouveaux groupes
   - Champ `derniere_modification` doit être mis à jour
   - Champ `modifie_par` doit être "gs8678"

5. **Vérifier l'application en temps réel** :
   - **Logs Flask** doivent montrer la revérification des habilitations
   - **Comportement** : 
     - Si vous supprimez le groupe qui donne votre accès (ex: "GR"), vous serez **déconnecté immédiatement**
     - Si vous ajoutez un groupe, les utilisateurs avec ce préfixe auront **accès immédiat**

### ✅ Critères de Succès
- [x] POST /admin/habilitations/update retourne 200
- [x] JSON file mis à jour avec nouvelles valeurs
- [x] Message de succès affiché : "✅ Modifications enregistrées avec succès"
- [x] Compteurs réinitialisés (Modifié: 0, Nouveau: 0, Supprimé: 0)
- [x] **CRITIQUE** : Habilitations revérifiées au prochain request (log "🔍 VÉRIFICATION DES HABILITATIONS")

---

## 🎯 Test #6 : Application Immédiate des Modifications

### Objectif
**TEST DE NON-RÉGRESSION** : Vérifier que les modifications sont appliquées SANS REDÉMARRAGE

### Étapes
1. **Avant modification** :
   - Notez les logs de vérification des habilitations
   - Exemple : `✅ MATCH avec 'GR_SMS_ADMIN_ENTITE_GCM'`

2. **Modifier les groupes** :
   - Supprimer "GR" (votre groupe d'accès actuel)
   - Enregistrer

3. **Recharger la page** (F5) ou naviguer vers `/`

4. **Vérifier les logs** :
   ```
   🔍 VÉRIFICATION DES HABILITATIONS - CORRESPONDANCE PARTIELLE
   📋 Groupes autorisés configurés: 3  # (4 - 1 supprimé)
      1. GR_SIMSAN_UTILISATEURS_GGE
      2. GR_SIMSAN_ADMIN
      3. GR_SIMSAN_TESTEUR
   ❌ ACCÈS REFUSÉ - Aucune correspondance
   ```

5. **Résultat attendu** :
   - Vous êtes **redirigé vers /login**
   - Message d'erreur : "Accès Révoqué - Vos habilitations ont été modifiées"
   - **Preuve** : Les modifications sont appliquées IMMÉDIATEMENT

### ✅ Critères de Succès
- [x] Aucun redémarrage nécessaire
- [x] Habilitations rechargées depuis JSON au prochain request
- [x] Utilisateur déconnecté si ses groupes ne matchent plus
- [x] Logs montrent la nouvelle liste de groupes

---

## 🎯 Test #7 : Recherche et Filtrage

### Objectif
Vérifier que la barre de recherche fonctionne

### Étapes
1. **Saisir** "ADMIN" dans le champ de recherche
2. **Vérifier** :
   - Seules les lignes contenant "ADMIN" sont visibles
   - Exemple : "GR_SIMSAN_ADMIN" visible, "GR_SIMSAN_UTILISATEURS_GGE" masqué
3. **Effacer** la recherche
4. **Vérifier** : Toutes les lignes réapparaissent

### ✅ Critères de Succès
- [x] Filtrage case-insensitive
- [x] Recherche en temps réel (sans bouton)
- [x] Compteur "X groupes affichés (sur Y total)"

---

## 🧪 Tests Avancés

### Test Edge Case #1 : Préfixes Dupliqués
**Action** : Essayer d'ajouter "GR_SIMSAN_ADMIN" (déjà existant)  
**Résultat Attendu** : ❌ Erreur "Ce préfixe existe déjà"

### Test Edge Case #2 : Caractères Invalides
**Action** : Essayer d'ajouter "GR SIMSAN" (avec espace)  
**Résultat Attendu** : ❌ Erreur "Caractères invalides (seuls lettres, chiffres, _, - autorisés)"

### Test Edge Case #3 : Enregistrement Sans Modifications
**Action** : Cliquer sur 💾 sans faire de changement  
**Résultat Attendu** : ℹ️ Message "Aucune modification à enregistrer"

### Test Edge Case #4 : Refresh Après Modification Non-Sauvegardée
**Action** : Modifier "GR" → "GR_TEST", puis F5 SANS enregistrer  
**Résultat Attendu** : Alerte "Vous avez des modifications non sauvegardées. Êtes-vous sûr ?"

---

## 📊 Checklist Finale

### Interface
- [ ] Tableau charge les 4 groupes initiaux
- [ ] Édition inline fonctionne (ligne orange)
- [ ] Ajout de ligne fonctionne (ligne verte)
- [ ] Suppression fonctionne avec confirmation
- [ ] Recherche/filtrage fonctionne
- [ ] Statistiques mises à jour en temps réel

### Backend
- [ ] GET /admin/habilitations/config retourne JSON
- [ ] POST /admin/habilitations/update sauvegarde en JSON
- [ ] Fichier JSON mis à jour avec timestamp
- [ ] Logs montrent "modifié par: gs8678"

### Temps Réel
- [ ] Modifications appliquées au prochain request (SANS REDÉMARRAGE)
- [ ] Utilisateur déconnecté si habilitations révoquées
- [ ] Logs montrent "🔍 VÉRIFICATION DES HABILITATIONS" avec nouvelle config
- [ ] Préfixes nouvellement ajoutés donnent accès immédiatement

---

## 🐛 Debugging

### Problème : Tableau vide
```javascript
// Console → F12
fetch('/admin/habilitations/config')
  .then(r => r.json())
  .then(data => console.log(data))
// Doit retourner : {"groupes_habilites": [...], ...}
```

### Problème : 403 Forbidden
```python
# Vérifier dans app.py ligne 1155
LISTE_ADMINS = ["gs8678", "Mouhssine.Benomar@groupama.com"]
# Vérifier session:
user_name = session.get('user_name')  # Doit être "gs8678"
```

### Problème : Modifications non appliquées
```bash
# Vérifier que le decorator revérifie les habilitations
grep -A 20 "def login_required" /home/gs8678/projet/simsan/infra/src/auth/gauthiq_d.py
# Doit contenir : hab_manager.user_has_access(user_habilitations)
```

---

## 📝 Documentation Associée

- **Guide Temps Réel** : `/home/gs8678/projet/simsan/infra/src/HABILITATIONS_TEMPS_REEL.md`
- **Réponse Quick** : `/home/gs8678/projet/simsan/infra/src/REPONSE_PRISE_EN_COMPTE_IMMEDIATE.md`
- **Code Source UI** : `/home/gs8678/projet/simsan/infra/src/templates/admin_habilitations.html`
- **Code Backend** : `/home/gs8678/projet/simsan/infra/src/app.py` (lignes 1144-1171)
- **Manager** : `/home/gs8678/projet/simsan/infra/src/core/habilitations_manager.py`

---

## 🚀 Prochaines Étapes

1. ✅ **Tester l'interface** avec ce guide
2. 📝 **Reporter les bugs** si trouvés
3. 🎨 **Améliorer l'UI** si besoin (CSS, animations)
4. 🔒 **Tester en production** avec gauthiq_p.py (HTTPS)
5. 📚 **Former les admins** à l'utilisation de l'interface
