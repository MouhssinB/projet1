"""
Fonctions de stockage unifiées - utilise directement le FileShare monté ou local
En production : FileShare Azure monté sur /mnt/storage
En développement : Répertoire local data/
"""

from datetime import datetime
import logging
from .storage_manager import get_storage_manager

logger = logging.getLogger(__name__)

# Répertoires dans le stockage
FILESHARE_ADMIN_DIR = "admin"
FILESHARE_USERS_DIR = "utilisateurs"
FILESHARE_GUIDE_DIR = "guide_utilisateur"


def ensure_directory_exists(directory_path):
    """Crée un répertoire dans le stockage s'il n'existe pas (récursif)"""
    try:
        storage = get_storage_manager()
        full_path = storage.base_path / directory_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"✓ Répertoire assuré: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"✗ Erreur création répertoire '{directory_path}': {str(e)}")
        return False


def save_file_to_fileshare(data, file_path):
    """Sauvegarde un fichier dans le stockage"""
    try:
        storage = get_storage_manager()
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        full_path = storage.base_path / file_path
        return storage.save_file(full_path, data)
    except Exception as e:
        logger.error(f"✗ Erreur sauvegarde '{file_path}': {str(e)}")
        return False


def get_file_from_fileshare(file_path):
    """Récupère un fichier depuis le stockage"""
    try:
        storage = get_storage_manager()
        full_path = storage.base_path / file_path
        if not full_path.exists():
            logger.warning(f"⚠ Fichier non trouvé: {file_path}")
            return False, None
        content = full_path.read_text(encoding="utf-8")
        return True, content
    except Exception as e:
        logger.error(f"✗ Erreur récupération '{file_path}': {str(e)}")
        return False, None


def list_files_from_fileshare(directory_path):
    """Liste les fichiers dans un répertoire"""
    try:
        storage = get_storage_manager()
        full_path = storage.base_path / directory_path
        if not full_path.exists():
            logger.debug(f"Répertoire inexistant: {directory_path}")
            return []
        files_info = []
        for file_path in full_path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files_info.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )
        return sorted(files_info, key=lambda x: x["modified"], reverse=True)
    except Exception as e:
        logger.error(f"✗ Erreur liste fichiers '{directory_path}': {str(e)}")
        return []


def get_user_folder_path_fileshare(user_email):
    """Récupère ou crée le chemin du dossier utilisateur"""
    try:
        storage = get_storage_manager()
        user_folder = storage.get_user_folder_path(user_email)
        user_folder_path = str(user_folder.relative_to(storage.base_path))
        history_conv = []
        history_eval = []
        try:
            conv_files = list_files_from_fileshare(f"{user_folder_path}/conversations")
            history_conv = [f["filename"] for f in conv_files]
        except:
            pass
        try:
            synth_files = list_files_from_fileshare(f"{user_folder_path}/syntheses")
            history_eval = [f["filename"] for f in synth_files]
        except:
            pass
        logger.info(f"📁 Dossier utilisateur: {user_folder_path}")
        logger.info(
            f"   Fichiers - Conversations: {len(history_conv)}, Synthèses: {len(history_eval)}"
        )
        return user_folder_path, history_conv, history_eval
    except Exception as e:
        logger.error(f"✗ Erreur création dossier utilisateur: {str(e)}")
        return f"{FILESHARE_USERS_DIR}/default_user", [], []


def save_file_to_azure(data, file_type, filename, user_folder):
    """Sauvegarde un fichier dans le stockage (compatibilité)"""
    try:
        if file_type == "conversation":
            file_path = f"{user_folder}/conversations/{filename}"
        elif file_type == "synthese":
            file_path = f"{user_folder}/syntheses/{filename}"
        else:
            raise ValueError(f"Type de fichier non supporté: {file_type}")
        success = save_file_to_fileshare(data, file_path)
        if success:
            logger.info(f"✓ Fichier sauvegardé: {file_path}")
            return True, file_path
        else:
            logger.error(f"✗ Échec sauvegarde: {filename}")
            return False, None
    except Exception as e:
        logger.error(f"✗ Erreur sauvegarde fichier '{filename}': {str(e)}")
        return False, None


