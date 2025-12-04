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
# Flask removed - migrated to FastAPI
from typing import Dict, Any
from .prompt_synthese import construire_prompt_synthese
from .fonctions_fileshare import save_file_to_azure

# Configuration du logger pour utiliser le système centralisé
logger = logging.getLogger("synthetiser")


def extraire_json_robuste(texte):
    """
    Extrait et parse le JSON même si du texte parasite est présent
    Gère les cas où GPT ajoute du markdown ou du texte avant/après le JSON
    
    Args:
        texte (str): Texte brut contenant potentiellement du JSON
        
    Returns:
        dict: Objet JSON parsé
        
    Raises:
        ValueError: Si aucun JSON valide n'est trouvé
    """
    logger.debug("Début de l'extraction robuste du JSON")
    
    # Supprimer les marqueurs markdown courants
    texte_nettoye = re.sub(r'```json\s*', '', texte)
    texte_nettoye = re.sub(r'```\s*$', '', texte_nettoye)
    texte_nettoye = re.sub(r'```', '', texte_nettoye)
    
    # Trouver le premier { et le dernier }
    debut = texte_nettoye.find('{')
    fin = texte_nettoye.rfind('}')
    
    if debut == -1 or fin == -1 or fin <= debut:
        logger.error("Aucun objet JSON valide trouvé dans la réponse")
        logger.debug(f"Contenu reçu (premiers 500 chars): {texte[:500]}")
        raise ValueError("Aucun objet JSON trouvé dans la réponse de l'API")
    
    json_str = texte_nettoye[debut:fin+1]
    
    try:
        resultat = json.loads(json_str)
        logger.info("JSON extrait et parsé avec succès")
        return resultat
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON: {e}")
        logger.debug(f"JSON problématique (premiers 500 chars): {json_str[:500]}")
        
        # Tentative de correction des erreurs courantes
        try:
            # Remplacer les guillemets simples par des doubles
            json_str_corrige = json_str.replace("'", '"')
            resultat = json.loads(json_str_corrige)
            logger.warning("JSON parsé après correction des guillemets")
            return resultat
        except:
            pass
        
        raise ValueError(f"Impossible de parser le JSON: {str(e)}")


def valider_schema_synthese(data):
    """
    Valide que le JSON de synthèse contient toutes les clés obligatoires
    
    Args:
        data (dict): Données à valider
        
    Returns:
        tuple: (bool, list) - (est_valide, liste_des_erreurs)
    """
    erreurs = []
    
    # Vérifier les clés de premier niveau
    cles_obligatoires = ['synthese', 'vision_detaillee', 'recommandations']
    for cle in cles_obligatoires:
        if cle not in data:
            erreurs.append(f"Clé manquante au premier niveau: {cle}")
    
    # Vérifier la structure de 'synthese'
    if 'synthese' in data:
        cles_synthese = ['niveau_general', 'commentaire_global', 'timestamp']
        for cle in cles_synthese:
            if cle not in data['synthese']:
                erreurs.append(f"Clé manquante dans 'synthese': {cle}")
    
    # Vérifier la structure de 'vision_detaillee'
    if 'vision_detaillee' in data:
        dimensions_requises = [
            'maitrise_produit_technique',
            'decouverte_client_relationnel_conclusion',
            'traitement_objections_argumentation',
            'cross_selling_opportunites',
            'posture_charte_relation_client'
        ]
        for dimension in dimensions_requises:
            if dimension not in data['vision_detaillee']:
                erreurs.append(f"Dimension manquante dans 'vision_detaillee': {dimension}")
            else:
                # Vérifier les sous-clés de chaque dimension
                cles_dimension = ['niveau', 'points_positifs', 'points_negatifs', 
                                'ce_qui_devrait_etre_dit', 'reponse_suggeree']
                for cle in cles_dimension:
                    if cle not in data['vision_detaillee'][dimension]:
                        erreurs.append(f"Clé manquante dans '{dimension}': {cle}")
    
    # Vérifier la structure de 'recommandations'
    if 'recommandations' in data:
        cles_recommandations = ['principales_forces', 'axes_amelioration_prioritaires', 
                               'actions_correctives_immediates']
        for cle in cles_recommandations:
            if cle not in data['recommandations']:
                erreurs.append(f"Clé manquante dans 'recommandations': {cle}")
    
    est_valide = len(erreurs) == 0
    return est_valide, erreurs


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


