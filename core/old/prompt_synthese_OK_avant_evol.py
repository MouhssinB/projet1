#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module pour la gestion du prompt de synthèse des conversations
Contient les templates et fonctions pour construire le prompt d'évaluation
"""

from datetime import datetime

def get_format_json():
    """
    Retourne le format JSON attendu pour la synthèse
    
    Returns:
        str: Template JSON avec placeholder pour timestamp
    """
    return """
    {
        "synthese": {
        "niveau_general": "[Très bien/Bien/Satisfaisant/À améliorer]",
        "commentaire_global": "[Appréciation générale de la performance du conseiller]",
        "timestamp": "TIMESTAMP_PLACEHOLDER"
        },
        "vision_detaillee": {
        "maitrise_produit_technique": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[Ce qui a été bien fait dans ce domaine ]",
            "points_negatifs": "[liste exhaustive des erreurs identifiées]",
            "ce_qui_devrait_etre_dit": "[Ce que le conseiller aurait dû dire ou faire : corrige les erreurs]",
            "reponse_suggeree": "[si niveau 'Satisfaisant' ou 'À améliorer':  créer une réponse commerciale optimale, sinon renseigner 'Rien à améliorer']"
        },
        "decouverte_client_relationnel_conclusion": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[Ce qui a été bien fait dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[Ce que le conseiller aurait dû dire ou faire]",
            "reponse_suggeree": "[si niveau 'Satisfaisant' ou 'À améliorer': créer une réponse commerciale optimale, sinon renseigner 'Rien à améliorer']"
        },
        "traitement_objections_argumentation": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[Ce qui a été bien fait dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[Ce que le conseiller aurait dû dire ou faire]",
            "reponse_suggeree": "[si niveau 'Satisfaisant' ou 'À améliorer': créer une réponse commerciale optimale, sinon renseigner 'Rien à améliorer']"
        },
        "cross_selling_opportunites": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[Ce qui a été bien fait dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[Ce que le conseiller aurait dû dire ou faire selon le profil client]",
            "reponse_suggeree": "[si niveau 'Satisfaisant' ou 'À améliorer': créer une réponse commerciale optimale, sinon renseigner 'Rien à améliorer']"
        },
        "posture_charte_relation_client": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[Ce qui a été bien fait dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[Ce que le conseiller aurait dû dire ou faire selon la charte relation client]",
            "reponse_suggeree": "[si niveau 'Satisfaisant' ou 'À améliorer': créer une réponse commerciale optimale, sinon renseigner 'Rien à améliorer']"
        }
        },
        "recommandations": {
        "principales_forces": [
            "[Force 1 identifiée]",
            "[Force 2 identifiée]",
            "[Force 3 identifiée]"
        ],
        "axes_amelioration_prioritaires": [
            "[Axe prioritaire 1]",
            "[Axe prioritaire 2]",
            "[Axe prioritaire 3]"
        ],
        "actions_correctives_immediates": [
            "[Action corrective concrète 1]",
            "[Action corrective concrète 2]",
            "[Action corrective concrète 3]"
        ]
        }
    }
    """

def get_mission_template():
    """
    Retourne le template de la mission d'évaluation
    
    Returns:
        str: Template de mission avec placeholders
    """
    return """
    <prompt>
        <mission>
        Vous êtes un expert en évaluation de conversations commerciales dans le domaine de l'assurance santé.
        Le but est d'evaluer le travail du conseiller client Groupama sur la base de l'historique de la conversation.
        Vous devez fournir une évaluation détaillée et structurée de la performance du conseiller.
        Vous devez vous baser sur les documents de référence fournis et l'historique complet.
        Il FAUT ETRE LE MOINS VERBEUX POSSIBLE, et aller droit au but.
        </mission>
        <contexte>
        Voici l'historique complet de la conversation : {historique_complet}
        </contexte>
        <profil_client>
        Informations sur le profil client :
        - Nom: {profil_nom}
        - Âge: {profil_age}
        - Profession: {profil_profession}
        - Situation: {profil_situation}
        - Localisation: {profil_localisation}
        - Type de profil: {profil_type}
        - Profil passerelle: {profil_passerelle}
        - Aidant: {profil_aidant}
        - Contrat GMA existant: {profil_contrat_gma}
        - Nombre d'enfants: {profil_enfants}
        - Hobby: {profil_hobby}
        </profil_client>
        <separateur>========================================</separateur>
        <criteres_evaluation titre="CRITÈRES D'ÉVALUATION (5 ITEMS)">
        <instruction>
            Évaluez la conversation selon ces 5 dimensions uniquement avec les niveaux : 
            <niveau>Très bien</niveau> / <niveau>Bien</niveau> / <niveau>Satisfaisant</niveau> / <niveau>À améliorer</niveau>
        </instruction>
        <critere id="1" titre="MAÎTRISE PRODUIT ET TECHNIQUE">
            <description>
        Si présence d'une erreur IL FAUT L'INDIQUER.
        - Exactitude des informations données sur l'offre GSA3.
        - Utilisation correcte des garanties, franchises et montants. Si une erreur est détectée, le niveau doit être 'À améliorer'.
        - Références appropriées aux conditions générales.
        - Informations de référence pour la présentation de l'offre : {doc_description_offre}.
        - Informations de référence pour TMGF : {doc_tmgf}.
            </description>
        </critere>
        <critere id="2" titre="DÉCOUVERTE CLIENT, RELATIONNEL ET CONCLUSION">
            <description>
        - Qualité des questions posées pour comprendre les besoins.
        - Professionnalisme et courtoisie dans les échanges.
        - Identification du profil et de la situation du client.
        - Qualité de l'écoute et de l'empathie.
        - Personnalisation de l'offre selon les besoins.
        - Tentatives de conclusion et gestion des engagements.
        - Respect des procédures Groupama.
            </description>
        </critere>
        <critere id="3" titre="TRAITEMENT DES OBJECTIONS ET ARGUMENTATION">
            <description>
        - Identification et reformulation des objections.
        - Utilisation de la méthode A.C.T.E (Accepter, Creuser, Traiter, Enchaîner).
        - Pertinence des arguments par rapport aux besoins.
        - Utilisation d'exemples concrets et chiffrés.
        - Documentation de traitement des objections : {doc_traitement_objections}.
        - Exemples de remboursements : {doc_exemples_remboursement}.
            </description>
        </critere>
        <critere id="4" titre="CROSS-SELLING ET OPPORTUNITÉS COMMERCIALES">
            <description>
        - Identification des besoins complémentaires du client.
        - Proposition pertinente d'autres produits Groupama selon le profil client.
        - Utilisation des informations du profil client pour détecter les opportunités.
        - Capacité à élargir la relation commerciale au-delà de la santé.
            </description>
        </critere>
        <critere id="5" titre="POSTURE ET RESPECT DE LA CHARTE RELATION CLIENT">
            <description>
        - Évaluer les 4 attitudes : 
            • Faire preuve d'empathie et de compréhension.
            • S'adapter à la situation de chaque client.
            • Faciliter les démarches.
            • Jouer collectif.
        - Documentation de référence pour la posture et la charte relation client : {doc_charte_relation_client}.
            </description>
        </critere>
        </criteres_evaluation>
        <format_reponse>
        <instruction>
            Répondez UNIQUEMENT au format JSON suivant (sans texte additionnel):
        </instruction>
        </format_reponse>
    </prompt>
    """

def get_instructions_template():
    """
    Retourne le template des instructions spécifiques
    
    Returns:
        str: Template d'instructions
    """
    return """
    <instructions>
        <title>INSTRUCTIONS SPÉCIFIQUES</title>
        <evaluation_criteria>
        <criterion number="1" action="Analysez attentivement ce qui a été dit par le commercial."/>
        <criterion number="2" action="Identifiez les points positifs : ce qui correspond aux bonnes pratiques Groupama, en listant tous les points positifs."/>
        <criterion number="3" action="Identifiez les points négatifs : ce qui manque, est incorrect ou non conforme, en listant exhaustivement les erreurs. TOUTES LES ERREURS DOIVENT ÊTRE IDENTIFIÉES ET MENTIONNÉES. Le TMGF est UTILISÉ POUR LES INFORMATIONS CHIFFRÉES."/>
        <criterion number="4" action="Précisez ce qui devrait être dit : en vous basant sur les documents de référence, indiquez les éléments manquants ou à corriger."/>
        <criterion number="5" action="Proposez une réponse optimale : seulement si la performance est 'Satisfaisant' ou 'À améliorer' pour tous les points insuffisants."/>
        </evaluation_criteria>
        <cross_selling>
        <description>Pour le CROSS-SELLING spécifiquement :</description>
        <item>Analysez si le commercial a identifié des opportunités commerciales complémentaires.</item>
        <item>Vérifiez s'il a utilisé les informations du profil client pour proposer d'autres produits Groupama.</item>
        <item>Évaluez la pertinence des propositions par rapport au profil et aux besoins exprimés.</item>
        <item>Identifiez les opportunités manquées basées sur le document profil client spécifique.</item>
        </cross_selling>
        <appreciation_levels>
        <level name="Très bien">Performance très satisfaisante, répond parfaitement à toutes les attentes Groupama.</level>
        <level name="Bien">Performance satisfaisante, répond à la plupart des attentes Groupama.</level>
        <level name="Satisfaisant">Performance acceptable mais avec des améliorations possibles.</level>
        <level name="À améliorer">Performance très insuffisante, nécessite une refonte complète.</level>
        </appreciation_levels>
        <note>Important : Basez-vous strictement sur les documents de référence fournis pour vos jugements et recommandations.</note>
        <summary>
        Il s'agit d'évaluer le travail du conseiller Groupama sur l'offre Groupama Santé 3 (GSA3)
        en fonction de l'historique de la conversation et des documents de référence fournis.
        Il FAUT ETRE LE MOINS VERBEUX POSSIBLE, et aller droit au but.
        </summary>
    </instructions>
    """

def get_documents_reference_template():
    """
    Retourne le template pour les documents de référence
    
    Returns:
        str: Template des documents de référence avec placeholders
    """
    return """