def get_file_from_azure(file_type, filename, user_folder):
    """Récupère un fichier depuis le stockage (compatibilité)"""
    try:
        if file_type == "conversation":
            file_path = f"{user_folder}/conversations/{filename}"
        elif file_type == "synthese":
            file_path = f"{user_folder}/syntheses/{filename}"
        else:
            raise ValueError(f"Type de fichier non supporté: {file_type}")
        return get_file_from_fileshare(file_path)
    except Exception as e:
        logger.error(f"✗ Erreur récupération '{filename}': {str(e)}")
        return False, None


def list_files_from_azure(file_type, user_folder):
    """Liste les fichiers d'un type donné (compatibilité)"""
    try:
        if file_type == "conversation":
            directory_path = f"{user_folder}/conversations"
        elif file_type == "synthese":
            directory_path = f"{user_folder}/syntheses"
        else:
            raise ValueError(f"Type de fichier non supporté: {file_type}")
        return list_files_from_fileshare(directory_path)
    except Exception as e:
        logger.error(f"✗ Erreur liste fichiers {file_type}: {str(e)}")
        return []


def save_to_azure_storage(data, filename):
    """Fonction de compatibilité - sauvegarde dans le stockage"""
    return save_file_to_fileshare(data, filename)


def get_guide_path():
    """Récupère le chemin du guide utilisateur"""
    try:
        storage = get_storage_manager()
        guide_dir = storage.base_path / FILESHARE_GUIDE_DIR
        guide_dir.mkdir(parents=True, exist_ok=True)

        # Chercher le fichier PDF dans le répertoire
        pdf_files = list(guide_dir.glob("*.pdf"))
        if pdf_files:
            return pdf_files[0]  # Retourne le premier PDF trouvé
        return None
    except Exception as e:
        logger.error(f"✗ Erreur récupération guide: {str(e)}")
        return None


def upload_guide(file_data, filename):
    """Upload le guide utilisateur"""
    try:
        storage = get_storage_manager()
        guide_dir = storage.base_path / FILESHARE_GUIDE_DIR
        guide_dir.mkdir(parents=True, exist_ok=True)

        # Supprimer l'ancien guide s'il existe
        for old_file in guide_dir.glob("*.pdf"):
            old_file.unlink()
            logger.info(f"✓ Ancien guide supprimé: {old_file.name}")

        # Sauvegarder le nouveau fichier
        file_path = guide_dir / filename
        file_path.write_bytes(file_data)
        logger.info(f"✓ Guide uploadé: {filename}")
        return True, str(file_path)
    except Exception as e:
        logger.error(f"✗ Erreur upload guide: {str(e)}")
        return False, None


def delete_guide():
    """Supprime le guide utilisateur"""
    try:
        storage = get_storage_manager()
        guide_dir = storage.base_path / FILESHARE_GUIDE_DIR

        deleted = False
        for pdf_file in guide_dir.glob("*.pdf"):
            pdf_file.unlink()
            logger.info(f"✓ Guide supprimé: {pdf_file.name}")
            deleted = True

        return deleted
    except Exception as e:
        logger.error(f"✗ Erreur suppression guide: {str(e)}")
        return False


def init_fileshare_structure():
    """Initialise la structure de base du stockage au démarrage de l'application"""
    try:
        logger.info("🔧 Initialisation de la structure de stockage...")
        storage = get_storage_manager()
        logger.info("✅ Structure de stockage initialisée")
        logger.info(
            f"   Mode: {'Production (FileShare)' if storage.is_production else 'Développement (Local)'}"
        )
        logger.info(f"   Base: {storage.base_path}")
        return True
    except Exception as e:
        logger.error(f"✗ Erreur initialisation structure: {str(e)}")
        return False
