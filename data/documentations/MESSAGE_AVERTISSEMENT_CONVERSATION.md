# Message d'avertissement - Conversation fictive

## 📋 Modifications apportées

### 1. **CSS (`templates/index.html`)** - Lignes ~138-197

Ajout du style pour le message d'avertissement :

```css
/* Message d'avertissement conversation fictive */
.conversation-disclaimer {
  position: sticky;
  top: 0;
  background: linear-gradient(135deg, #fff8e1 0%, #fffbf0 100%);
  border: 2px solid #ffa726;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(255, 167, 38, 0.2);
  z-index: 100;
  animation: slideInDown 0.5s ease-out;
}
```

**Caractéristiques du design :**
- ✅ **Sticky** : Reste visible en haut même en scrollant
- ✅ **Gradient** : Dégradé jaune/beige doux et professionnel
- ✅ **Bordure orange** : Attire l'attention sans être agressive
- ✅ **Icône ℹ️** : Badge circulaire orange avec icône d'information
- ✅ **Animation** : Apparition fluide avec `slideInDown`
- ✅ **Box-shadow** : Légère ombre pour se détacher du fond
- ✅ **z-index: 100** : Toujours au-dessus des messages

### 2. **HTML (`templates/index.html`)** - Ligne ~1112

Structure HTML du message :

```html
<div class="conversation-disclaimer">
  <div class="conversation-disclaimer-icon">ℹ️</div>
  <div class="conversation-disclaimer-text">
    <strong>Conversation fictive :</strong> 
    Le client est un personnage simulé par l'intelligence artificielle.
  </div>
</div>
```

### 3. **JavaScript (`static/js/app.js`)** - Ligne ~645

Préservation du message dans `updateConversation()` :

```javascript
// Sauvegarder le message d'avertissement avant de vider
const disclaimerElement = conversation.querySelector('.conversation-disclaimer');

conversation.innerHTML = "";

// Restaurer le message d'avertissement en premier
if (disclaimerElement) {
    conversation.appendChild(disclaimerElement);
}
```

### 4. **JavaScript (`templates/index.html`)** - 3 endroits

Protection du message lors des réinitialisations :

**a) Changement de profil** (ligne ~1435) :
```javascript
const disclaimer = conversationDiv.querySelector('.conversation-disclaimer');
conversationDiv.innerHTML = '';
if (disclaimer) conversationDiv.appendChild(disclaimer);
```

**b) Reset conversation** (ligne ~1476) :
```javascript
const disclaimer = conversationDiv.querySelector('.conversation-disclaimer');
conversationDiv.innerHTML = '';
if (disclaimer) conversationDiv.appendChild(disclaimer);
```

**c) Après synthèse** (ligne ~1520) :
```javascript
const disclaimer = conversationDiv.querySelector('.conversation-disclaimer');
conversationDiv.innerHTML = '';
if (disclaimer) conversationDiv.appendChild(disclaimer);
```

## 🎨 Aperçu visuel

```
┌─────────────────────────────────────────────────────┐
│  ℹ️  Conversation fictive : Le client est un        │
│     personnage simulé par l'intelligence            │
│     artificielle.                                   │
└─────────────────────────────────────────────────────┘
  ⬇️ (reste fixé en haut lors du scroll)
┌─────────────────────────────────────────────────────┐
│ Vous: Bonjour, je souhaite...                       │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│ Assistant: Bonjour, je suis là pour...              │
└─────────────────────────────────────────────────────┘
```

## ✅ Comportement

Le message :
- ✅ **Apparaît immédiatement** au chargement de la page
- ✅ **Reste visible en haut** (sticky) pendant le scroll
- ✅ **Persiste** après changement de profil
- ✅ **Persiste** après reset de conversation
- ✅ **Persiste** après une synthèse
- ✅ **Ne gêne pas** l'utilisation de l'application
- ✅ **S'intègre visuellement** avec le design Groupama

## 🎯 Message affiché

> **Conversation fictive :** Le client est un personnage simulé par l'intelligence artificielle.

## 📐 Palette de couleurs

- **Background** : Gradient #fff8e1 → #fffbf0 (beige/jaune pastel)
- **Bordure** : #ffa726 (orange)
- **Texte** : #5d4037 (marron foncé)
- **Texte accentué** : #e65100 (orange foncé)
- **Badge icône** : #ffa726 (orange)
- **Ombre** : rgba(255, 167, 38, 0.2)

## 📱 Responsive

Le message s'adapte automatiquement à la largeur de l'écran grâce à :
- `flex-direction: row` avec `gap: 12px`
- `flex-shrink: 0` pour l'icône (toujours visible)
- `flex: 1` pour le texte (prend l'espace disponible)
- Padding et marges proportionnels

## 🔧 Test

Pour vérifier le bon fonctionnement :

1. ✅ Charger la page → Le message apparaît en haut
2. ✅ Échanger des messages → Le message reste visible
3. ✅ Scroller dans la conversation → Le message reste en haut
4. ✅ Changer de profil → Le message reste présent
5. ✅ Réinitialiser la conversation → Le message reste présent
6. ✅ Faire une synthèse → Le message reste présent après redirection
