#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module pour la synthèse des conversations
Fournit des fonctions autonomes pour la synthèse et le traitement des historiques de conversation
"""

import os
import json
import time
import glob
import re
import logging
from datetime import datetime
from pathlib import Path
import openai
from openai import AzureOpenAI
from .prompt_synthese_v2 import construire_prompt_synthese

# Configuration du logger pour utiliser le système centralisé
logger = logging.getLogger("synthetiser")
# Ne pas configurer de handlers ici - ils seront hérités du logger racine configuré dans app.py



def calcule_statistiques_conv(conversation_history):
    """
    Calcule les statistiques d'une conversation à partir de son historique.
    
    Args:
        conversation_history (list): Liste des messages de la conversation
        
    Returns:
        dict: Dictionnaire JSON contenant les statistiques
    """
    
    if not conversation_history:
        return {
            "duree_conversation": "00:00:00",
            "nombre_mots_total": 0,
            "nombre_mots_assistant": 0,
            "nombre_mots_vous": 0,
            "nombre_total_echanges": 0
        }
    
    # Calcul de la durée de conversation
    premier_timestamp = datetime.fromisoformat(conversation_history[0]["timestamp"])
    dernier_timestamp = datetime.fromisoformat(conversation_history[-1]["timestamp"])
    duree = dernier_timestamp - premier_timestamp
    
    # Conversion en format HH:MM:SS
    heures = duree.seconds // 3600
    minutes = (duree.seconds % 3600) // 60
    secondes = duree.seconds % 60
    duree_formatee = f"{heures:02d}:{minutes:02d}:{secondes:02d}"
    
    # Initialisation des compteurs
    nombre_mots_total = 0
    nombre_mots_assistant = 0
    nombre_mots_vous = 0
    nombre_total_echanges = len(conversation_history)
    
    # Comptage des mots pour chaque message
    for message in conversation_history:
        text = message["text"].strip()
        if text:  # Éviter les messages vides
            # Comptage des mots (séparés par des espaces)
            mots = len(text.split())
            nombre_mots_total += mots
            
            # Comptage par rôle
            if message["role"] == "Assistant":
                nombre_mots_assistant += mots
            elif message["role"] == "Vous":
                nombre_mots_vous += mots
    
    # Construction du résultat
    statistiques = {
        "duree_conversation": duree_formatee,
        "nombre_mots_total": nombre_mots_total,
        "nombre_mots_assistant": nombre_mots_assistant,
        "nombre_mots_vous": nombre_mots_vous,
        "nombre_total_echanges": nombre_total_echanges
    }
    
    return statistiques


def historique_remap_roles(history):
    """
    Remape les rôles des messages dans l'historique
    
    Args:
        history: Liste des messages de la conversation
    
    Returns:
        tuple: (historique remapé, historique formaté)
    """
    logger.info(f"Remappage des rôles pour {len(history) if history else 0} messages")
    
    if not history:
        logger.warning("Historique vide, aucun remappage effectué")
        return [], ""
    
    # Mapping des rôles pour affichage et traitement
    role_mapping = {
        'system': 'Système',
        'assistant': 'Bot',
        'Bot': 'Bot',
        'user': 'Vous',
        'Vous': 'Vous',
        'Demande du Client': 'Vous',
        'Réponse du Bot': 'Bot'
    }
    
    # Conversion pour l'historique complet et remappage des rôles
    historique = []
    historique_formate = ""
    
    for message in history:
        # Extraire le rôle et le contenu
        role_original = message.get('role', 'unknown')
        content = message.get('content', message.get('text', ''))
        
        # Remap du rôle
        role = role_mapping.get(role_original, role_original)
        
        # Ajout à l'historique
        historique.append({
            'role': role,
            'text': content
        })
        
        # Formatage pour affichage
        historique_formate += f"{role}: {content}\n\n"
    
    logger.debug(f"Remappage terminé: {len(historique)} messages")
    return historique, historique_formate






def synthese_2_v2(history, client, documents_reference , profil_manager):
    """
    Effectue une évaluation unique sur tout l'historique de la conversation
    en utilisant les documents de référence Groupama.
    
    Args:
        history: Historique de la conversation
        client: Client OpenAI configuré
        documents_reference: Documents de référence chargés
    
    Returns:
        dict: Résultats d'évaluation structurés pour automatisation
    """
    logger.info("Début de l'évaluation complète avec synthese_2")
    
    print("fffffffffffffffffffffffffffffffffff")
    print(profil_manager.profil)
    print("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii")



    # 1. Préparer l'historique complet de la conversation
    historique_complet = _preparer_historique_pour_synthese(history)
    #print(f"Historique complet préparé: {historique_complet}...")  # Affiche les 100 premiers caractères pour vérification

    # 2. Détecter le profil client et charger le document spécifique
    document_profil_specifique = _charger_document_profil_client(profil_manager)

    # 3. Construire le prompt d'évaluation en utilisant le module externalisé
    prompt_synthese = construire_prompt_synthese(documents_reference, historique_complet, document_profil_specifique, profil_manager)
    
    # Sauvegarde du prompt pour debugging
    with open(f'data/conversations/prompt_synthese_{datetime.now().isoformat()}.txt', 'w', encoding='utf-8') as f:
        f.write(prompt_synthese)
    logger.info("Prompt d'évaluation construit avec succès")
    
    # 4. Appeler l'API avec mécanisme de retry
    max_retries = 4
    logger.info(f"Tentatives d'évaluation avec un maximum de {max_retries} tentatives")
    


    for attempt in range(1, max_retries + 1):
        start_time = time.time()
        logger.info(f"Tentative {attempt}/{max_retries} - Début")
        import random
        try:
            # Appel à l'API OpenAI
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_m"),     # snapshot / deployment figé
                messages=[
                    {
                        "role": "system",
                        "content": prompt_synthese
                    },
                    {
                        "role": "user",
                        "content": f"Évaluez la conversation suivante : {historique_complet}"
                    }
                ],
                temperature=0,
                top_p=1,
                seed=42,
                max_tokens=3000,
                n=1,                 # implicite mais on le fixe pour la clarté
                stream=False,
                timeout=120
            )
            # response = client.responses.create(
            #     model=os.getenv("AZURE_OPENAI_DEPLOYMENT_m"),
            #     input=prompt_synthese
            # )

            # print(response.output_text)
            # synthese_text = response.output_text
            # print(response)

            # Traitement de la réponse
            api_response_time = time.time()
            logger.info("Réponse de l'API reçue, traitement en cours...")
            synthese_text = response.choices[0].message.content
            
            # 5. Parser et structurer les résultats
            resultats_structures = _parser_resultats_synthese_2(history, synthese_text , profil_manager)
            
            # Si le parsing a échoué, on réessaie
            if "erreur" in resultats_structures and "echec_parsing" in resultats_structures.get("statut", ""):
                logger.warning(f"Erreur de parsing détectée (tentative {attempt}/{max_retries})")
                if attempt == max_retries:
                    logger.error("Nombre maximum de tentatives atteint - échec du parsing")
                    return resultats_structures
                continue
            
            # Si tout s'est bien passé, sauvegarder et retourner
            with open(f'data/syntheses/z_synthese_complete_{datetime.now().isoformat()}.json', 'w', encoding='utf-8') as f:
                json.dump(resultats_structures, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Évaluation réussie à la tentative {attempt}")
            return resultats_structures

        except Exception as e:
            error_duration = time.time() - start_time
            
            logger.error(f"Erreur lors de l'évaluation (tentative {attempt}/{max_retries}): {e}")
            logger.info(f"Durée avant erreur: {error_duration:.3f} secondes")
            
            if attempt == max_retries:
                total_failed_duration = time.time() - start_time
                logger.error("Nombre maximum de tentatives atteint - échec de l'évaluation")
                
                return {
                    "erreur": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "statut": "echec",
                    "tentatives": max_retries,
                    "derniere_erreur": str(e),
                    "duree_totale_echec": f"{total_failed_duration:.3f}s"
                }
            else:
                logger.info("Nouvelle tentative dans 2 secondes...")
                time.sleep(2)  # Pause de 2 secondes entre les tentatives



def _preparer_historique_pour_synthese(history):
    """
    Prépare l'historique complet de la conversation pour l'évaluation
    
    Returns:
        str: Historique formaté pour l'évaluation
    """
    logger.info("Préparation de l'historique pour l'évaluation")
    if not history:
        return "Aucune conversation à évaluer."
    
    if history and history[-1].get('role') != 'Vous':
        history.pop()
    
    # Utilisation de la fonction historique_remap_roles pour convertir les rôles
    historique, formatted_history = historique_remap_roles(history)

    # Check if historique is not empty and last message role is not 'Demande du Client'



    historique_formate = "=== HISTORIQUE COMPLET DE LA CONVERSATION ===\n\n"
    
    for i, message in enumerate(historique, 1):
        role = message.get('role', 'Inconnu')
        contenu = message.get('text', '')
        
        historique_formate += f"[{i:02d}] {role}: {contenu}\n\n"
    
    logger.info("Historique préparé pour l'évaluation")
    return historique_formate

def _parser_resultats_synthese_2(history, synthese_text , profil_manager):
    """
    Parse les résultats de l'évaluation et les structure pour automatisation
    
    Args:
        history: Historique de la conversation
        synthese_text (str): Texte brut de l'évaluation
        
    Returns:
        dict: Résultats structurés
    """
    try:
        # Tenter de parser le JSON directement
        import json
        # Nettoyage du JSON
        start_index = synthese_text.find("{")
        end_index = synthese_text.rfind("}")
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_data = synthese_text[start_index:end_index + 1]
        
        resultats = json.loads(json_data)
        
        # Validation des niveaux
        niveaux_valides = ["Très bien", "Bien", "Satisfaisant", "À améliorer"]
        # Valider le niveau général
        if resultats.get("synthese", {}).get("niveau_general") not in niveaux_valides:
            resultats["synthese"]["niveau_general"] = "Satisfaisant"
        
        # Valider les niveaux détaillés
        for critere, details in resultats.get("vision_detaillee", {}).items():
            if details.get("niveau") not in niveaux_valides:
                details["niveau"] = "Satisfaisant"

        # Récupérer les détails du client depuis ProfilManager
        details_client = {}
        if profil_manager:
            # Récupérer les détails de la personne
            person_details = profil_manager.get_person_details() or {}
            details_client = {
                "nom": person_details.get('Nom', 'Non spécifié'),
                "age": person_details.get('Age', 'Non spécifié'),
                "sexe": person_details.get('Sexe', 'Non spécifié'),
                "profession": person_details.get('Profession', 'Non spécifié'),
                "localisation": person_details.get('Localisation', 'Non spécifié'),
                "situation_maritale": person_details.get('situation_maritale', 'Non spécifié'),
                "nombre_enfants": person_details.get('nombre_enfants', 'Non spécifié'),
                "profil_passerelle": person_details.get('profil_passerelle', 'Non spécifié'),
                "aidant": person_details.get('aidant', 'Non spécifié'),
                "a_deja_contrat_gma": person_details.get('a_deja_contrat_gma', 'Non spécifié'),
                "hobby": person_details.get('hobby', 'Non spécifié'),
                "type_personne": profil_manager.get_profil_type or 'Non spécifié'
            }
        else:
            # Valeurs par défaut si profil_manager n'est pas disponible
            details_client = {
                "nom": "Non spécifié",
                "age": "Non spécifié",
                "sexe": "Non spécifié",
                "profession": "Non spécifié",
                "localisation": "Non spécifié",
                "situation_maritale": "Non spécifié",
                "nombre_enfants": "Non spécifié",
                "profil_passerelle": "Non spécifié",
                "aidant": "Non spécifié",
                "a_deja_contrat_gma": "Non spécifié",
                "hobby": "Non spécifié",
                "type_personne": "Non spécifié"
            }
        
        # Préparer l'historique de conversation avec les rôles remappés
        historique_formate = []
        if history:
            historique_remappe, _ = historique_remap_roles(history)
            for i, message in enumerate(historique_remappe, 1):
                historique_formate.append({
                    "numero_message": i,
                    "role": message.get('role', 'Inconnu'),
                    "texte": message.get('text', ''),
                    "timestamp": message.get('timestamp', datetime.now().isoformat()),
                    "msg_num_original": message.get('msg_num', i)
                })
        
        # Ajouter des métadonnées supplémentaires
        resultats["synthese_metadata"] = {
            "method": "synthese_2_simplifiee",
            "timestamp": datetime.now().isoformat(),
            "conversation_length": len(history),
            "criteres_evalues": 5,
            "documents_utilises": [
                "description_offre", "tmgf", "exemples_remboursements",
                "methodes_commerciales_recommendees", "traitement_objections",
                "cg_vocabulaire", "cg_garanties", "cg_garanties_assistance", 
                "cg_contrat", "infos_commerciales", "charte_relation_client",
                "profil_client_specifique"
            ]
        }
        
        # Ajouter les détails du client
        resultats["details_client"] = details_client
        
        # Ajouter l'historique de conversation
        resultats["historique_conversation"] = {
            "nombre_messages": len(historique_formate),
            "messages": historique_formate,
            "duree_conversation_estimee": f"{len(historique_formate) * 2} minutes"
        }
        
        # Ajouter des informations supplémentaires sur le contexte
        resultats["contexte_synthese"] = {
            "profil_manager_actif": profil_manager is not None,
            "date_synthese": datetime.now().isoformat()
        }
        
        return resultats
        
    except json.JSONDecodeError as e:
        # Si le parsing JSON échoue, créer une structure d'erreur enrichie
        # Récupérer quand même les détails du client pour l'erreur
        details_client_erreur = {}
        historique_erreur = []
        
        try:
            if profil_manager:
                person_details = profil_manager.get_person_details() or {}
                details_client_erreur = {
                    "nom": person_details.get('Nom', 'Non spécifié'),
                    "type_personne": profil_manager.get_profil_type or 'Non spécifié'
                }
            
            if history:
                historique_remappe, _ = historique_remap_roles(history)
                historique_erreur = [{"role": msg.get('role'), "texte": msg.get('text')} 
                                for msg in historique_remappe[:5]]  # Limiter à 5 messages pour l'erreur
        except:
            pass  # En cas d'erreur, on garde les dictionnaires vides
        
        return {
            "erreur": "Impossible de parser la synthese",
            "synthese_brute": synthese_text,
            "erreur_parsing": str(e),
            "timestamp": datetime.now().isoformat(),
            "statut": "echec_parsing",
            "structure_attendue": "synthese_2_simplifiee",
            "details_client": details_client_erreur,
            "historique_conversation": {
                "nombre_messages": len(history) if history else 0,
                "messages_partiels": historique_erreur,
                "note": "Historique partiel en raison de l'erreur de parsing"
            },
            "contexte_synthese": {
                "date_synthese": datetime.now().isoformat()
            }
        }

def _charger_document_profil_client(profil_manager):
    """
    Charge le document de profil spécifique selon l'âge et le profil_passerelle du client
    
    Returns:
        str: Contenu du document de profil ou chaîne vide si non trouvé
    """
    # Extraire les informations du client depuis l'historique ou le contexte
    age_client = profil_manager.profil.get('Age', 40)
    profil_passerelle = profil_manager.profil.get('profil_passerelle', 'Famille')

    # Mapping des fichiers selon le tableau fourni
    fichier_profil = None
    
    if profil_passerelle == "Aidant":
        fichier_profil = "data/txt/profil_aidants.txt"
    elif profil_passerelle == "Famille":
        if 45 <= age_client <= 54:
            fichier_profil = "data/txt/profil_familles_installees_45_54.txt"
        elif 30 <= age_client <= 44:
            fichier_profil = "data/txt/Profil_jeune_famille_30_44.txt"
    elif profil_passerelle == "Jeune client":
        if 18 <= age_client <= 29:
            fichier_profil = "data/txt/Profil_jeunes_actifs_18_29.txt"
    elif profil_passerelle == "Senior":
        if 55 <= age_client <= 64:
            fichier_profil = "data/txt/profil_jeunes_senior_55_64.txt"
        elif age_client >= 75:
            fichier_profil = "data/txt/profil_retraite_aide_sup75.txt"
        elif 65 <= age_client <= 74:
            fichier_profil = "data/txt/profil_retraite_en_forme_65_74.txt"
    
    if fichier_profil:
        try:
            with open(fichier_profil, 'r', encoding='utf-8') as f:
                contenu = f.read()
            logger.info(f"Document profil chargé: {fichier_profil}")
            return contenu
        except FileNotFoundError:
            logger.warning(f"Fichier profil non trouvé: {fichier_profil}")
            return ""
        except Exception as e:
            logger.error(f"Erreur lors du chargement du profil {fichier_profil}: {e}")
            return ""
    else:
        logger.warning(f"Aucun document profil trouvé pour âge={age_client}, profil={profil_passerelle}")
        return ""

def conversation_history_to_html(conversation_history , profil_manager):
    """
    Prend en entrée l'historique de conversation (liste de dicts)
    et crée un fichier HTML dans le dossier ./conversations.
    Retourne le chemin vers le fichier HTML créé.
    Le HTML inclut un bloc d'informations sur la personne (nom, âge, profession, localisation).
    """
    # Récupération des infos nécessaires
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_type = profil_manager.get_profil_type or "Particulier"
    person_details = profil_manager.get_person_details() or {}
    person_name = person_details.get("Nom", "Inconnu").replace(" ", "_")
    age = person_details.get("Age", "N/A")
    profession = person_details.get("Profession", "N/A")
    localisation = person_details.get("Localisation", "N/A")

    # Génération du HTML
    html = [
        "<!DOCTYPE html>",
        "<html lang='fr'>",
        "<head>",
        "<meta charset='utf-8'/>",
        "<title>Historique de conversation</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; background: #f7f7f7; padding: 2em; }",
        ".msg { margin-bottom: 1em; padding: 1em; border-radius: 8px; max-width: 600px; }",
        ".Commercial { background: #e0f7fa; align-self: flex-start; }",
        ".Client { background: #fffde7; align-self: flex-start; }",
        ".role { font-weight: bold; margin-bottom: 0.3em; }",
        ".container { display: flex; flex-direction: column; gap: 0.5em; }",
        ".person-info { background: #e8f5e9; padding: 1em; margin-bottom: 1.5em; border-radius: 6px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h2>Historique de conversation</h2>",
        "<div class='person-info'>",
        f"<p><strong>Profil:</strong> {profile_type}</p>",
        f"<p><strong>Nom:</strong> {person_name.replace('_',' ')}</p>",
        f"<p><strong>Âge:</strong> {age}</p>",
        f"<p><strong>Profession:</strong> {profession}</p>",
        f"<p><strong>Localisation:</strong> {localisation}</p>",
        "</div>",
        "<div class='container'>"
    ]

    # Remap roles for display
    historique, _ = historique_remap_roles(conversation_history)
    for msg in historique:
        role = msg.get("role", "Inconnu")
        text = msg.get("text", "")
        html.append(
            f"<div class='msg {role}'>"
            f"<div class='role'>{role}</div>"
            f"<div class='text'>{text}</div>"
            "</div>"
        )
    html.append("</div></body></html>")
    html_content = "\n".join(html)
    # html_filename = f"data/conversations/conversation_{profile_type}_{person_name}_{timestamp}.html"
    html_filename = f"conversation_{profile_type}_{person_name}_{timestamp}.html"

    return html_content, str(html_filename)

def delete_old_files(max_files=50):
    """
    Supprime les vieux fichiers, ne gardant que les max_files plus récents
    """
    for directory in ['data/conversations', 'data/syntheses']:
        try:
            # Vérifie si le répertoire existe, sinon le crée
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Répertoire {directory} créé")
                return
                
            files = sorted(Path(directory).glob("*.*"), key=os.path.getmtime)
            if len(files) <= max_files:
                logger.info(f"Pas de fichiers à supprimer (total: {len(files)}, max: {max_files})")
                return
                
            files_to_delete = files[:-max_files]
            for f in files_to_delete:
                f.unlink()
                logger.info(f"Fichier supprimé: {f}")
                
            logger.info(f"Suppression de {len(files_to_delete)} anciens fichiers, conservation des {max_files} plus récents.")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des anciens fichiers: {e}")











