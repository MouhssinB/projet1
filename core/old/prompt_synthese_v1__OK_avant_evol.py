#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module pour la gestion du prompt de synthèse des conversations
Contient les templates et fonctions pour construire le prompt d'évaluation
"""

from datetime import datetime

def get_format_json():
    """
    Format JSON de sortie — compatible avec l'existant, enrichi pour:
    - personnalisation par profil
    - ton coaching & non infantilisant
    - relation client calibrée (teasing, refus, cross-sell conditionnel)
    - concision (Top 3)
    """
    return """
    {
      "synthese": {
        "niveau_general": "[Très bien/Bien/Satisfaisant/À améliorer]",
        "commentaire_global": "[1 à 3 phrases, ton coach bienveillant, sans jargon inutile]",
        "timestamp": "TIMESTAMP_PLACEHOLDER",
        "meta": {
          "profil_detecte": "[ex: Demandeur d’emploi, Emprunteur, Senior, Famille...]",
          "adequation_personnalisation": "[Forte/Moyenne/Faible]",
          "teasing_utilise": "[Oui/Non]",
          "refus_respectes": "[Oui/Non]",
          "cross_sell_conditionnel": "[Oui/Non]",
          "registre_langage_client_respecte": "[Oui/Non]"
        }
      },
      "vision_detaillee": {
        "maitrise_produit_technique": {
          "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
          "points_positifs_top3": ["[max 3 bullets courts]"],
          "points_amelioration_top3": ["[max 3 bullets courts]"],
          "ce_qui_devrait_etre_dit": "[1 à 2 phrases, exact, factuel]",
          "exemple_formulation_breve": "[<= 2 phrases, prêt à dire]"
        },
        "decouverte_client_relationnel_conclusion": {
          "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
          "points_positifs_top3": ["[max 3]"],
          "points_amelioration_top3": ["[max 3]",
            "Respect des refus: [OK/À renforcer]",
            "Teasing avant détails: [OK/À renforcer]"
          ],
          "ce_qui_devrait_etre_dit": "[1 à 2 phrases orientées besoin]",
          "exemple_formulation_breve": "[<= 2 phrases, naturel]"
        },
        "traitement_objections_argumentation": {
          "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
          "points_positifs_top3": ["[max 3]"],
          "points_amelioration_top3": ["[max 3]"],
          "ce_qui_devrait_etre_dit": "[méthode ACTE en 1-2 phrases]",
          "exemple_formulation_breve": "[<= 2 phrases, reformulation + solution]"
        },
        "cross_selling_opportunites": {
          "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
          "points_positifs_top3": ["[max 3]"],
          "points_amelioration_top3": ["[max 3]"],
          "regles_conditionnelles": {
            "proposer_si": ["[conditions liées au profil & besoins explicites]"],
            "ne_pas_proposer_si": ["Refus répété 2x", "Hors contexte besoin", "Temps d’appel < X min"]
          },
          "exemple_formulation_breve": "[<= 2 phrases, si pertinent, sinon 'Rien à proposer']"
        },
        "posture_charte_relation_client": {
          "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
          "points_positifs_top3": ["[max 3]"],
          "points_amelioration_top3": ["[max 3, ex: laisser parler, éviter jargon]"],
          "registre_langage_client": "[Adaptation OK / Trop soutenu / Trop familier]",
          "exemple_formulation_breve": "[<= 2 phrases, empathie + clarté]"
        }
      },
      "recommandations": {
        "principales_forces": ["[Top 3 forces, formulées positivement]"],
        "axes_amelioration_prioritaires": ["[Top 3, spécifiques au profil]"],
        "actions_correctives_immediates": ["[3 actions concrètes à tester dès le prochain appel]"],
        "micro_exercices": [
          "[Ex: 'Pitch 30s profil emprunteur']",
          "[Ex: 'Reformulation objection prix en 1 phrase']"
        ],
        "ton_coaching": "Bienveillant, concret, sans infantiliser."
      }
    }
    """

def get_mission_template():
    """
    Mission reformulée:
    - concision & naturel
    - personnalisation par profil
    - teasing d'abord, pas d'infobésité
    - respect strict des refus (stop après 2)
    - cross-sell 100% conditionnel
    - bannir tout ton infantilisant
    """
    return """
    <prompt>
      <mission>
        Vous êtes coach qualité-conseil (assurance santé) pour Groupama.
        À partir de l'historique d'appel, générez une évaluation concise, utile, et PERSONNALISÉE au profil client.
        Votre sortie doit privilégier: naturel, simplicité, respect des refus, et propositions actionnables.
        Interdits: ton moralisateur/infantilisant, listes exhaustives, jargon non expliqué.
      </mission>

      <contexte>
        Historique complet: {historique_complet}
      </contexte>

      <profil_client>
        - Nom: {profil_nom}
        - Âge: {profil_age}
        - Profession: {profil_profession}
        - Situation: {profil_situation}
        - Localisation: {profil_localisation}
        - Type de profil: {profil_type}
        - Profil passerelle: {profil_passerelle}
        - Aidant: {profil_aidant}
        - Contrat GMA existant: {profil_contrat_gma}
        - Enfants: {profil_enfants}
        - Hobby: {profil_hobby}
      </profil_client>

      <garde_fous_relationnels>
        - Teasing avant détails: présenter l’essentiel d’abord, chiffres ensuite sur demande.
        - Respect des refus: après 2 refus clairs, NE PLUS INSISTER (y compris cross-sell).
        - Registre: s’aligner sur le niveau de langage du client (familier poli accepté, jamais vulgaire).
        - Cross-sell: UNIQUEMENT si besoin explicite/profil pertinent et moment opportun (sinon noter "Rien à proposer").
        - Concision: 3 points max par rubrique; 1-2 phrases par exemple de formulation.
        - Ton: coach bienveillant, motivant, tourné solutions (jamais culpabilisant).
      </garde_fous_relationnels>

      <references>
        - Description offre GSA3: {doc_description_offre}
        - TMGF: {doc_tmgf}
        - Traitement objections: {doc_traitement_objections}
        - Exemples remboursement: {doc_exemples_remboursement}
        - Charte relation client: {doc_charte_relation_client}
      </references>

      <format_reponse>
        Répondez UNIQUEMENT au JSON fourni plus bas (aucun texte hors JSON).
      </format_reponse>
    </prompt>
    """


def get_instructions_template():
    """
    Instructions spécifiques orientées: concision, personnalisation, coaching.
    """
    return """
    <instructions>
      <title>INSTRUCTIONS SPÉCIFIQUES</title>

      <evaluation_criteria>
        <criterion number="1" action="Analyser ce qui a été réellement DIT (pas d’invention)."/>
        <criterion number="2" action="Lister au plus 3 points positifs par rubrique (impact client)."/>
        <criterion number="3" action="Lister au plus 3 axes d’amélioration par rubrique (spécifiques au profil)."/>
        <criterion number="4" action="Donner UNE seule formulation brève (<=2 phrases) par rubrique, naturelle et utilisable immédiatement."/>
        <criterion number="5" action="Appliquer la règle des 2 refus: si le client refuse deux fois, arrêter d’insister et le signaler comme 'refus_respectes=Oui'."/>
        <criterion number="6" action="Teasing avant détails: si trop d’infos d’un coup, recommander une version teaser (1-2 phrases)."/>
        <criterion number="7" action="Cross-sell 100% conditionnel: proposer seulement si pertinent pour le profil et le besoin exprimé; sinon indiquer 'Rien à proposer'."/>
        <criterion number="8" action="Bannir tout ton infantilisant: préférer 'Prochaine étape' / 'Astuce' / 'À tester'."/>
      </evaluation_criteria>

      <appreciation_levels>
        <level name="Très bien">Répond précisément aux besoins du profil, respecte refus, concis, sans erreur.</level>
        <level name="Bien">Globalement bon; quelques optimisations mineures.</level>
        <level name="Satisfaisant">OK mais perfectible sur personnalisation/teasing/refus.</level>
        <level name="À améliorer">Erreurs factuelles, verbosité, ou non-respect des refus.</level>
      </appreciation_levels>

      <resume>
        Objectif: évaluer le conseiller sur GSA3 en se basant strictement sur les documents de référence et l’historique,
        en produisant un feedback utile, bref, personnalisé et motivant.
      </resume>
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