<DocumentsReference>
    <InformationsCommerciales>
    {doc_infos_commerciales}
    </InformationsCommerciales>
    <MethodesCommercialesRecommandees>
    {doc_methodes_commerciales_recommendees}
    </MethodesCommercialesRecommandees>
    <ConditionsGenerales>
    <Vocabulaire>
        {doc_cg_vocabulaire}
    </Vocabulaire>
    <Garanties>
        {doc_cg_garanties}
    </Garanties>
    <GarantiesAssistance>
        {doc_cg_garanties_assistance}
    </GarantiesAssistance>
    <Contrat>
        {doc_cg_contrat}
    </Contrat>
    </ConditionsGenerales>
    <ProfilClientSpecifique>
    {document_profil_specifique}
    </ProfilClientSpecifique>
</DocumentsReference>
"""

def construire_prompt_synthese(documents_reference, historique_complet, document_profil_specifique, profil_manager):
    """
    Construit le prompt d'évaluation en utilisant les templates externalisés
    
    Args:
        documents_reference (dict): Documents de référence chargés
        historique_complet (str): Historique de la conversation
        document_profil_specifique (str): Document spécifique au profil client
        profil_manager: Manager des profils clients
        
    Returns:
        str: Prompt d'évaluation complet
    """
    # Récupérer les informations du profil client
    profil_info = _extraire_infos_profil(profil_manager)
    
    # Récupérer et formater le JSON avec timestamp
    format_json = get_format_json()
    format_json = format_json.replace("TIMESTAMP_PLACEHOLDER", datetime.now().isoformat())
    
    # Construire la partie mission avec les infos du profil
    mission = get_mission_template().format(
        historique_complet=historique_complet,
        profil_nom=profil_info['nom'],
        profil_age=profil_info['age'],
        profil_profession=profil_info['profession'],
        profil_situation=profil_info['situation_maritale'],
        profil_localisation=profil_info['localisation'],
        profil_type=profil_info['type_personne'],
        profil_passerelle=profil_info['profil_passerelle'],
        profil_aidant=profil_info['aidant'],
        profil_contrat_gma=profil_info['a_deja_contrat_gma'],
        profil_enfants=profil_info['nombre_enfants'],
        profil_hobby=profil_info['hobby'],
        doc_description_offre=documents_reference.get('description_offre', 'Non disponible'),
        doc_tmgf=documents_reference.get('tmgf', 'Non disponible'),
        doc_traitement_objections=documents_reference.get('traitement_objections', 'Non disponible'),
        doc_exemples_remboursement=documents_reference.get('exemples_remboursement', 'Non disponible'),
        doc_charte_relation_client=documents_reference.get('charte_relation_client', 'Non disponible')
    )
    
    # Instructions
    instructions = get_instructions_template()
    
    # Documents de référence
    documents_ref = get_documents_reference_template().format(
        doc_infos_commerciales=documents_reference.get('infos_commerciales', 'Non disponible'),
        doc_methodes_commerciales_recommendees=documents_reference.get('methodes_commerciales_recommendees', 'Non disponible'),
        doc_cg_vocabulaire=documents_reference.get('cg_vocabulaire', 'Non disponible'),
        doc_cg_garanties=documents_reference.get('cg_garanties', 'Non disponible'),
        doc_cg_garanties_assistance=documents_reference.get('cg_garanties_assistance', 'Non disponible'),
        doc_cg_contrat=documents_reference.get('cg_contrat', 'Non disponible'),
        document_profil_specifique=document_profil_specifique if document_profil_specifique else 'Profil générique'
    )
    
    # Assembler toutes les parties du prompt
    prompt = mission + format_json + instructions + documents_ref
    return prompt

def _extraire_infos_profil(profil_manager):
    """
    Extrait les informations du profil client depuis le ProfilManager
    
    Args:
        profil_manager: Instance du ProfilManager
        
    Returns:
        dict: Informations du profil formatées
    """
    if not profil_manager:
        return {
            'nom': 'Non spécifié',
            'age': 'Non spécifié',
            'profession': 'Non spécifié',
            'situation_maritale': 'Non spécifié',
            'localisation': 'Non spécifié',
            'type_personne': 'Non spécifié',
            'profil_passerelle': 'Non spécifié',
            'aidant': 'Non spécifié',
            'a_deja_contrat_gma': 'Non spécifié',
            'nombre_enfants': 'Non spécifié',
            'hobby': 'Non spécifié'
        }
    
    person_details = profil_manager.get_person_details() or {}
    
    return {
        'nom': person_details.get('Nom', 'Non spécifié'),
        'age': person_details.get('Age', 'Non spécifié'),
        'profession': person_details.get('Profession', 'Non spécifié'),
        'situation_maritale': person_details.get('situation_maritale', 'Non spécifié'),
        'localisation': person_details.get('Localisation', 'Non spécifié'),
        'type_personne': profil_manager.get_profil_type or 'Non spécifié',
        'profil_passerelle': person_details.get('profil_passerelle', 'Non spécifié'),
        'aidant': person_details.get('aidant', 'Non spécifié'),
        'a_deja_contrat_gma': person_details.get('a_deja_contrat_gma', 'Non spécifié'),
        'nombre_enfants': person_details.get('nombre_enfants', 'Non spécifié'),
        'hobby': person_details.get('hobby', 'Non spécifié')
    }
