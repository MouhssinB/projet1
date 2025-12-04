"""
Gestionnaire des habilitations - Gestion des groupes autorisés à accéder à l'application
"""

import json
import logging
from typing import List, Dict, Tuple
from .storage_manager import get_storage_manager

logger = logging.getLogger(__name__)

# Liste complète des groupes d'habilitation disponibles
GROUPES_DISPONIBLES = [
    {"entite": "PVL", "groupe": "GR_SIMSAN_UTILISATEURS_PVL"},
    {"entite": "LBR", "groupe": "GR_SIMSAN_UTILISATEURS_LBR"},
    {"entite": "GROM", "groupe": "GR_SIMSAN_UTILISATEURS_GROM"},
    {"entite": "GPJ", "groupe": "GR_SIMSAN_UTILISATEURS_GPJ"},
    {"entite": "GPAT", "groupe": "GR_SIMSAN_UTILISATEURS_GPAT"},
    {"entite": "GOC", "groupe": "GR_SIMSAN_UTILISATEURS_GOC"},
    {"entite": "GNC", "groupe": "GR_SIMSAN_UTILISATEURS_GNC"},
    {"entite": "GGBH", "groupe": "GR_SIMSAN_UTILISATEURS_GGBH"},
    {"entite": "GCM", "groupe": "GR_SIMSAN_UTILISATEURS_GCM"},
    {"entite": "GASM", "groupe": "GR_SIMSAN_UTILISATEURS_GASM"},
    {"entite": "GSP", "groupe": "GR_SIMSAN_UTILISATEURS_GSP"},
    {"entite": "GPF", "groupe": "GR_SIMSAN_UTILISATEURS_GPF"},
    {"entite": "GOI", "groupe": "GR_SIMSAN_UTILISATEURS_GOI"},
    {"entite": "GNE", "groupe": "GR_SIMSAN_UTILISATEURS_GNE"},
    {"entite": "GMED", "groupe": "GR_SIMSAN_UTILISATEURS_GMED"},
    {"entite": "GGBS", "groupe": "GR_SIMSAN_UTILISATEURS_GGBS"},
    {"entite": "GES", "groupe": "GR_SIMSAN_UTILISATEURS_GES"},
    {"entite": "GCA", "groupe": "GR_SIMSAN_UTILISATEURS_GCA"},
    {"entite": "GANAS", "groupe": "GR_SIMSAN_UTILISATEURS_GANAS"},
    {"entite": "GAC", "groupe": "GR_SIMSAN_UTILISATEURS_GAC"},
    {"entite": "MUT", "groupe": "GR_SIMSAN_UTILISATEURS_MUT"},
    {"entite": "GRA", "groupe": "GR_SIMSAN_UTILISATEURS_GRA"},
    {"entite": "GPREV", "groupe": "GR_SIMSAN_UTILISATEURS_GPREV"},
    {"entite": "GGE", "groupe": "GR_SIMSAN_UTILISATEURS_GGE"},
    {"entite": "GAA", "groupe": "GR_SIMSAN_UTILISATEURS_GAA"},
    {"entite": "ALL", "groupe": "GR_SIMSAN_ADMIN"},
    {
        "entite": "SPECIAL",
        "groupe": "GR_SIMSAN_ALL",
    },  # ⭐ Groupe spécial: accès universel
    {"entite": "TEST", "groupe": "GR_"},
]


