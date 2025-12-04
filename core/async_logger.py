import asyncio
import logging
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
import time


class AsyncFileLogger:
    """Logger asynchrone optimisé - écrit directement dans le FileShare monté ou local"""
    
    def __init__(self, log_file: Optional[str] = None, 
                 max_queue_size: int = 10000,
                 batch_size: int = 100,
                 flush_interval: float = 5.0,
                 max_file_size: int = 50 * 1024 * 1024):  # 50MB
        
        # Utiliser le StorageManager pour déterminer le chemin du log
        if log_file is None:
            from .storage_manager import get_storage_manager
            storage = get_storage_manager()
            self.log_file = storage.get_log_path()
        else:
            self.log_file = Path(log_file)
        
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.log_queue = Queue(maxsize=max_queue_size)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_file_size = max_file_size
        
        self.is_running = True
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="async-logger")
        self.writer_thread = None
        
        # Compteurs pour monitoring
        self.logs_written = 0
        self.logs_dropped = 0
        self.last_flush_time = time.time()
        
        self._start_writer()
    
    def _start_writer(self):
        """Démarre le thread d'écriture asynchrone"""
        self.writer_thread = threading.Thread(
            target=self._writer_loop,
            name="log-writer",
            daemon=True
        )
        self.writer_thread.start()
    
    def _writer_loop(self):
        """Boucle principale d'écriture des logs"""
        log_buffer = []
        
        while self.is_running or not self.log_queue.empty():
            try:
                # Collecte des logs en batch
                current_time = time.time()
                
                # Récupérer les logs disponibles
                while len(log_buffer) < self.batch_size:
                    try:
                        # Timeout court pour vérifier périodiquement
                        log_entry = self.log_queue.get(timeout=0.1)
                        log_buffer.append(log_entry)
                        self.log_queue.task_done()
                    except Empty:
                        break
                
                # Écrire si on a des logs ou si l'intervalle est dépassé
                should_flush = (
                    len(log_buffer) >= self.batch_size or
                    (log_buffer and current_time - self.last_flush_time >= self.flush_interval) or
                    not self.is_running
                )
                
                if should_flush and log_buffer:
                    self._write_batch(log_buffer)
                    log_buffer.clear()
                    self.last_flush_time = current_time
                
                # Petite pause si pas de logs
                if not log_buffer:
                    time.sleep(0.1)
                    
            except Exception as e:
                # En cas d'erreur, on continue mais on log sur stderr
                print(f"Erreur dans le writer loop: {e}", file=os.sys.stderr)
                time.sleep(1)
    
    def _write_batch(self, log_entries: list):
        """Écrit un batch de logs de manière atomique"""
        try:
            # Vérifier la taille du fichier et faire une rotation si nécessaire
            if self.log_file.exists() and self.log_file.stat().st_size > self.max_file_size:
                self._rotate_log_file()
            
            # Écriture atomique du batch
            with open(self.log_file, 'a', encoding='utf-8', buffering=8192) as f:
                for entry in log_entries:
                    f.write(entry + '\n')
                f.flush()  # Force l'écriture sur disque
                os.fsync(f.fileno())  # Sync sur Azure
            
            self.logs_written += len(log_entries)
            
        except Exception as e:
            print(f"Erreur lors de l'écriture du batch: {e}", file=os.sys.stderr)
            # On pourrait remettre les logs en queue ici si nécessaire
    
    def _rotate_log_file(self):
        """Rotation simple du fichier de log"""
        try:
            backup_file = self.log_file.with_suffix(f'.{int(time.time())}.log')
            if self.log_file.exists():
                self.log_file.rename(backup_file)
        except Exception as e:
            print(f"Erreur lors de la rotation: {e}", file=os.sys.stderr)
    
    def log(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Méthode principale pour logger un message"""
        if not self.is_running:
            return False
        
        timestamp = datetime.now().isoformat()
        
        # Format compact pour Azure
        log_entry = f"{timestamp} - {level} - {message}"
        
        # Ajouter des données extra si présentes
        if extra_data:
            try:
                extra_str = json.dumps(extra_data, ensure_ascii=False, separators=(',', ':'))
                log_entry += f" - EXTRA: {extra_str}"
            except Exception:
                log_entry += f" - EXTRA: {str(extra_data)}"
        
        # Tentative d'ajout en queue (non-bloquant)
        try:
            self.log_queue.put_nowait(log_entry)
            return True
        except:
            # Queue pleine - on abandonne le log pour éviter de bloquer
            self.logs_dropped += 1
            if self.logs_dropped % 100 == 0:  # Log périodique des pertes
                print(f"WARNING: {self.logs_dropped} logs dropped due to full queue", 
                      file=os.sys.stderr)
            return False
    
    def info(self, message: str, **kwargs):
        return self.log("INFO", message, kwargs if kwargs else None)
    
    def debug(self, message: str, **kwargs):
        return self.log("DEBUG", message, kwargs if kwargs else None)
    
    def warning(self, message: str, **kwargs):
        return self.log("WARNING", message, kwargs if kwargs else None)
    
    def error(self, message: str, **kwargs):
        return self.log("ERROR", message, kwargs if kwargs else None)
    
    def critical(self, message: str, **kwargs):
        return self.log("CRITICAL", message, kwargs if kwargs else None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du logger"""
        return {
            "logs_written": self.logs_written,
            "logs_dropped": self.logs_dropped,
            "queue_size": self.log_queue.qsize(),
            "is_running": self.is_running,
            "max_queue_size": self.log_queue.maxsize
        }
    
    def shutdown(self, timeout: float = 10.0):
        """Arrêt propre du logger"""
        self.is_running = False
        
        # Attendre que la queue se vide
        start_time = time.time()
        while not self.log_queue.empty() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        # Attendre le thread writer
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5.0)
        
        # Fermer l'executor (sans timeout car non supporté en Python 3.11)
        self.executor.shutdown(wait=True)
        
        stats = self.get_stats()
        print(f"AsyncLogger shutdown - Stats: {stats}", file=os.sys.stderr)


# Instance globale du logger asynchrone
async_logger = None

def get_async_logger() -> AsyncFileLogger:
    """Retourne l'instance globale du logger asynchrone"""
    global async_logger
    if async_logger is None:
        async_logger = AsyncFileLogger()
    return async_logger

def shutdown_async_logger():
    """Ferme proprement le logger asynchrone"""
    global async_logger
    if async_logger:
        async_logger.shutdown()
        async_logger = None