def synthese_2(history, client, documents_reference, profil_manager, session_data: Dict[str, Any] = None):
    """
    Effectue une évaluation unique sur tout l'historique de la conversation
    en utilisant les documents de référence Groupama.
    VERSION AMÉLIORÉE avec garantie de JSON valide.

    Args:
        history: Historique de la conversation
        client: Client OpenAI configuré
        documents_reference: Documents de référence chargés
        profil_manager: Manager des profils clients
        session_data: Dictionnaire de session FastAPI (optionnel)

    Returns:
        dict: Résultats d'évaluation structurés pour automatisation
    """
    logger.info("Début de l'évaluation complète avec synthese_2 (version améliorée)")
    
    # 1. Préparer l'historique complet de la conversation
    historique_complet = _preparer_historique_pour_synthese(history)

    # 2. Détecter le profil client et charger le document spécifique
    document_profil_specifique = _charger_document_profil_client(profil_manager)

    # 3. Construire le prompt d'évaluation avec instructions JSON renforcées
    prompt_synthese = construire_prompt_synthese(
        documents_reference, 
        historique_complet, 
        document_profil_specifique, 
        profil_manager
    )
    
    # Ajouter un header JSON strict au début du prompt système
    json_header = """
⚠️ **CONSIGNES CRITIQUES DE FORMAT** ⚠️
Vous DEVEZ répondre EXCLUSIVEMENT avec un objet JSON valide.
- ❌ AUCUN texte explicatif avant le JSON
- ❌ AUCUN texte explicatif après le JSON
- ❌ AUCUNE balise markdown (pas de ```json ni ```)
- ✅ Commencez DIRECTEMENT par le caractère {
- ✅ Terminez DIRECTEMENT par le caractère }
- ✅ Toutes les chaînes doivent être entre guillemets doubles "
- ✅ Respectez EXACTEMENT la structure JSON fournie

"""
    prompt_synthese_complet = json_header + prompt_synthese
    
    # Sauvegarde du prompt pour debugging dans Azure FileShare
    try:
        user_folder = session_data.get('user_folder', None) if session_data else None

        if user_folder:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prompt_synthese_{timestamp}.txt"
            
            success, azure_path = save_file_to_azure(
                prompt_synthese_complet,
                'conversation',
                filename,
                user_folder
            )
            
            if success:
                logger.info(f"Prompt d'évaluation sauvegardé dans FileShare: {azure_path}")
            else:
                logger.warning("Échec de la sauvegarde du prompt dans FileShare")
        else:
            logger.warning("user_folder non disponible dans la session, prompt non sauvegardé")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du prompt: {str(e)}")
    
    # 4. Appeler l'API avec mécanisme de retry amélioré
    max_retries = 4
    logger.info(f"Tentatives d'évaluation avec un maximum de {max_retries} tentatives")
    
    for attempt in range(1, max_retries + 1):
        start_time = time.time()
        logger.info(f"Tentative {attempt}/{max_retries} - Début")
        
        try:
            # Appel à l'API OpenAI avec response_format pour garantir le JSON
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_m"),
                messages=[
                    {
                        "role": "system",
                        "content": prompt_synthese_complet
                    },
                    {
                        "role": "user",
                        "content": "Évaluez cette conversation et répondez UNIQUEMENT avec le JSON structuré demandé."
                    }
                ],
                response_format={"type": "json_object"},  # ← CRUCIAL pour forcer le JSON
                temperature=0,      # Déterminisme maximal
                top_p=1,
                seed=42,            # Reproductibilité
                max_tokens=4000,    # Augmenté pour les réponses complètes
                n=1,
                stream=False,
                timeout=120
            )

            # Traitement de la réponse
            api_response_time = time.time()
            logger.info("Réponse de l'API reçue, traitement en cours...")
            synthese_text = response.choices[0].message.content
            
            # Log de la réponse brute pour debugging
            logger.debug(f"Réponse brute (100 premiers chars): {synthese_text[:100]}")
            
            # 5. Extraction robuste du JSON
            try:
                resultats_json = extraire_json_robuste(synthese_text)
                logger.info("JSON extrait avec succès")
            except ValueError as e:
                logger.error(f"Échec d'extraction du JSON (tentative {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    return _creer_reponse_erreur(
                        "Échec d'extraction du JSON après toutes les tentatives",
                        synthese_text,
                        str(e),
                        history,
                        profil_manager,
                        max_retries
                    )
                continue
            
            # 6. Validation du schéma
            est_valide, erreurs = valider_schema_synthese(resultats_json)
            
            if not est_valide:
                logger.warning(f"Schéma JSON invalide (tentative {attempt}/{max_retries})")
                logger.warning(f"Erreurs de validation: {erreurs}")
                
                if attempt == max_retries:
                    # Dernière tentative : on retourne quand même avec warning
                    logger.error("Schéma invalide après toutes les tentatives, retour avec données partielles")
                    resultats_json["_avertissements_validation"] = {
                        "schema_invalide": True,
                        "erreurs": erreurs,
                        "message": "Le JSON a été retourné malgré des erreurs de validation"
                    }
                else:
                    # On réessaie
                    time.sleep(2)
                    continue
            
            # 7. Parser et enrichir les résultats
            resultats_structures = _parser_resultats_synthese_2(
                history, 
                json.dumps(resultats_json),  # Convertir en string pour compatibilité
                profil_manager
            )
            
            # Vérifier si le parsing a échoué
            if "erreur" in resultats_structures and "echec_parsing" in resultats_structures.get("statut", ""):
                logger.warning(f"Erreur de parsing détectée (tentative {attempt}/{max_retries})")
                if attempt == max_retries:
                    logger.error("Nombre maximum de tentatives atteint - échec du parsing")
                    return resultats_structures
                time.sleep(2)
                continue
            
            # ✅ Succès !
            duree_totale = time.time() - start_time
            logger.info(f"✅ Évaluation réussie à la tentative {attempt}/{max_retries}")
            logger.info(f"Durée totale: {duree_totale:.2f} secondes")
            
            # Ajouter des métadonnées de succès
            resultats_structures["_metadata_appel"] = {
                "tentative_reussie": attempt,
                "duree_totale_secondes": round(duree_totale, 2),
                "schema_valide": est_valide,
                "timestamp_reussite": datetime.now().isoformat()
            }
            
            return resultats_structures

        except Exception as e:
            error_duration = time.time() - start_time
            
            logger.error(f"Erreur lors de l'évaluation (tentative {attempt}/{max_retries}): {e}")
            logger.error(f"Type d'erreur: {type(e).__name__}")
            logger.info(f"Durée avant erreur: {error_duration:.2f} secondes")
            
            if attempt == max_retries:
                total_failed_duration = time.time() - start_time
                logger.error("❌ Nombre maximum de tentatives atteint - échec de l'évaluation")
                
                return {
                    "erreur": str(e),
                    "type_erreur": type(e).__name__,
                    "timestamp": datetime.now().isoformat(),
                    "statut": "echec_api",
                    "tentatives": max_retries,
                    "derniere_erreur": str(e),
                    "duree_totale_echec": f"{total_failed_duration:.2f}s",
                    "details_client": _extraire_details_client_securise(profil_manager),
                    "contexte": {
                        "nombre_messages": len(history) if history else 0,
                        "date_erreur": datetime.now().isoformat()
                    }
                }
            else:
                logger.info(f"Nouvelle tentative dans 2 secondes... ({attempt + 1}/{max_retries})")
                time.sleep(2)


