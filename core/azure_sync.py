import os
import threading
import time
import csv
import io
from datetime import datetime, timedelta
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient, ShareServiceClient
from pathlib import Path

class AzureFileShareSync:
    """Service de synchronisation automatique vers Azure FileShare"""

    def __init__(self, connection_string, share_name, interval_minutes: int, max_size_mb: int,
                 session_dir: str, session_max_age_hours: int):
        self.connection_string = connection_string
        self.share_name = share_name
        self.interval_seconds = int(interval_minutes * 60)
        self.max_size_mb = max_size_mb
        self.running = False
        self.thread = None
        self.initialized = False
        
        # Configuration nettoyage sessions
        self.session_dir = Path(session_dir) if session_dir else None
        self.session_max_age_hours = session_max_age_hours
        
        # Fichiers par défaut - peuvent être modifiés après l'instanciation
        self.files_to_sync = [
            {'local': 'data/suivis/journal.csv', 'remote': 'admin/journal.csv'},
            {'local': 'log/application.log', 'remote': 'admin/application.log'}
        ]
    
    def initialize_fileshare(self):
        """Crée le FileShare et les répertoires s'ils n'existent pas"""
        try:
            # Créer le service client
            service_client = ShareServiceClient.from_connection_string(self.connection_string)
            
            # Créer le share s'il n'existe pas
            try:
                share_client = service_client.get_share_client(self.share_name)
                share_client.create_share()
                print(f"[Azure Sync] ✓ FileShare '{self.share_name}' créé")
            except Exception as e:
                if "ShareAlreadyExists" in str(e):
                    print(f"[Azure Sync] ✓ FileShare '{self.share_name}' existe déjà")
                else:
                    print(f"[Azure Sync] ⚠ Erreur création share: {e}")
            
            # Créer les répertoires nécessaires
            directories = set()
            for file_config in self.files_to_sync:
                dir_path = os.path.dirname(file_config['remote'])
                if dir_path:
                    directories.add(dir_path)
            
            for dir_path in directories:
                try:
                    dir_client = ShareDirectoryClient.from_connection_string(
                        self.connection_string, self.share_name, dir_path
                    )
                    
                    # Vérifier si le répertoire existe avant de le créer
                    try:
                        dir_client.get_directory_properties()
                        print(f"[Azure Sync] ✓ Répertoire '{dir_path}' existe déjà")
                    except Exception:
                        # Le répertoire n'existe pas, on le crée
                        dir_client.create_directory()
                        print(f"[Azure Sync] ✓ Répertoire '{dir_path}' créé")
                        
                except Exception as e:
                    print(f"[Azure Sync] ⚠ Erreur avec le répertoire '{dir_path}': {e}")
            
            self.initialized = True
            print(f"[Azure Sync] ✓ Initialisation terminée")
            return True
            
        except Exception as e:
            print(f"[Azure Sync] ✗ Erreur initialisation: {e}")
            return False
    
    def download_from_fileshare(self, remote_path):
        """Télécharge un fichier depuis Azure FileShare"""
        try:
            file_client = ShareFileClient.from_connection_string(
                self.connection_string, self.share_name, remote_path
            )
            download = file_client.download_file()
            return download.readall().decode('utf-8')
        except:
            return ""
    
    def upload_to_fileshare(self, remote_path, content):
        """Upload un fichier vers Azure FileShare"""
        try:
            file_client = ShareFileClient.from_connection_string(
                self.connection_string, self.share_name, remote_path
            )
            
            # Supprimer le fichier s'il existe déjà
            try:
                file_client.delete_file()
            except:
                pass
            
            # Upload le nouveau contenu
            file_client.upload_file(content.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[Azure Sync] Erreur upload {remote_path}: {e}")
            return False
    
    def archive_file(self, remote_path):
        """Archive le fichier avec un timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_path = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        name, ext = os.path.splitext(filename)
        archive_path = f"{dir_path}/{name}_{timestamp}{ext}"
        
        try:
            content = self.download_from_fileshare(remote_path)
            self.upload_to_fileshare(archive_path, content)
            print(f"[Azure Sync] ✓ Archivé: {archive_path}")
            return True
        except Exception as e:
            print(f"[Azure Sync] Erreur archivage {remote_path}: {e}")
            return False
    
    def process_journal_csv(self, content):
        """
        Traite le contenu du fichier journal.csv pour fusionner les lignes
        'note utilisateur' avec les lignes 'génération de synthèse' correspondantes.
        
        Args:
            content (str): Contenu brut du fichier CSV
            
        Returns:
            str: Contenu traité avec les lignes fusionnées
        """
        if not content.strip():
            return content
        
        try:
            # Lire le CSV
            lines = content.strip().split('\n')
            if not lines:
                return content
            
            # Détecter l'en-tête (ligne contenant 'user,mail,event')
            header = None
            header_idx = -1
            for idx, line in enumerate(lines):
                if line.startswith('user,') or line.startswith('user;'):
                    header = line
                    header_idx = idx
                    break
            
            # Si pas d'en-tête trouvé, considérer que toutes les lignes sont des données
            if header_idx == -1:
                data_lines = lines
                header = None
                print(f"[Journal Processing] Aucun en-tête trouvé, traitement de {len(lines)} lignes de données")
            else:
                data_lines = lines[header_idx + 1:] if header_idx + 1 < len(lines) else []
                print(f"[Journal Processing] En-tête trouvé à la ligne {header_idx}, {len(data_lines)} lignes de données")
            
            if not data_lines:
                return content
            
            # Parser les lignes CSV
            reader = csv.reader(data_lines)
            rows = list(reader)
            
            # Grouper les lignes par utilisateur (colonne 0)
            user_groups = {}
            for idx, row in enumerate(rows):
                if len(row) < 3:  # Ligne invalide
                    continue
                user = row[0]
                if user not in user_groups:
                    user_groups[user] = []
                user_groups[user].append({'index': idx, 'row': row})
            
            # Marquer les lignes à supprimer
            lines_to_remove = set()
            
            # Pour chaque utilisateur, fusionner les notes avec les synthèses
            for user, user_rows in user_groups.items():
                for i, item in enumerate(user_rows):
                    row = item['row']
                    idx = item['index']
                    
                    # Si c'est une ligne "génération de synthèse"
                    if len(row) >= 3 and row[2] == 'génération de synthèse':
                        # Chercher une ligne "note utilisateur" juste avant dans le même groupe
                        for j in range(i - 1, -1, -1):
                            prev_item = user_rows[j]
                            prev_row = prev_item['row']
                            prev_idx = prev_item['index']
                            
                            # Si on trouve une note utilisateur
                            if len(prev_row) >= 5 and prev_row[2] == 'note utilisateur':
                                # Fusionner : prendre la note de la ligne "note utilisateur"
                                note_user = prev_row[4] if len(prev_row) > 4 else '--'
                                
                                # Mettre à jour la ligne de synthèse avec la note
                                if len(row) > 4:
                                    row[4] = note_user
                                
                                # Marquer la ligne "note utilisateur" pour suppression
                                lines_to_remove.add(prev_idx)
                                
                                print(f"[Journal Processing] Fusion: note={note_user} pour {user}")
                                break  # On ne fusionne qu'avec la note la plus proche
                            
                            # Si on trouve une autre synthèse ou connexion, on arrête
                            elif prev_row[2] in ['génération de synthèse', 'connexion']:
                                break
            
            # Reconstruire le CSV sans les lignes supprimées
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Écrire l'en-tête
            if header:
                output.write(header + '\n')
            
            # Écrire les lignes conservées
            lines_written = 0
            for idx, row in enumerate(rows):
                if idx not in lines_to_remove:
                    writer.writerow(row)
                    lines_written += 1
            
            result = output.getvalue()
            
            if lines_to_remove:
                print(f"[Journal Processing] ✓ {len(lines_to_remove)} ligne(s) 'note utilisateur' fusionnée(s)")
            print(f"[Journal Processing] ✓ Résultat: {lines_written} lignes conservées sur {len(rows)} traitées")
            
            return result
            
        except Exception as e:
            print(f"[Journal Processing] ✗ Erreur traitement: {e}")
            import traceback
            traceback.print_exc()
            # En cas d'erreur, retourner le contenu original
            return content
    
    def sync_file(self, local_path, remote_path):
        """Synchronise un fichier local vers Azure FileShare"""
        if not os.path.exists(local_path):
            return
        
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                local_content = f.read()
            
            if not local_content.strip():
                return
            
            # Traitement spécial pour journal.csv : fusionner les lignes
            is_journal = 'journal.csv' in local_path.lower()
            
            # Traiter le contenu LOCAL avant de le combiner
            if is_journal:
                print(f"[Azure Sync] 📝 Traitement du contenu local journal.csv")
                local_content = self.process_journal_csv(local_content)
            
            remote_content = self.download_from_fileshare(remote_path)
            
            if remote_content:
                combined_content = remote_content + local_content
            else:
                combined_content = local_content
            
            # Traiter aussi le contenu combiné (pour fusionner avec les anciennes lignes)
            if is_journal:
                print(f"[Azure Sync] 📝 Traitement du contenu combiné journal.csv")
                combined_content = self.process_journal_csv(combined_content)
            
            size_mb = len(combined_content.encode('utf-8')) / (1024 * 1024)
            
            if size_mb > self.max_size_mb:
                print(f"[Azure Sync] ⚠ Taille dépassée ({size_mb:.2f} Mo) - Archivage...")
                self.archive_file(remote_path)
                # Utiliser le contenu local déjà traité
                combined_content = local_content
            
            if self.upload_to_fileshare(remote_path, combined_content):
                print(f"[Azure Sync] ✓ Synchronisé: {local_path} ({size_mb:.2f} Mo)")
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write("")
        except Exception as e:
            print(f"[Azure Sync] Erreur sync {local_path}: {e}")
    
    def sync_all_files(self):
        """Synchronise tous les fichiers configurés"""
        for file_config in self.files_to_sync:
            self.sync_file(file_config['local'], file_config['remote'])
    
    def clean_old_sessions(self):
        """
        Nettoie les fichiers de session dont la dernière modification 
        remonte à plus de session_max_age_hours
        """
        if not self.session_dir or not self.session_dir.exists():
            return
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.session_max_age_hours)
            files_deleted = 0
            total_size = 0
            errors = 0
            
            print(f"[Session Cleanup] 🧹 Nettoyage des sessions > {self.session_max_age_hours}h")
            
            # Parcourir tous les fichiers du répertoire
            for item in self.session_dir.iterdir():
                try:
                    if item.is_file():
                        # Obtenir la date de dernière modification
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        
                        # Vérifier si le fichier est trop ancien
                        if mtime < cutoff_time:
                            file_size = item.stat().st_size
                            item.unlink()
                            files_deleted += 1
                            total_size += file_size
                            
                            age_hours = (datetime.now() - mtime).total_seconds() / 3600
                            print(f"[Session Cleanup]   Supprimé: {item.name} (âge: {age_hours:.1f}h)")
                    
                    elif item.is_dir():
                        # Supprimer les sous-répertoires anciens
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if mtime < cutoff_time:
                            import shutil
                            shutil.rmtree(item)
                            files_deleted += 1
                            print(f"[Session Cleanup]   Répertoire supprimé: {item.name}")
                
                except Exception as e:
                    errors += 1
                    print(f"[Session Cleanup]   Erreur suppression {item.name}: {e}")
            
            if files_deleted > 0:
                size_mb = total_size / (1024 * 1024)
                print(f"[Session Cleanup] ✓ {files_deleted} sessions supprimées, {size_mb:.2f} Mo libérés")
            
            if errors > 0:
                print(f"[Session Cleanup] ⚠ {errors} erreur(s)")
                
        except Exception as e:
            print(f"[Session Cleanup] Erreur: {e}")
    
    def _sync_loop(self):
        """Boucle de synchronisation (exécutée dans un thread)"""
        print(f"[Azure Sync] 🚀 Service démarré - Intervalle: {self.interval_seconds} secondes")
        
        if self.session_dir:
            print(f"[Session Cleanup] 📂 Nettoyage activé - Âge max: {self.session_max_age_hours}h")
        
        # Initialiser le FileShare et les répertoires au démarrage
        if not self.initialize_fileshare():
            print(f"[Azure Sync] ✗ Impossible d'initialiser le FileShare. Service arrêté.")
            return
        
        while self.running:
            try:
                # 1. Synchroniser les fichiers vers FileShare
                self.sync_all_files()
                
                # 2. Nettoyer les anciennes sessions
                if self.session_dir:
                    self.clean_old_sessions()
                
            except Exception as e:
                print(f"[Azure Sync] Erreur: {e}")
            
            time.sleep(self.interval_seconds)
    
    def start(self):
        """Démarre le service de synchronisation en arrière-plan"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Arrête le service de synchronisation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)