class HabilitationsManager:
    """Gestionnaire des habilitations utilisateur"""

    def __init__(self):
        self.storage = get_storage_manager()
        self.config_file = (
            self.storage.base_path / "admin" / "habilitations_config.json"
        )
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Crée le fichier de configuration s'il n'existe pas"""
        if not self.config_file.exists():
            # Configuration par défaut : tous les groupes sont habilités
            default_config = {
                "groupes_habilites": [g["groupe"] for g in GROUPES_DISPONIBLES],
                "derniere_modification": None,
                "modifie_par": "system",
            }
            self._save_config(default_config)
            logger.info(
                "✓ Fichier de configuration habilitations créé avec valeurs par défaut"
            )

    def _save_config(self, config: dict) -> bool:
        """Sauvegarde la configuration dans le fichier"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("✓ Configuration habilitations sauvegardée")
            return True
        except Exception as e:
            logger.error(f"✗ Erreur sauvegarde configuration: {e}")
            return False

    def _load_config(self) -> dict:
        """Charge la configuration depuis le fichier"""
        try:
            if not self.config_file.exists():
                self._ensure_config_exists()

            with self.config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)

            return config
        except Exception as e:
            logger.error(f"✗ Erreur chargement configuration: {e}")
            # Retourner une configuration par défaut en cas d'erreur
            return {
                "groupes_habilites": [g["groupe"] for g in GROUPES_DISPONIBLES],
                "derniere_modification": None,
                "modifie_par": "system",
            }

    def get_groupes_habilites(self) -> List[str]:
        """
        Récupère la liste des groupes habilités
        🔒 FORCE l'inclusion de GR_SIMSAN_ADMIN dans tous les cas

        Returns:
            List[str]: Liste des noms de groupes habilités
        """
        config = self._load_config()
        groupes = config.get("groupes_habilites", [])

        # 🔒 FORCER l'inclusion de GR_SIMSAN_ADMIN
        if "GR_SIMSAN_ADMIN" not in groupes:
            groupes.append("GR_SIMSAN_ADMIN")
            logger.info("🔒 Groupe GR_SIMSAN_ADMIN forcé dans les habilitations")

        return groupes

    def get_all_groupes(self) -> List[Dict[str, str]]:
        """
        Récupère la liste complète des groupes disponibles

        Returns:
            List[Dict]: Liste des groupes avec entité et nom
        """
        return GROUPES_DISPONIBLES

    def get_configuration_complete(self) -> Dict:
        """
        Récupère la configuration complète avec statut de chaque groupe

        Returns:
            Dict: Configuration avec liste des groupes et leur statut
        """
        config = self._load_config()
        groupes_habilites = set(config.get("groupes_habilites", []))

        groupes_avec_statut = []
        for groupe in GROUPES_DISPONIBLES:
            groupes_avec_statut.append(
                {
                    "entite": groupe["entite"],
                    "groupe": groupe["groupe"],
                    "habilite": groupe["groupe"] in groupes_habilites,
                }
            )

        return {
            "groupes": groupes_avec_statut,
            "derniere_modification": config.get("derniere_modification"),
            "modifie_par": config.get("modifie_par"),
        }

    def update_habilitations(
        self, groupes_habilites: List[str], modifie_par: str
    ) -> Tuple[bool, str]:
        """
        Met à jour la liste des groupes habilités

        Args:
            groupes_habilites: Liste des noms de groupes à habiliter
            modifie_par: Identifiant de l'utilisateur effectuant la modification

        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            # Validation : vérifier que tous les groupes commencent par GR ou GF
            groupes_invalides = [
                g
                for g in groupes_habilites
                if not g.startswith("GR") and not g.startswith("GF")
            ]

            if groupes_invalides:
                return (
                    False,
                    f"Groupes invalides (doivent commencer par GR ou GF): {', '.join(groupes_invalides)}",
                )

            # Créer la nouvelle configuration
            from datetime import datetime

            config = {
                "groupes_habilites": groupes_habilites,
                "derniere_modification": datetime.now().isoformat(),
                "modifie_par": modifie_par,
            }

            # Sauvegarder
            if self._save_config(config):
                logger.info(
                    f"✓ Habilitations mises à jour par {modifie_par} - "
                    f"{len(groupes_habilites)} groupes habilités"
                )
                return True, "Habilitations mises à jour avec succès"
            else:
                return False, "Erreur lors de la sauvegarde"

        except Exception as e:
            logger.error(f"✗ Erreur mise à jour habilitations: {e}")
            return False, f"Erreur: {str(e)}"

    def user_has_access(self, user_habilitations: dict) -> Tuple[bool, str]:
        """
        Vérifie si un utilisateur a accès à l'application avec correspondance partielle des groupes

        Logique de vérification:
        - Les groupes utilisateur doivent commencer par GR ou GF
        - Si un groupe autorisé (ex: "GR") est un PRÉFIXE d'un groupe utilisateur (ex: "GR_SMS_ADMIN_ENTITE_GCM"),
          l'accès est autorisé
        - Exemple: groupe autorisé "GR_SIMSAN" correspond à "GR_SIMSAN_UTILISATEURS_PVL"

        Args:
            user_habilitations: Dictionnaire des habilitations de l'utilisateur
                               Format API Gauthiq: {"roles": {"GR_XXX": [...], "GF_XXX": [...], ...}}

        Returns:
            Tuple[bool, str]: (a_acces, message_debug)
        """
        try:
            logger.info("=" * 70)
            logger.info(
                "🔍 VÉRIFICATION DES HABILITATIONS - CORRESPONDANCE PARTIELLE (GR/GF)"
            )
            logger.info("=" * 70)

            groupes_habilites = self.get_groupes_habilites()

            if not groupes_habilites:
                logger.warning(
                    "⚠️ Aucun groupe habilité configuré - accès refusé par défaut"
                )
                logger.info("=" * 70)
                return False, "Aucun groupe habilité configuré"

            logger.info(f"📋 Groupes autorisés configurés: {len(groupes_habilites)}")
            for idx, groupe in enumerate(groupes_habilites[:5], 1):
                logger.info(f"   {idx}. {groupe}")
            if len(groupes_habilites) > 5:
                logger.info(f"   ... et {len(groupes_habilites) - 5} autres")

            # ⭐ GROUPE SPÉCIAL: GR_SIMSAN_ALL autorise TOUS les utilisateurs
            if "GR_SIMSAN_ALL" in groupes_habilites:
                logger.info("")
                logger.info("⭐" * 35)
                logger.info("🌐 GROUPE SPÉCIAL 'GR_SIMSAN_ALL' DÉTECTÉ")
                logger.info("✅ ACCÈS AUTORISÉ À TOUS LES UTILISATEURS")
                logger.info(
                    "   → Tout le monde peut se connecter sans vérification de groupes"
                )
                logger.info("⭐" * 35)
                logger.info("=" * 70)
                return True, "Accès autorisé via GR_SIMSAN_ALL (accès universel)"

            # Extraire les groupes de l'utilisateur depuis le format API Gauthiq
            # Format: {"roles": {"GR_SMS_ADMIN_ENTITE_GCM": [...], "GF_XXX": [...], ...}}
            user_groups = []

            logger.info("")
            logger.info(
                "🔍 Extraction des groupes utilisateur depuis les habilitations:"
            )

            # L'API Gauthiq retourne les rôles comme clés du dict "roles"
            if "roles" in user_habilitations and isinstance(
                user_habilitations["roles"], dict
            ):
                all_groups = list(user_habilitations["roles"].keys())

                # Filtrer uniquement les groupes commençant par GR ou GF
                user_groups = [
                    g for g in all_groups if g.startswith("GR") or g.startswith("GF")
                ]

                logger.info(
                    f"   ✅ Trouvé {len(all_groups)} groupe(s) total dans 'roles'"
                )
                logger.info(f"   ✅ Filtré: {len(user_groups)} groupe(s) GR/GF valides")

                if len(all_groups) > len(user_groups):
                    ignored = len(all_groups) - len(user_groups)
                    logger.info(
                        f"   ⚠️  Ignoré: {ignored} groupe(s) ne commençant pas par GR/GF"
                    )

                for idx, groupe in enumerate(user_groups[:5], 1):
                    logger.info(f"      {idx}. {groupe}")
                if len(user_groups) > 5:
                    logger.info(f"      ... et {len(user_groups) - 5} autres")

            # Essayer d'autres formats possibles
            for key in ["groups", "habilitations", "groupes"]:
                if key in user_habilitations:
                    value = user_habilitations[key]
                    if isinstance(value, list):
                        user_groups.extend(value)
                        logger.info(f"   ✅ Trouvé {len(value)} groupe(s) dans '{key}'")
                    elif isinstance(value, dict):
                        user_groups.extend(value.keys())
                        logger.info(
                            f"   ✅ Trouvé {len(value.keys())} groupe(s) dans '{key}'"
                        )
                    elif isinstance(value, str):
                        user_groups.append(value)
                        logger.info(f"   ✅ Trouvé 1 groupe dans '{key}': {value}")

            if not user_groups:
                logger.warning(
                    "⚠️ Aucun groupe trouvé dans les habilitations utilisateur"
                )
                logger.info("=" * 70)
                return False, "Aucun groupe trouvé pour cet utilisateur"

            logger.info("")
            logger.info(f"📊 Total groupes utilisateur extraits: {len(user_groups)}")

            # Vérification avec correspondance partielle
            logger.info("")
            logger.info("🔐 Vérification des correspondances (préfixe):")
            logger.info("-" * 70)

            matches = []

            for groupe_autorise in groupes_habilites:
                logger.info(f"\n   🔍 Groupe autorisé: '{groupe_autorise}'")

                for user_group in user_groups:
                    # Vérifier si le groupe autorisé est un préfixe du groupe utilisateur
                    if user_group.startswith(groupe_autorise):
                        matches.append(
                            {
                                "groupe_autorise": groupe_autorise,
                                "groupe_utilisateur": user_group,
                            }
                        )
                        logger.info(f"      ✅ MATCH avec '{user_group}'")
                        logger.info(
                            f"         → '{user_group}' commence par '{groupe_autorise}'"
                        )
                        break
                else:
                    # Aucun match trouvé pour ce groupe autorisé
                    logger.info("      ❌ Aucune correspondance")

            logger.info("")
            logger.info("-" * 70)

            if matches:
                logger.info(
                    f"✅ ACCÈS AUTORISÉ - {len(matches)} correspondance(s) trouvée(s):"
                )
                for idx, match in enumerate(matches, 1):
                    logger.info(
                        f"   {idx}. Groupe autorisé '{match['groupe_autorise']}' "
                        f"→ Groupe utilisateur '{match['groupe_utilisateur']}'"
                    )
                logger.info("=" * 70)

                # Message de résumé
                groupes_autorises_str = ", ".join(
                    [m["groupe_autorise"] for m in matches]
                )
                return True, f"Accès autorisé via: {groupes_autorises_str}"
            else:
                logger.warning("❌ ACCÈS REFUSÉ - Aucune correspondance trouvée")
                logger.warning("")
                logger.warning("   Groupes autorisés:")
                for groupe in groupes_habilites[:3]:
                    logger.warning(f"      • {groupe}")
                if len(groupes_habilites) > 3:
                    logger.warning(
                        f"      • ... et {len(groupes_habilites) - 3} autres"
                    )

                logger.warning("")
                logger.warning("   Groupes utilisateur:")
                for groupe in user_groups[:3]:
                    logger.warning(f"      • {groupe}")
                if len(user_groups) > 3:
                    logger.warning(f"      • ... et {len(user_groups) - 3} autres")

                logger.info("=" * 70)
                return (
                    False,
                    "Aucun groupe habilité ne correspond aux groupes de l'utilisateur",
                )

        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"❌ ERREUR lors de la vérification des habilitations: {e}")
            logger.error("=" * 70)
            import traceback

            logger.error(traceback.format_exc())
            return False, f"Erreur lors de la vérification: {str(e)}"


# Instance globale
_habilitations_manager = None


def get_habilitations_manager() -> HabilitationsManager:
    """Retourne l'instance du gestionnaire d'habilitations (singleton)"""
    global _habilitations_manager
    if _habilitations_manager is None:
        _habilitations_manager = HabilitationsManager()
    return _habilitations_manager