def _creer_reponse_erreur(message_erreur, synthese_brute, erreur_parsing, 
                         history, profil_manager, tentatives):
    """
    Crée une réponse d'erreur structurée de manière sécurisée
    """
    return {
        "erreur": message_erreur,
        "synthese_brute": synthese_brute[:1000] if synthese_brute else "Aucune réponse",
        "erreur_parsing": erreur_parsing,
        "timestamp": datetime.now().isoformat(),
        "statut": "echec_parsing_final",
        "tentatives": tentatives,
        "details_client": _extraire_details_client_securise(profil_manager),
        "historique_conversation": {
            "nombre_messages": len(history) if history else 0
        }
    }


def _extraire_details_client_securise(profil_manager):
    """
    Extrait les détails du client de manière sécurisée (gestion des erreurs)
    """
    try:
        if not profil_manager:
            return {"statut": "profil_manager_indisponible"}
        
        person_details = profil_manager.get_person_details() or {}
        return {
            "nom": person_details.get('Nom', 'Non spécifié'),
            "age": person_details.get('Age', 'Non spécifié'),
            "profession": person_details.get('Profession', 'Non spécifié'),
            "type_personne": profil_manager.get_profil_type or 'Non spécifié'
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails client: {e}")
        return {"erreur_extraction": str(e)}


def _preparer_historique_pour_synthese(history):
    """
    Prépare l'historique complet de la conversation pour l'évaluation
    Filtre les messages d'erreur technique et leurs messages précédents
    
    Returns:
        str: Historique formaté pour l'évaluation
    """
    logger.info("Préparation de l'historique pour l'évaluation")
    if not history:
        return "Aucune conversation à évaluer."
    
    # Message d'erreur technique à filtrer
    message_erreur_technique = "Je suis désolé, mais je rencontre des difficultés techniques. Pouvez-vous reformuler ou essayer plus tard?"
    
    # Filtrer les messages d'erreur technique et leurs précédents
    history_filtered = []
    i = 0
    messages_supprimes = 0
    
    while i < len(history):
        message_actuel = history[i]
        
        # Vérifier si c'est un message d'erreur technique de l'Assistant
        if (message_actuel.get('role') == 'Assistant' and 
            message_actuel.get('text', '').strip() == message_erreur_technique):
            
            # Supprimer le message précédent s'il existe et qu'il vient de 'Vous'
            if (history_filtered and 
                history_filtered[-1].get('role') == 'Vous'):
                message_supprime_precedent = history_filtered.pop()
                messages_supprimes += 1
                logger.info(f"Message 'Vous' supprimé avant erreur technique: {message_supprime_precedent.get('text', '')[:50]}...")
            
            # Ne pas ajouter le message d'erreur technique
            messages_supprimes += 1
            logger.info("Message d'erreur technique de l'Assistant supprimé")
            
        else:
            # Ajouter le message normal à l'historique filtré
            history_filtered.append(message_actuel)
        
        i += 1
    
    logger.info(f"Filtrage terminé: {messages_supprimes} messages supprimés")
    
    # Vérifier si le dernier message n'est pas de 'Vous' et le supprimer si nécessaire
    if history_filtered and history_filtered[-1].get('role') != 'Vous':
        dernier_message = history_filtered.pop()
        logger.info(f"Dernier message non-utilisateur supprimé: {dernier_message.get('role')}")
    
    # Utilisation de la fonction historique_remap_roles pour convertir les rôles
    historique, formatted_history = historique_remap_roles(history_filtered)

    historique_formate = "=== HISTORIQUE COMPLET DE LA CONVERSATION ===\n\n"
    
    if not historique:
        historique_formate += "Aucune conversation valide à évaluer après filtrage.\n"
        logger.warning("Aucun message valide après filtrage")
        return historique_formate
    
    for i, message in enumerate(historique, 1):
        role = message.get('role', 'Inconnu')
        contenu = message.get('text', '')
        
        historique_formate += f"[{i:02d}] {role}: {contenu}\n\n"
    
    logger.info(f"Historique préparé pour l'évaluation: {len(historique)} messages valides")
    return historique_formate


def _parser_resultats_synthese_2(history, synthese_text, profil_manager):
    """
    Parse les résultats de l'évaluation et les structure pour automatisation
    VERSION AMÉLIORÉE avec meilleure gestion des erreurs
    
    Args:
        history: Historique de la conversation
        synthese_text (str): Texte brut de l'évaluation (JSON string)
        profil_manager: Manager des profils
        
    Returns:
        dict: Résultats structurés
    """
    try:
        # Utiliser la fonction d'extraction robuste
        resultats = extraire_json_robuste(synthese_text)
        
        # Validation des niveaux
        niveaux_valides = ["Très bien", "Bien", "Satisfaisant", "À améliorer"]
        
        # Valider le niveau général
        if resultats.get("synthese", {}).get("niveau_general") not in niveaux_valides:
            logger.warning(f"Niveau général invalide: {resultats.get('synthese', {}).get('niveau_general')}")
            resultats["synthese"]["niveau_general"] = "Satisfaisant"
        
        # Valider les niveaux détaillés
        for critere, details in resultats.get("vision_detaillee", {}).items():
            if details.get("niveau") not in niveaux_valides:
                logger.warning(f"Niveau invalide pour {critere}: {details.get('niveau')}")
                details["niveau"] = "Satisfaisant"

        # Récupérer les détails du client depuis ProfilManager
        details_client = _extraire_details_client_complet(profil_manager)
        
        # Préparer l'historique de conversation avec les rôles remappés
        historique_formate = _formater_historique_conversation(history)
        
        # Ajouter des métadonnées supplémentaires
        resultats["synthese_metadata"] = {
            "method": "synthese_2_amelioree",
            "timestamp": datetime.now().isoformat(),
            "conversation_length": len(history),
            "criteres_evalues": 5,
            "documents_utilises": [
                "description_offre", "tmgf", "exemples_remboursements",
                "methodes_commerciales_recommendees", "traitement_objections",
                "cg_vocabulaire", "cg_garanties", "cg_garanties_assistance", 
                "cg_contrat", "infos_commerciales", "charte_relation_client",
                "profil_client_specifique"
            ],
            "extraction_method": "robuste_avec_validation"
        }
        
        # Ajouter les détails du client
        resultats["details_client"] = details_client
        
        # Ajouter l'historique de conversation
        resultats["historique_conversation"] = historique_formate
        
        # Ajouter des informations supplémentaires sur le contexte
        resultats["contexte_synthese"] = {
            "profil_manager_actif": profil_manager is not None,
            "date_synthese": datetime.now().isoformat(),
            "parsing_reussi": True
        }
        
        logger.info("Parsing des résultats terminé avec succès")
        return resultats
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Échec du parsing JSON: {e}")
        
        # Créer une structure d'erreur enrichie
        details_client_erreur = _extraire_details_client_securise(profil_manager)
        historique_erreur = _formater_historique_erreur(history)
        
        return {
            "erreur": "Impossible de parser la synthese",
            "synthese_brute": synthese_text[:1000] if len(synthese_text) > 1000 else synthese_text,
            "erreur_parsing": str(e),
            "timestamp": datetime.now().isoformat(),
            "statut": "echec_parsing",
            "structure_attendue": "synthese_2_amelioree",
            "details_client": details_client_erreur,
            "historique_conversation": historique_erreur,
            "contexte_synthese": {
                "date_synthese": datetime.now().isoformat(),
                "parsing_reussi": False
            }
        }


def _extraire_details_client_complet(profil_manager):
    """
    Extrait tous les détails du client depuis le ProfilManager
    """
    if not profil_manager:
        return {
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
    
    try:
        person_details = profil_manager.get_person_details() or {}
        return {
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
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails client: {e}")
        return {"erreur_extraction": str(e)}


def _formater_historique_conversation(history):
    """
    Formate l'historique de conversation pour inclusion dans les résultats
    """
    historique_formate = {
        "nombre_messages": 0,
        "messages": [],
        "duree_conversation_estimee": "0 minutes"
    }
    
    if not history:
        return historique_formate
    
    try:
        historique_remappe, _ = historique_remap_roles(history)
        
        messages_formated = []
        for i, message in enumerate(historique_remappe, 1):
            messages_formated.append({
                "numero_message": i,
                "role": message.get('role', 'Inconnu'),
                "texte": message.get('text', ''),
                "timestamp": message.get('timestamp', datetime.now().isoformat()),
                "msg_num_original": message.get('msg_num', i)
            })
        
        historique_formate = {
            "nombre_messages": len(messages_formated),
            "messages": messages_formated,
            "duree_conversation_estimee": f"{len(messages_formated) * 2} minutes"
        }
    except Exception as e:
        logger.error(f"Erreur lors du formatage de l'historique: {e}")
        historique_formate["erreur_formatage"] = str(e)
    
    return historique_formate


def _formater_historique_erreur(history):
    """
    Formate un historique partiel en cas d'erreur (premiers messages seulement)
    """
    if not history:
        return {
            "nombre_messages": 0,
            "messages_partiels": [],
            "note": "Aucun historique disponible"
        }
    
    try:
        historique_remappe, _ = historique_remap_roles(history)
        messages_partiels = [
            {
                "role": msg.get('role'), 
                "texte": msg.get('text')[:100] + "..." if len(msg.get('text', '')) > 100 else msg.get('text')
            } 
            for msg in historique_remappe[:5]
        ]
        
        return {
            "nombre_messages": len(history),
            "messages_partiels": messages_partiels,
            "note": "Historique partiel (5 premiers messages) en raison d'une erreur"
        }
    except Exception as e:
        return {
            "nombre_messages": len(history),
            "erreur": str(e),
            "note": "Impossible de formater l'historique"
        }


def _charger_document_profil_client(profil_manager):
    """
    Charge le document de profil spécifique selon l'âge et le profil_passerelle du client
    
    Returns:
        str: Contenu du document de profil ou chaîne vide si non trouvé
    """
    # Extraire les informations du client
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


def conversation_history_to_html(conversation_history, profil_manager):
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
            