"""
core/profil_manager.py
User profile management logic for Groupama training bot.
"""
import logging , json , random
from pathlib import Path


def select_profil(chemin_fichier, type_personne=None, nb_caracteristiques=2, nb_objections=1, nb_aleas=1):
    """
    Charge le fichier de jeu de personnages et sélectionne des éléments pour un scénario.
    
    Args:
        chemin_fichier (str ou Path): Chemin vers le fichier JSON contenant les données
        type_personne (str, optional): Type de personne à sélectionner (Particulier, ACPS, Agriculteur)
        nb_caracteristiques (int, optional): Nombre de caractéristiques à sélectionner. Défaut: 3
        nb_objections (int, optional): Nombre d'objections à sélectionner. Défaut: 3
        nb_aleas (int, optional): Nombre d'aléas à sélectionner. Défaut: 1
    
    Returns:
        tuple: (scenario, prompt_client) - Dictionnaire contenant le scénario sélectionné et le prompt
    """
    # 1. Charger le fichier JSON
    chemin_fichier = Path(chemin_fichier)
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as f:
            donnees = json.load(f)
    except FileNotFoundError:
        print(f"Erreur: Le fichier {chemin_fichier} n'a pas été trouvé.")
        return None, None
    except json.JSONDecodeError:
        print(f"Erreur: Le fichier {chemin_fichier} n'est pas un JSON valide.")
        return None, None
    
    # Extraire la liste des types de personnes (exclure le type "format_entretien")
    types_personnes = [type_p for type_p in donnees["jeu_de_personnages"] 
                      if isinstance(type_p, dict) and type_p.get("type_de_personne")]


    # 2. Sélectionner le type de personne (selon le paramètre ou aléatoirement)
    if type_personne:
        # Rechercher le type de personne spécifié
        type_personne_selectionne = None
        for tp in types_personnes:
            if tp["type_de_personne"].lower() == type_personne.lower():
                type_personne_selectionne = tp
                break
        
        if not type_personne_selectionne:
            print(f"Type de personne '{type_personne}' non trouvé. Sélection aléatoire à la place.")
            type_personne_selectionne = random.choice(types_personnes)
    else:
        type_personne_selectionne = random.choice(types_personnes)
    
    type_nom = type_personne_selectionne["type_de_personne"]
    
    # 3. Sélectionner une personne aléatoirement dans ce type
    personne = random.choice(type_personne_selectionne["liste_personne"])
    
    # 4. Sélectionner les caractéristiques
    caracteristiques_disponibles = type_personne_selectionne.get("caracteristiques", [])
    nb_carac_dispo = len(caracteristiques_disponibles)
    nb_carac_select = min(nb_caracteristiques, nb_carac_dispo)
    
    if nb_carac_dispo > 0:
        caracteristiques = random.sample(caracteristiques_disponibles, nb_carac_select)
    else:
        caracteristiques = []
    
    # 5. Sélectionner les objections
    objections_disponibles = type_personne_selectionne.get("objections", [])
    nb_obj_dispo = len(objections_disponibles)
    nb_obj_select = min(nb_objections, nb_obj_dispo)
    
    if nb_obj_dispo > 0:
        objections = random.sample(objections_disponibles, nb_obj_select)
    else:
        objections = []
    
    # 6. Sélectionner les aléas
    aleas_disponibles = type_personne_selectionne.get("alea", [])
    nb_alea_dispo = len(aleas_disponibles)
    nb_alea_select = min(nb_aleas, nb_alea_dispo)
    
    if nb_alea_dispo > 0:
        if nb_alea_select == 1:
            aleas = [random.choice(aleas_disponibles)]
        else:
            aleas = random.sample(aleas_disponibles, nb_alea_select)
    else:
        aleas = []
    
    # 7. Construire le dictionnaire résultat
    scenario = {
        "type_de_personne": type_nom,
        "personne": personne,
        "caracteristiques": caracteristiques,
        "objections": objections,
        "aleas": aleas
    }
    
    # 8. Créer le prompt pour le client avec les nouveaux champs
    prompt_client =f"""
Vous incarnez **le client** lors d'un rendez-vous d'assurance santé avec un conseiller Groupama (l'utilisateur).

## 👤 VOTRE PROFIL

**Identité :**
- Nom : {personne['Nom']}
- Âge : {personne['Age']} ans
- Sexe : {personne['Sexe']}
- Profession : {personne['Profession']}
- Localisation : {personne['Localisation']}

**Situation personnelle :**
- Situation maritale : {personne['situation_maritale']}
- Nombre d'enfants : {personne['nombre_enfants']}
- Profil passerelle : {personne['profil_passerelle']}
- Aidant : {personne['aidant']}
- Contrat GMA existant : {personne['a_deja_contrat_gma']}
- Hobby : {personne['hobby']}

## 🎭 ÉLÉMENTS À INTÉGRER PROGRESSIVEMENT

**Votre situation personnelle** (à révéler naturellement, avec vos propres mots) :
{chr(10).join(f"• {carac}" for carac in caracteristiques)}

**Vos préoccupations** (EXPRIMER UNE SEULE FOIS au bon moment et s'en souvenir ) :
{chr(10).join(f"{i+1}. {obj}" for i, obj in enumerate(objections))}

**Événements personnels** (à mentionner progressivement, selon le contexte) :
{chr(10).join(f"{i+1}. {alea_item}" for i, alea_item in enumerate(aleas))}


"""
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print("voici les types de personnes dispos : ")
    print(personne)
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print("ssssssssssssssssssssssssssssssssssssss")

    # Retourner le dictionnaire et le prompt
    return scenario, prompt_client


