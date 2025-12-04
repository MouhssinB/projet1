"""
Gestionnaire de stockage unifié - détecte automatiquement l'environnement
En production : utilise le FileShare Azure monté sur /mnt/storage
En développement : utilise le système de fichiers local dans data/
"""
import os
from pathlib import Path
from typing import Tuple, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Gestionnaire de stockage qui s'adapte automatiquement à l'environnement.
    
    - Production (Azure) : FileShare monté sur /mnt/storage
    - Développement : Répertoire local data/
    """
    
    def __init__(self):
        self.mount_point = os.getenv('AZURE_FILESHARE_MOUNT_POINT', '/mnt/storage')
        self.is_production = self._detect_production()
        self.base_path = self._get_base_path()
        self._ensure_directories()
        
        logger.info(f"📁 StorageManager initialisé")
        logger.info(f"   Mode: {'PRODUCTION (FileShare)' if self.is_production else 'DÉVELOPPEMENT (Local)'}")
        logger.info(f"   Base path: {self.base_path}")
    
    def _detect_production(self) -> bool:
        """Détecte si on est en production (FileShare monté et accessible)"""
        if os.path.exists(self.mount_point) and os.access(self.mount_point, os.W_OK):
            logger.info(f"✅ FileShare détecté et accessible sur {self.mount_point}")
            return True
        else:
            logger.info(f"⚠️  FileShare non disponible - mode développement")
            return False
    
    def _get_base_path(self) -> Path:
        """Retourne le chemin de base pour le stockage"""
        if self.is_production:
            return Path(self.mount_point)
        else:
            return Path(os.getcwd()) / "data"
    
    def _ensure_directories(self):
        """Crée la structure de répertoires nécessaire"""
        directories = [
            self.base_path / "admin",
            self.base_path / "utilisateurs",
            self.base_path / "suivis",
            self.base_path / "conversations",
            self.base_path / "syntheses",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"   ✓ {directory}")
    
    def get_user_folder_path(self, user_email: str) -> Path:
        """
        Retourne le chemin du dossier utilisateur
        Structure: utilisateurs/<user_email>/conversations/
                                            /syntheses/
        """
        user_folder_name = user_email.replace('@', '_').replace('.', '_')
        user_folder = self.base_path / "utilisateurs" / user_folder_name
        
        # Créer les sous-dossiers
        (user_folder / "conversations").mkdir(parents=True, exist_ok=True)
        (user_folder / "syntheses").mkdir(parents=True, exist_ok=True)
        
        return user_folder
    
    def get_admin_folder_path(self) -> Path:
        """Retourne le chemin du dossier admin"""
        return self.base_path / "admin"
    
    def get_journal_path(self) -> Path:
        """Retourne le chemin du fichier journal.csv"""
        return self.get_admin_folder_path() / "journal.csv"
    
    def get_log_path(self) -> Path:
        """Retourne le chemin du fichier application.log"""
        return self.get_admin_folder_path() / "application.log"
    
    def save_file(self, file_path: Path, content: str) -> bool:
        """
        Sauvegarde un fichier avec le contenu donné
        
        Args:
            file_path: Chemin complet du fichier (Path object)
            content: Contenu à sauvegarder (str)
        
        Returns:
            bool: True si succès
        """
        try:
            # Créer le répertoire parent si nécessaire
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire le fichier
            file_path.write_text(content, encoding='utf-8')
            logger.debug(f"✓ Fichier sauvegardé: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Erreur sauvegarde {file_path}: {e}")
            return False
    
    def read_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Lit le contenu d'un fichier
        
        Args:
            file_path: Chemin complet du fichier (Path object)
        
        Returns:
            tuple: (success: bool, content: str or None)
        """
        try:
            if not file_path.exists():
                logger.warning(f"⚠ Fichier non trouvé: {file_path}")
                return False, None
            
            content = file_path.read_text(encoding='utf-8')
            return True, content
            
        except Exception as e:
            logger.error(f"✗ Erreur lecture {file_path}: {e}")
            return False, None
    
    def list_files(self, directory_path: Path, pattern: str = "*") -> List[Dict[str, Any]]:
        """
        Liste les fichiers dans un répertoire
        
        Args:
            directory_path: Chemin du répertoire (Path object)
            pattern: Pattern de fichiers à rechercher (ex: "*.json")
        
        Returns:
            list: Liste de dictionnaires avec infos fichiers
        """
        try:
            if not directory_path.exists():
                logger.debug(f"Répertoire inexistant: {directory_path}")
                return []
            
            files_info = []
            for file_path in directory_path.glob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files_info.append({
                        'filename': file_path.name,
                        'path': str(file_path),
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
            
            return sorted(files_info, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"✗ Erreur liste fichiers {directory_path}: {e}")
            return []
    
    def delete_file(self, file_path: Path) -> bool:
        """
        Supprime un fichier
        
        Args:
            file_path: Chemin complet du fichier (Path object)
        
        Returns:
            bool: True si succès
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"✓ Fichier supprimé: {file_path}")
                return True
            else:
                logger.warning(f"⚠ Fichier non trouvé: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Erreur suppression {file_path}: {e}")
            return False
    
    def append_to_file(self, file_path: Path, content: str) -> bool:
        """
        Ajoute du contenu à la fin d'un fichier
        
        Args:
            file_path: Chemin complet du fichier (Path object)
            content: Contenu à ajouter
        
        Returns:
            bool: True si succès
        """
        try:
            # Créer le répertoire parent si nécessaire
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Ajouter le contenu
            with file_path.open('a', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"✓ Contenu ajouté à: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Erreur ajout dans {file_path}: {e}")
            return False


# Instance globale du gestionnaire de stockage
_storage_manager = None


def get_storage_manager() -> StorageManager:
    """Retourne l'instance du gestionnaire de stockage (singleton)"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager
