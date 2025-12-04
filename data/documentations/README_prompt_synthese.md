# Module prompt_synthese

## Description

Ce module a été créé pour externaliser la logique de construction du prompt de synthèse des conversations depuis le fichier `synthetiser.py`. Cette refactorisation améliore la maintenabilité du code en séparant les responsabilités.

## Motivation

Le prompt de synthèse était précédemment défini directement dans la fonction `_construire_prompt_synthese_2()` du fichier `synthetiser.py`. Cette approche présentait plusieurs inconvénients :

- Code difficile à maintenir (prompt très long intégré dans la logique métier)
- Difficile de modifier le template du prompt sans affecter le reste du code
- Manque de réutilisabilité des templates de prompt
- Code peu lisible avec des chaînes de caractères très longues

## Nouvelle architecture

### Fichiers concernés

1. **`prompt_synthese.py`** (nouveau) : Module dédié à la gestion des templates de prompt
2. **`synthetiser.py`** (modifié) : Utilise désormais le module externalisé

### Fonctionnalités du module prompt_synthese

#### Templates disponibles

- `get_format_json()` : Format JSON attendu pour la réponse
- `get_mission_template()` : Template de la mission d'évaluation avec placeholders pour le profil client
- `get_instructions_template()` : Instructions spécifiques d'évaluation
- `get_documents_reference_template()` : Template pour l'injection des documents de référence

#### Fonction principale

```python
construire_prompt_synthese(documents_reference, historique_complet, document_profil_specifique, profil_manager)
```

Cette fonction remplace l'ancienne `_construire_prompt_synthese_2()` et offre les améliorations suivantes :

#### Nouvelles fonctionnalités ajoutées

1. **Intégration complète du profil client** : 
   - Nom, âge, profession, localisation
   - Situation familiale, nombre d'enfants
   - Type de profil, profil passerelle
   - Statut aidant, contrats existants
   - Hobbies et centres d'intérêt

2. **Template modulaire** : 
   - Chaque section du prompt est dans une fonction séparée
   - Facilite les modifications et tests unitaires
   - Permet la réutilisation de sections dans d'autres contextes

3. **Meilleure gestion des placeholders** :
   - Substitution automatique des variables du profil
   - Gestion des valeurs par défaut si informations manquantes
   - Formatage cohérent des données

## Utilisation

### Avant (ancien code)
```python
# Dans synthetiser.py
prompt_synthese = _construire_prompt_synthese_2(documents_reference, historique_complet, document_profil_specifique)
```

### Après (nouveau code)
```python
# Import du module
from .prompt_synthese import construire_prompt_synthese

# Utilisation
prompt_synthese = construire_prompt_synthese(documents_reference, historique_complet, document_profil_specifique, profil_manager)
```

## Avantages de cette refactorisation

1. **Séparation des responsabilités** :
   - `synthetiser.py` se concentre sur la logique métier
   - `prompt_synthese.py` gère uniquement les templates

2. **Maintenabilité améliorée** :
   - Modifications du prompt sans impact sur le reste du code
   - Structure modulaire facilitant les tests
   - Code plus lisible et organisé

3. **Extensibilité** :
   - Facile d'ajouter de nouveaux templates
   - Possibilité de créer des variantes de prompts
   - Réutilisation dans d'autres modules

4. **Intégration du profil enrichie** :
   - Toutes les informations du profil client sont maintenant incluses
   - Personnalisation poussée de l'évaluation
   - Meilleure contextualisation pour l'IA

## Structure du prompt généré

Le prompt final est composé de :

1. **Mission et contexte** : Objectifs et historique de conversation
2. **Profil client détaillé** : Toutes les informations disponibles sur le client
3. **Critères d'évaluation** : 5 dimensions d'évaluation avec niveaux
4. **Format JSON** : Structure attendue pour la réponse
5. **Instructions spécifiques** : Méthodologie d'évaluation détaillée
6. **Documents de référence** : Tous les documents Groupama injectés

## Migration

L'ancienne fonction `_construire_prompt_synthese_2()` a été supprimée du fichier `synthetiser.py`. Le comportement reste identique mais avec l'ajout des informations de profil client dans le prompt.

## Tests recommandés

Après cette modification, il est recommandé de :

1. Tester la génération de prompt avec différents profils clients
2. Vérifier que tous les placeholders sont correctement substitués
3. S'assurer que le format JSON généré est valide
4. Tester les cas où certaines informations de profil sont manquantes
