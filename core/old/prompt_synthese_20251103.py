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
            "points_positifs": "[resumé de ce qui a été bien dit par le commercial dans ce domaine]",
            "points_negatifs": "[liste exhaustive des erreurs identifiées]",
            "ce_qui_devrait_etre_dit": "[resumé de ce que le conseiller aurait dû dire : corrige les erreurs]",
            "reponse_suggeree": "[si le niveau est 'À améliorer': suggérer une réponse commerciale optimale concise, sinon renseigner 'Rien à améliorer']"
        },
        "decouverte_client_relationnel_conclusion": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[resumé de ce qui a été bien dit par le commercial dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[resumé de ce que le conseiller aurait dû dire]",
            "reponse_suggeree": "[si le niveau est 'À améliorer': suggérer une réponse commerciale optimale concise, sinon renseigner 'Rien à améliorer']"
        },
        "traitement_objections_argumentation": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[resumé de ce qui a été bien dit par le commercial dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[resumé de ce que le conseiller aurait dû dire]",
            "reponse_suggeree": "[si le niveau est 'À améliorer': suggérer une réponse commerciale optimale concise, sinon renseigner 'Rien à améliorer']"
        },
        "cross_selling_opportunites": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[resumé de ce qui a été bien dit par le commercial dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[resumé de ce que le conseiller aurait dû dire selon le profil client]",
            "reponse_suggeree": "[si le niveau est 'À améliorer': suggérer une réponse commerciale optimale concise, sinon renseigner 'Rien à améliorer']"
        },
        "posture_charte_relation_client": {
            "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
            "points_positifs": "[resumé de ce qui a été bien dit par le commercial dans ce domaine]",
            "points_negatifs": "[Ce qui a été mal fait ou manqué]",
            "ce_qui_devrait_etre_dit": "[resumé de ce que le conseiller aurait dû dire selon la charte relation client]",
            "reponse_suggeree": "[si le niveau est 'À améliorer': suggérer une réponse commerciale optimale concise, sinon renseigner 'Rien à améliorer']"
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
    # 🎯 Mission
    Vous êtes **coach qualité-conseil** (assurance santé Groupama).  
    À partir de l'historique d'appel, générez une **analyse concise, utile et personnalisée** au **profil client**, en vous basant sur la documentation de référence.

    ### ⚖️ Principes clés
    - Adapter l'évaluation et les recommandations au **profil du client** (âge, profession, sexe, situation personnelle).
    - ❌ Ne jamais proposer de garanties inadaptées  
    (ex. GAV > 65 ans, garantie emprunteur à un demandeur d'emploi).
    - ✅ Privilégier simplicité, naturel, respect des refus, et conseils actionnables.
    - ❌ Interdit : ton moralisateur ou infantilisant.
    - Ne pas pénaliser le conseiller s'il ne donne pas de détails techniques spontanément. si le conseiller n'aborde pas la regle d'écart de 2 niveaux, ne pas le pénaliser.
    ➝ Ces détails ne doivent apparaître **que si le client les demande** ou si la situation l'exige.  
    - Vérifier que les informations fournies sont exactes.
    

    ---

    # 👤 Profil client
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

    ---

    # 📞 Contexte
    Historique de la conversation :  
    {historique_complet}

    ---

    # 📝 Critères d'évaluation
    Évaluer selon ces **5 dimensions**, avec les niveaux :  
    **"Très bien" / "Bien" / "Satisfaisant" / "À améliorer"**

    1. **Maîtrise produit & technique**  
    - Exactitude des infos sur l'offre GSA3 et garanties.  
    - Adapter les propositions au profil.  
    - Ne pas détailler inutilement les aspects techniques.  

    2. **Découverte client, relationnel & conclusion**  
    - Pertinence des questions.  
    - Courtoisie, empathie, professionnalisme.  
    - Personnalisation et qualité d'écoute.  

    3. **Traitement des objections & argumentation**  
    - Détection et reformulation.  
    - Utilisation de la méthode A.C.T.E.  
    - Arguments adaptés et concrets.  

    4. **Cross-selling & opportunités**  
    - Détecter besoins complémentaires.  
    - Proposer produits pertinents Groupama.  

    5. **Posture & respect de la charte relation client**  
    - Empathie, adaptation, facilitation, esprit collectif.  

    ---

    # 📤 Format de réponse attendu
    Réponds **uniquement** au format JSON suivant (aucun texte additionnel) :
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
        <maitrise_produit_technique>
        <description>Pour la MAÎTRISE PRODUIT & TECHNIQUE :</description>
        <item>Vérifiez l'exactitude des informations données sur l'offre Groupama Santé 3 (GSA3).</item>
        <item>Lors de l'évaluation d'une conversation, ne pénalisez pas le conseiller s'il ne fournit pas spontanément les détails techniques de l'offre.</item>
        <item>Il est préférable de rester simple et clair afin de ne pas noyer le client dans des informations complexes.</item>
        <item>Les détails techniques doivent être présentés uniquement si le client les demande explicitement ou si la situation l'exige.</item>
        <item>inutile de preciser la regle des 2 niveaux d'ecart si le client ne pose pas de question a ce sujet.</item>
        <item>Par contre, il faut vérifier à donner les informations correctes.</item>
        </maitrise_produit_technique>
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
    <InfosCommerciales priority="CRITIQUE">
        <description>
        Document officiel décrivant l'offre Groupama Santé 3 (GSA3).
        Toute information produit donnée par le conseiller DOIT correspondre à ce document.
        Vérifier : descriptions de l'offre , des garanties, formules, services inclus.

        </description>
        <contenu>
        {doc_description_offre}
        </contenu>
    </InfosCommerciales>
    <Tmgf priority="CRITIQUE">
        <description>
        Tableau des Montants de Garanties et Franchises - LA SOURCE DE VÉRITÉ pour tous les chiffres.
        TOUT montant, pourcentage, plafond mentionné par le conseiller DOIT être vérifié contre ce tableau.
        En cas de différence, c'est une ERREUR à signaler obligatoirement.
        </description>
        <contenu>
        {doc_tmgf}
        </contenu>
    </Tmgf>
    

    <MethodesCommercialesRecommandees>
        <DescriptionOffre_CharteClient_TraimemntObjections>
    {doc_methodes_commerciales_recommendees}
        </DescriptionOffre_CharteClient_TraimemntObjections>
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
        profil_hobby=profil_info['hobby']

    )
    
    # Instructions
    instructions = get_instructions_template()
    
    # Documents de référence
    documents_ref = get_documents_reference_template().format(
        doc_description_offre=documents_reference.get('description_offre', 'Non disponible'),
        doc_infos_commerciales=documents_reference.get('infos_commerciales', 'Non disponible'),
        doc_methodes_commerciales_recommendees=documents_reference.get('methodes_commerciales_recommendees', 'Non disponible'),
        doc_cg_vocabulaire=documents_reference.get('cg_vocabulaire', 'Non disponible'),
        doc_cg_garanties=documents_reference.get('cg_garanties', 'Non disponible'),
        doc_cg_garanties_assistance=documents_reference.get('cg_garanties_assistance', 'Non disponible'),
        doc_cg_contrat=documents_reference.get('cg_contrat', 'Non disponible'),
        doc_tmgf=documents_reference.get('tmgf', 'Non disponible'),
        document_profil_specifique=document_profil_specifique if document_profil_specifique else 'Profil générique',
        doc_traitement_objections=documents_reference.get('traitement_objections', 'Non disponible'),
        doc_exemples_remboursement=documents_reference.get('exemples_remboursement', 'Non disponible'),
        doc_charte_relation_client=documents_reference.get('charte_relation_client', 'Non disponible')
    )
    
    # Assembler toutes les parties du prompt
    prompt = mission + format_json + instructions + documents_ref

    print("Debut du prompt de synthese")
    prompt_stats = {
        'nombre_caracteres': len(prompt),
        'nombre_mots': len(prompt.split()),
        'nombre_lignes': len(prompt.splitlines()),
        'nombre_caracteres_sans_espaces': len(prompt.replace(' ', '').replace('\n', '').replace('\t', ''))
        }
    print(f"Statistiques du prompt:")
    print(f"  - Nombre de caractères: {prompt_stats['nombre_caracteres']:,}")
    print(f"  - Nombre de mots: {prompt_stats['nombre_mots']:,}")
    print(f"  - Nombre de lignes: {prompt_stats['nombre_lignes']:,}")
    print(f"  - Nombre de caractères (sans espaces): {prompt_stats['nombre_caracteres_sans_espaces']:,}")
    print("===================================")
    try:
        path = '.prompt.txt'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"Prompt écrit dans {path}")
    except Exception as e:
        print(f"Erreur lors de l'écriture du prompt: {e}")
    print("===================================")
    print("Fin du prompt de synthese")

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