class ProfilManager:
  def __init__(self, type_personne='Particulier', nb_caracteristiques=2, nb_objections=1, nb_aleas=1):
    chemin_jeu_de_personnages = 'data/jeu_de_personnages.json' 
    self._type_personne = type_personne
    self._personne= None
    self._profil = None
    self._prompt = None
    self._liste_questions = []
    self._current_profil = None
    self._initialize_profil(chemin_jeu_de_personnages, type_personne, nb_caracteristiques, nb_objections, nb_aleas)

  def _initialize_profil(self, chemin_jeu_de_personnages, type_personne, nb_caracteristiques, nb_objections, nb_aleas):
    """Initialize the profil using select_profil function"""


    self._profil, self._prompt = select_profil(
      chemin_jeu_de_personnages,
      type_personne=type_personne,
      nb_caracteristiques=nb_caracteristiques,
      nb_objections=nb_objections,
      nb_aleas=nb_aleas
    )
    if self._profil:
      self._type_personne = self._profil.get('type_de_personne')
      self._personne = self._profil.get('personne')
      self._current_profil = self._profil  # Keep current_profil in sync
    else:
      logging.error("select_profil n'a pas renvoyé de profil valide.")

  @property
  def profil(self):
    """Get the current profil"""
    return self._profil

  @profil.setter
  def profil(self, value):
    """Set the current profil"""
    self._profil = value
    self._prompt = None

  @property
  def current_profil(self):
    """Get the current active profil"""
    return self._current_profil

  @current_profil.setter
  def current_profil(self, value):
    """Set the current active profil"""
    self._current_profil = value
    self._profil = value  # Sync with _profil if needed
    self._prompt = None  # Reset prompt when switching profiles

  @property
  def prompt(self):
    """Get the current prompt"""
    return self._prompt

  @property
  def get_profil_type(self):
    """Get the type of the current profil"""
    if self._profil:
      return self._profil.get('type_de_personne')
    if self._type_personne:  # Add fallback to _type_personne
      return self._type_personne
    logging.warning("_profil est None, impossible de récupérer le type de profil.")
    return None

  def get_person_details(self):
    """Get the person details from the profil"""
    return self._profil.get('personne') if self._profil else None

  def get_caracteristiques(self):
    """Get the caracteristiques from the profil"""
    return self._profil.get('caracteristiques') if self._profil else None

  def get_objections(self):
    """Get the objections from the profil"""
    return self._profil.get('objections') if self._profil else None

  def get_contingencies(self):
    """Get the contingencies (aléas) from the profil"""
    return self._profil.get('aleas') if self._profil else None
  
  def get_person_details(self):
    """Get the person details from the profil"""
    return self._profil.get('personne') if self._profil else None


  @property
  def liste_questions(self):
    """Get the list of questions"""
    return self._liste_questions


#profilManagerprofil = ProfilManager(type_personne='Agriculteur')
#print(profilManagerprofil.profil)
# print(profilManagerprofil.get_profil_type(type_personne='Agriculteur'))





# # Pour tester la fonction
# if __name__ == "__main__":
#     # Exemple d'utilisation avec le nouveau format
#     chemin = "data/jeu_de_personnages.json"
    
#     # Version de base (tous les paramètres par défaut)
#     scenario1, prompt_client1 = select_profil(chemin)
#     print("=== SCENARIO 1 (Aléatoire) ===")
#     print("Scénario:", scenario1)
#     print("\nPrompt:", prompt_client1)
    
#     # Version avec type de personne spécifié
#     scenario2, prompt_client2 = select_profil(chemin, type_personne="Agriculteur")
#     print("\n=== SCENARIO 2 (Agriculteur) ===")
#     print("Scénario:", scenario2)
    
#     # Version avec nombre personnalisé de caractéristiques et d'objections
#     scenario3, prompt_client3 = select_profil(chemin, nb_caracteristiques=2, nb_objections=4)
#     print("\n=== SCENARIO 3 (Personnalisé) ===")
#     print("Scénario:", scenario3)