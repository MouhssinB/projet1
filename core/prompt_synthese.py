#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module pour la gestion du prompt de synthèse des conversations
Contient les templates et fonctions pour construire le prompt d'évaluation
Version améliorée avec évaluation plus stricte des erreurs factuelles
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
    - Ne pas pénaliser le conseiller s'il ne donne pas de détails techniques spontanément si le client ne les demande pas et si la situation ne l'exige pas.
    ➝ Ces détails ne doivent apparaître **que si le client les demande** ou si la situation l'exige.  
    - ⚠️ CRITIQUE: Vérifier que les informations fournies sont EXACTES et correspondent STRICTEMENT aux documents de référence.
    - ⚠️ TOUTE erreur factuelle (chiffres, garanties, structure de l'offre) est RÉDHIBITOIRE.
    

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
    - Exactitude ABSOLUE des infos sur l'offre GSA3 et garanties.  
    - Adapter les propositions au profil.  
    - Ne pas détailler inutilement les aspects techniques.  
    - ⚠️ UNE SEULE ERREUR FACTUELLE = niveau "À améliorer" AUTOMATIQUE.

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
        
        <severite_erreurs_factuelles priority="CRITIQUE">
        <description>RÈGLES ABSOLUES pour l'évaluation des erreurs factuelles - PRIORITÉ MAXIMALE</description>
        
        <principe_fondamental>
        Les erreurs factuelles sont RÉDHIBITOIRES. Elles ne peuvent JAMAIS être compensées par des qualités relationnelles.
        Un conseiller peut être très sympathique et à l'écoute, mais s'il donne des informations fausses sur le produit, il met l'entreprise en danger juridique et commercial.
        </principe_fondamental>
        
        <regles_automatiques>
        <regle number="1">TOUTE erreur sur des données structurelles (nombre de blocs, niveaux) = AUTOMATIQUEMENT "À améliorer"</regle>
        <regle number="2">TOUTE mention de garantie inexistante dans l'offre GSA3 = AUTOMATIQUEMENT "À améliorer"</regle>
        <regle number="3">TOUTE information contredite par le TMGF = AUTOMATIQUEMENT "À améliorer"</regle>
        <regle number="4">TOUTE erreur sur un montant, pourcentage ou plafond = AUTOMATIQUEMENT "À améliorer"</regle>
        <regle number="5">Pour obtenir "Bien" ou "Très bien" : ZÉRO erreur factuelle majeure tolérée</regle>
        </regles_automatiques>
        
        <exemples_erreurs_majeures>
            <exemple type="structure">Dire "5 blocs" au lieu de "6 blocs" = ERREUR MAJEURE = "À améliorer"</exemple>
            <exemple type="structure">Dire "5 niveaux" au lieu de "4 niveaux" = ERREUR MAJEURE = "À améliorer"</exemple>
            <exemple type="garantie">Mentionner "chirurgie esthétique" qui n'existe pas dans GSA3 = ERREUR MAJEURE = "À améliorer"</exemple>
            <exemple type="montant">Donner un montant qui contredit le TMGF = ERREUR MAJEURE = "À améliorer"</exemple>
            <exemple type="montant">Dire "niveau 1 : 2 séances à 50€" alors que TMGF indique "niveau 1 : pas de remboursement" = ERREUR MAJEURE = "À améliorer"</exemple>
        </exemples_erreurs_majeures>
        
        <hierarchie_severite>
        <niveau1 severite="critique">Erreurs sur la structure de l'offre (nombre blocs, niveaux)</niveau1>
        <niveau2 severite="critique">Montants contredisant le TMGF</niveau2>
        <niveau3 severite="critique">Garanties inexistantes</niveau3>
        <niveau4 severite="majeure">Conditions d'éligibilité incorrectes</niveau4>
        <niveau5 severite="mineure">Détails techniques manquants (si non demandés par client)</niveau5>
        </hierarchie_severite>
        
        <verification_obligatoire>
        Avant d'attribuer un niveau "Bien" ou "Très bien", vous DEVEZ vérifier :
        1. Chaque nombre mentionné (blocs, niveaux, montants) contre les documents de référence
        2. Chaque garantie mentionnée existe bien dans GSA3
        3. Chaque montant correspond exactement au TMGF
        4. Aucune information contradictoire n'a été donnée
        </verification_obligatoire>
        
        <cas_particuliers>
        <cas>Si le conseiller donne des informations simples mais 100% exactes = peut obtenir "Très bien"</cas>
        <cas>Si le conseiller donne beaucoup d'informations mais avec 1 erreur factuelle = maximum "Satisfaisant", plus probablement "À améliorer"</cas>
        <cas>Si le conseiller donne plusieurs erreurs factuelles = OBLIGATOIREMENT "À améliorer"</cas>
        </cas_particuliers>
        
        </severite_erreurs_factuelles>
        
        <maitrise_produit_technique>
        <description>Pour la MAÎTRISE PRODUIT & TECHNIQUE :</description>
        <item priority="CRITIQUE">L'EXACTITUDE prime sur la quantité d'informations.</item>
        <item>Vérifiez l'exactitude de CHAQUE information donnée sur l'offre Groupama Santé 3 (GSA3).</item>
        <item>Ne pénalisez pas le conseiller s'il ne fournit pas spontanément les détails techniques SI ET SEULEMENT SI les informations qu'il donne sont EXACTES.</item>
        <item>Il est préférable de rester simple et clair, MAIS l'exactitude est NON NÉGOCIABLE.</item>
        <item>Les détails techniques doivent être présentés uniquement si le client les demande explicitement ou si la situation l'exige.</item>
        <item>La règle des 2 niveaux d'écart n'a pas besoin d'être mentionnée si le client ne pose pas de question à ce sujet.</item>
        <item priority="CRITIQUE">TOUT chiffre donné doit correspondre EXACTEMENT au TMGF. Aucune approximation tolérée.</item>
        <item priority="CRITIQUE">TOUTE garantie mentionnée doit exister dans la documentation GSA3.</item>
        </maitrise_produit_technique>
        
        <cross_selling>
        <description>Pour le CROSS-SELLING spécifiquement :</description>
        <item>Analysez si le commercial a identifié des opportunités commerciales complémentaires.</item>
        <item>Vérifiez s'il a utilisé les informations du profil client pour proposer d'autres produits Groupama.</item>
        <item>Évaluez la pertinence des propositions par rapport au profil et aux besoins exprimés.</item>
        <item>Identifiez les opportunités manquées basées sur le document profil client spécifique.</item>
        </cross_selling>
        
        <appreciation_levels>
        <level name="Très bien">Performance très satisfaisante, répond parfaitement à toutes les attentes Groupama. ZÉRO erreur factuelle. Informations simples ET exactes.</level>
        <level name="Bien">Performance satisfaisante, répond à la plupart des attentes Groupama. ZÉRO erreur factuelle majeure. Quelques imprécisions mineures possibles.</level>
        <level name="Satisfaisant">Performance acceptable mais avec des améliorations possibles. Peut contenir 1 erreur factuelle mineure OU plusieurs manques.</level>
        <level name="À améliorer">Performance insuffisante. Contient au moins 1 erreur factuelle majeure OU plusieurs erreurs mineures OU des informations contradictoires.</level>
        </appreciation_levels>
        
        <note priority="CRITIQUE">Important : Basez-vous strictement sur les documents de référence fournis pour vos jugements et recommandations. Le TMGF fait autorité pour TOUS les chiffres.</note>
        
        <summary>
        Il s'agit d'évaluer le travail du conseiller Groupama sur l'offre Groupama Santé 3 (GSA3)
        en fonction de l'historique de la conversation et des documents de référence fournis.
        Il FAUT ETRE LE MOINS VERBEUX POSSIBLE, et aller droit au but.
        L'EXACTITUDE DES INFORMATIONS est le critère PRIORITAIRE sur la Maîtrise Produit & Technique.
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
        AUCUNE APPROXIMATION N'EST TOLÉRÉE.
        </description>
        <contenu>
        {doc_description_offre}
        </contenu>
    </InfosCommerciales>
    
    <Tmgf priority="CRITIQUE">
        <description>
        Tableau des Montants de Garanties et Franchises - LA SOURCE DE VÉRITÉ ABSOLUE pour tous les chiffres.
        TOUT montant, pourcentage, plafond mentionné par le conseiller DOIT être vérifié contre ce tableau.
        En cas de différence même minime, c'est une ERREUR MAJEURE à signaler obligatoirement.
        Ce document fait AUTORITÉ. Aucun autre chiffre ne peut le contredire.
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


# ========================================
# NOUVELLE APPROCHE : ÉVALUATION PAR DIMENSION
# ========================================

def get_format_json_dimension():
    """
    Retourne le format JSON attendu pour l'évaluation d'UNE SEULE dimension

    Returns:
        str: Template JSON pour une dimension unique
    """
    return """
    {
        "dimension": "[nom de la dimension]",
        "niveau": "[Très bien/Bien/Satisfaisant/À améliorer]",
        "points_positifs": "[resumé de ce qui a été bien dit par le commercial dans ce domaine]",
        "points_negatifs": "[liste exhaustive des erreurs identifiées]",
        "ce_qui_devrait_etre_dit": "[resumé de ce que le conseiller aurait dû dire : corrige les erreurs]",
        "reponse_suggeree": "[si le niveau est 'À améliorer': suggérer une réponse commerciale optimale concise, sinon renseigner 'Rien à améliorer']",
        "timestamp": "TIMESTAMP_PLACEHOLDER"
    }
    """


def get_instructions_dimension(dimension_name):
    """
    Retourne les instructions spécifiques pour une dimension donnée

    Args:
        dimension_name (str): Nom de la dimension à évaluer

    Returns:
        str: Instructions spécifiques pour cette dimension
    """
    instructions_specifiques = {
        "maitrise_produit_technique": """
        <instructions_dimension>
            <dimension>Maîtrise produit & technique</dimension>
            <description>Évaluer la capacité du conseiller à présenter correctement l'offre Groupama Santé 3 (GSA3)</description>

            <criteres_evaluation>
                <critere priority="CRITIQUE">L'EXACTITUDE prime sur la quantité d'informations.</critere>
                <critere priority="CRITIQUE">TOUTE erreur factuelle (chiffres, garanties, structure) = AUTOMATIQUEMENT "À améliorer"</critere>
                <critere>Vérifier l'exactitude de CHAQUE information donnée sur GSA3</critere>
                <critere>Ne pas pénaliser si les détails techniques ne sont pas donnés spontanément SI les infos données sont EXACTES</critere>
                <critere>Il est préférable de rester simple et clair, MAIS l'exactitude est NON NÉGOCIABLE</critere>
                <critere priority="CRITIQUE">TOUT chiffre donné doit correspondre EXACTEMENT au TMGF</critere>
                <critere priority="CRITIQUE">TOUTE garantie mentionnée doit exister dans la documentation GSA3</critere>
            </criteres_evaluation>

            <erreurs_automatiques_ameliorer>
                <erreur>Erreur sur le nombre de blocs (doit être 6)</erreur>
                <erreur>Erreur sur le nombre de niveaux (doit être 4)</erreur>
                <erreur>Montant ne correspondant pas au TMGF</erreur>
                <erreur>Mention d'une garantie inexistante dans GSA3</erreur>
                <erreur>Information contradictoire avec les documents de référence</erreur>
            </erreurs_automatiques_ameliorer>

            <niveaux>
                <niveau name="Très bien">Informations 100% exactes, simples et claires. ZÉRO erreur factuelle.</niveau>
                <niveau name="Bien">Informations exactes avec quelques imprécisions mineures. ZÉRO erreur factuelle majeure.</niveau>
                <niveau name="Satisfaisant">Informations globalement correctes avec 1 erreur mineure OU plusieurs manques.</niveau>
                <niveau name="À améliorer">Au moins 1 erreur factuelle majeure OU plusieurs erreurs mineures.</niveau>
            </niveaux>
        </instructions_dimension>
        """,

        "decouverte_client_relationnel_conclusion": """
        <instructions_dimension>
            <dimension>Découverte client, relationnel & conclusion</dimension>
            <description>Évaluer la qualité de la découverte client, la relation établie et la conclusion de l'entretien</description>

            <criteres_evaluation>
                <critere>Pertinence et qualité des questions posées pour comprendre les besoins</critere>
                <critere>Courtoisie, empathie et professionnalisme dans les échanges</critere>
                <critere>Personnalisation de l'approche selon le profil client</critere>
                <critere>Qualité de l'écoute active et reformulation</critere>
                <critere>Adaptation au contexte et à la situation du client</critere>
                <critere>Qualité de la conclusion (synthèse, prochaines étapes)</critere>
            </criteres_evaluation>

            <niveaux>
                <niveau name="Très bien">Découverte approfondie, excellente relation, conclusion claire et engageante</niveau>
                <niveau name="Bien">Bonne découverte, relation professionnelle, conclusion satisfaisante</niveau>
                <niveau name="Satisfaisant">Découverte basique, relation correcte, conclusion présente</niveau>
                <niveau name="À améliorer">Découverte insuffisante, relation impersonnelle, conclusion faible ou absente</niveau>
            </niveaux>
        </instructions_dimension>
        """,

        "traitement_objections_argumentation": """
        <instructions_dimension>
            <dimension>Traitement des objections & argumentation</dimension>
            <description>Évaluer la capacité à détecter, traiter les objections et à argumenter efficacement</description>

            <criteres_evaluation>
                <critere>Détection et identification des objections explicites et implicites</critere>
                <critere>Utilisation de la méthode A.C.T.E (Accepter, Creuser, Traiter, Évaluer)</critere>
                <critere>Reformulation pour valider la compréhension</critere>
                <critere>Arguments adaptés, concrets et basés sur les documents de référence</critere>
                <critere>Réponses personnalisées selon le profil et les besoins du client</critere>
                <critere>Vérification de la satisfaction après traitement de l'objection</critere>
            </criteres_evaluation>

            <niveaux>
                <niveau name="Très bien">Objections bien détectées, méthode A.C.T.E appliquée, arguments pertinents et personnalisés</niveau>
                <niveau name="Bien">Objections traitées avec arguments adaptés, méthode partiellement appliquée</niveau>
                <niveau name="Satisfaisant">Objections identifiées mais traitement basique</niveau>
                <niveau name="À améliorer">Objections mal traitées, ignorées ou arguments inadaptés</niveau>
            </niveaux>
        </instructions_dimension>
        """,

        "cross_selling_opportunites": """
        <instructions_dimension>
            <dimension>Cross-selling & opportunités commerciales</dimension>
            <description>Évaluer la capacité à identifier et proposer des produits complémentaires adaptés au profil client</description>

            <criteres_evaluation>
                <critere>Identification des besoins complémentaires selon le profil client</critere>
                <critere>Utilisation des informations du profil pour proposer des produits Groupama pertinents</critere>
                <critere>Adaptation des propositions au profil (âge, situation, profession, etc.)</critere>
                <critere>Respect de la pertinence (ne pas proposer de garanties inadaptées)</critere>
                <critere>Présentation naturelle des opportunités sans forcer</critere>
                <critere>Lien avec les besoins exprimés ou le document profil spécifique</critere>
            </criteres_evaluation>

            <exemples_opportunites_manquees>
                <exemple>Client avec enfants : ne pas mentionner la garantie assistance scolaire</exemple>
                <exemple>Client senior : ne pas évoquer les services d'assistance adaptés</exemple>
                <exemple>Client aidant : ne pas proposer les garanties spécifiques aidants</exemple>
            </exemples_opportunites_manquees>

            <interdictions>
                <interdit>GAV pour les clients de plus de 65 ans</interdit>
                <interdit>Garantie emprunteur pour demandeurs d'emploi</interdit>
                <interdit>Produits inadaptés au profil ou à la situation</interdit>
            </interdictions>

            <niveaux>
                <niveau name="Très bien">Opportunités identifiées et proposées de manière pertinente et personnalisée</niveau>
                <niveau name="Bien">Quelques opportunités identifiées avec propositions adaptées</niveau>
                <niveau name="Satisfaisant">Opportunités basiques identifiées</niveau>
                <niveau name="À améliorer">Aucune opportunité identifiée OU propositions inadaptées au profil</niveau>
            </niveaux>
        </instructions_dimension>
        """,

        "posture_charte_relation_client": """
        <instructions_dimension>
            <dimension>Posture & respect de la charte relation client</dimension>
            <description>Évaluer le respect des valeurs Groupama en matière de relation client</description>

            <criteres_evaluation>
                <critere>Empathie : écoute attentive, compréhension des émotions et besoins</critere>
                <critere>Adaptation : personnalisation selon le profil et la situation</critere>
                <critere>Facilitation : simplification, clarté, accessibilité des informations</critere>
                <critere>Esprit collectif : références aux valeurs mutualistes Groupama</critere>
                <critere>Respect du client : politesse, professionnalisme, considération</critere>
                <critere>Ton et langage appropriés (ni moralisateur, ni infantilisant)</critere>
            </criteres_evaluation>

            <interdictions>
                <interdit>Ton moralisateur ou infantilisant</interdit>
                <interdit>Manque de respect ou d'empathie</interdit>
                <interdit>Insistance excessive malgré un refus clair</interdit>
                <interdit>Langage inapproprié ou trop technique sans explication</interdit>
            </interdictions>

            <niveaux>
                <niveau name="Très bien">Parfaite incarnation des valeurs Groupama, posture exemplaire</niveau>
                <niveau name="Bien">Bonne application de la charte relation client</niveau>
                <niveau name="Satisfaisant">Respect basique de la charte</niveau>
                <niveau name="À améliorer">Manquements à la charte ou posture inappropriée</niveau>
            </niveaux>
        </instructions_dimension>
        """
    }

    return instructions_specifiques.get(dimension_name, "")


def construire_prompt_dimension(dimension_name, documents_reference, historique_complet,
                                document_profil_specifique, profil_manager):
    """
    Construit le prompt d'évaluation pour UNE dimension spécifique

    Args:
        dimension_name (str): Nom de la dimension à évaluer
        documents_reference (dict): Documents de référence chargés
        historique_complet (str): Historique de la conversation
        document_profil_specifique (str): Document spécifique au profil client
        profil_manager: Manager des profils clients

    Returns:
        str: Prompt d'évaluation pour cette dimension
    """
    # Récupérer les informations du profil client
    profil_info = _extraire_infos_profil(profil_manager)

    # Récupérer et formater le JSON avec timestamp
    format_json = get_format_json_dimension()
    format_json = format_json.replace("TIMESTAMP_PLACEHOLDER", datetime.now().isoformat())
    format_json = format_json.replace('"[nom de la dimension]"', f'"{dimension_name}"')

    # Construire la partie mission simplifiée pour une dimension
    mission = f"""
# 🎯 Mission
Vous êtes **coach qualité-conseil** (assurance santé Groupama).
Vous devez évaluer le conseiller Groupama UNIQUEMENT sur la dimension : **{dimension_name}**

À partir de l'historique d'appel, générez une **analyse concise et personnalisée** pour cette dimension uniquement.

### ⚖️ Principes clés
- Adapter l'évaluation au **profil du client** (âge, profession, sexe, situation personnelle).
- ❌ Ne jamais proposer de garanties inadaptées
- ✅ Privilégier simplicité, naturel, respect des refus, et conseils actionnables.
- ❌ Interdit : ton moralisateur ou infantilisant.
- ⚠️ CRITIQUE: Vérifier que les informations fournies sont EXACTES et correspondent aux documents de référence.

---

# 👤 Profil client
- Nom: {profil_info['nom']}
- Âge: {profil_info['age']}
- Profession: {profil_info['profession']}
- Situation: {profil_info['situation_maritale']}
- Localisation: {profil_info['localisation']}
- Type de profil: {profil_info['type_personne']}
- Profil passerelle: {profil_info['profil_passerelle']}
- Aidant: {profil_info['aidant']}
- Contrat GMA existant: {profil_info['a_deja_contrat_gma']}
- Nombre d'enfants: {profil_info['nombre_enfants']}
- Hobby: {profil_info['hobby']}

---

# 📞 Contexte
Historique de la conversation :
{historique_complet}

---

# 📝 Dimension à évaluer : {dimension_name}

"""

    # Instructions spécifiques à la dimension
    instructions = get_instructions_dimension(dimension_name)

    # Documents de référence (sélectionner ceux pertinents pour la dimension)
    documents_ref = _get_documents_reference_pour_dimension(
        dimension_name, documents_reference, document_profil_specifique
    )

    # Format JSON attendu
    format_section = f"""
---

# 📤 Format de réponse attendu
Réponds **uniquement** au format JSON suivant (aucun texte additionnel) :
{format_json}

⚠️ **CONSIGNES CRITIQUES DE FORMAT** ⚠️
Vous DEVEZ répondre EXCLUSIVEMENT avec un objet JSON valide.
- ❌ AUCUN texte explicatif avant le JSON
- ❌ AUCUN texte explicatif après le JSON
- ❌ AUCUNE balise markdown (pas de ```json ni ```)
- ✅ Commencez DIRECTEMENT par le caractère {{
- ✅ Terminez DIRECTEMENT par le caractère }}
- ✅ Toutes les chaînes doivent être entre guillemets doubles "
- ✅ Respectez EXACTEMENT la structure JSON fournie
"""

    # Assembler toutes les parties du prompt
    prompt = mission + instructions + documents_ref + format_section

    return prompt


def _get_documents_reference_pour_dimension(dimension_name, documents_reference, document_profil_specifique):
    """
    Sélectionne les documents de référence pertinents pour une dimension donnée

    Args:
        dimension_name (str): Nom de la dimension
        documents_reference (dict): Tous les documents de référence
        document_profil_specifique (str): Document profil spécifique

    Returns:
        str: Documents de référence formatés pour cette dimension
    """
    docs = "\n<DocumentsReference>\n"

    # Documents communs à toutes les dimensions
    docs += f"""
    <InfosCommerciales priority="CRITIQUE">
        <description>Document officiel décrivant l'offre GSA3</description>
        <contenu>
        {documents_reference.get('description_offre', 'Non disponible')}
        </contenu>
    </InfosCommerciales>

    <Tmgf priority="CRITIQUE">
        <description>Tableau des Montants - SOURCE DE VÉRITÉ pour tous les chiffres</description>
        <contenu>
        {documents_reference.get('tmgf', 'Non disponible')}
        </contenu>
    </Tmgf>
"""

    # Documents spécifiques selon la dimension
    if dimension_name == "maitrise_produit_technique":
        docs += f"""
    <ConditionsGenerales>
        <Vocabulaire>{documents_reference.get('cg_vocabulaire', 'Non disponible')}</Vocabulaire>
        <Garanties>{documents_reference.get('cg_garanties', 'Non disponible')}</Garanties>
        <GarantiesAssistance>{documents_reference.get('cg_garanties_assistance', 'Non disponible')}</GarantiesAssistance>
        <Contrat>{documents_reference.get('cg_contrat', 'Non disponible')}</Contrat>
    </ConditionsGenerales>

    <ExemplesRemboursement>
        {documents_reference.get('exemples_remboursement', 'Non disponible')}
    </ExemplesRemboursement>
"""

    elif dimension_name == "decouverte_client_relationnel_conclusion":
        docs += f"""
    <MethodesCommercialesRecommandees>
        {documents_reference.get('methodes_commerciales_recommendees', 'Non disponible')}
    </MethodesCommercialesRecommandees>

    <CharteRelationClient>
        {documents_reference.get('charte_relation_client', 'Non disponible')}
    </CharteRelationClient>

    <ProfilClientSpecifique>
        {document_profil_specifique if document_profil_specifique else 'Profil générique'}
    </ProfilClientSpecifique>
"""

    elif dimension_name == "traitement_objections_argumentation":
        docs += f"""
    <TraitementObjections>
        {documents_reference.get('traitement_objections', 'Non disponible')}
    </TraitementObjections>

    <MethodesCommercialesRecommandees>
        {documents_reference.get('methodes_commerciales_recommendees', 'Non disponible')}
    </MethodesCommercialesRecommandees>
"""

    elif dimension_name == "cross_selling_opportunites":
        docs += f"""
    <ProfilClientSpecifique>
        {document_profil_specifique if document_profil_specifique else 'Profil générique'}
    </ProfilClientSpecifique>

    <ConditionsGenerales>
        <Garanties>{documents_reference.get('cg_garanties', 'Non disponible')}</Garanties>
        <GarantiesAssistance>{documents_reference.get('cg_garanties_assistance', 'Non disponible')}</GarantiesAssistance>
    </ConditionsGenerales>
"""

    elif dimension_name == "posture_charte_relation_client":
        docs += f"""
    <CharteRelationClient>
        {documents_reference.get('charte_relation_client', 'Non disponible')}
    </CharteRelationClient>

    <MethodesCommercialesRecommandees>
        {documents_reference.get('methodes_commerciales_recommendees', 'Non disponible')}
    </MethodesCommercialesRecommandees>
"""

    docs += "\n</DocumentsReference>\n"

    return docs

