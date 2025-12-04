"""
Configuration centralisée pour l'application FastAPI
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application"""

    # Application
    app_name: str = "GMA Training Bot IHM"
    app_version: str = "2.0.0"
    debug: bool = False

    # Mode d'authentification : "local" ou "production"
    # local : gauthiq sans SSL (développement uniquement)
    # production : gauthiq avec SSL sécurisé
    auth_mode: str = "production"

    # Security
    secret_key: str
    session_lifetime_hours: int = 24
    session_cookie_name: str = "session_simsan"
    session_cookie_samesite: str = "Lax"
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_m: str
    azure_openai_deployment_n: str

    # OAuth2 Gauthiq
    gauthiq_client_id: str
    gauthiq_client_secret: str
    gauthiq_discovery_url: str
    gauthiq_redirect_uri: str
    gauthiq_habilitation: str
    gauthiq_habilitation_filtre: str
    gauthiq_ssl_verify: bool = True

    # Admin users (comma-separated)
    liste_admins: str = ""

    # Azure Speech
    azure_speech_key: Optional[str] = None
    azure_service_region: Optional[str] = None
    azure_speech_endpoint: Optional[str] = None

    # Azure Storage
    azure_storage_connection_string: Optional[str] = None
    azure_storage_account_name: Optional[str] = None
    azure_storage_container_name: Optional[str] = None
    azure_storage_base_blob_folder: Optional[str] = None
    azure_fileshare_name: Optional[str] = None
    azure_fileshare_mount_point: str = "/mnt/storage"

    # Application Insights
    applicationinsights_connection_string: Optional[str] = None

    # Forms and External URLs
    url_forms_eval: Optional[str] = None

    # Logging Configuration
    pythonunbuffered: str = "1"
    async_log_queue_size: int = 5000
    async_log_batch_size: int = 50
    async_log_flush_interval: float = 3.0
    taille_fichiers_max_mb_rotation: int = 5

    # OAuth2 Gauthiq - Additional
    gauthiq_habilitation_endpoint: str = "/api/habilitations"

    # Session Configuration - Additional
    session_max_age_hours: int = 1
    session_cookie_path: str = "/"
    session_type: str = "filesystem"
    session_file_dir: str = "flask_session/"
    session_file_threshold: int = 100
    session_use_signer: bool = True
    session_permanent: bool = True

    # Server Configuration
    port: int = 5000
    gunicorn_workers: int = 4
    gunicorn_threads: int = 2
    gunicorn_timeout: int = 600

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_admin_list(self) -> list[str]:
        """Retourne la liste des administrateurs"""
        if not self.liste_admins:
            return []
        return [admin.strip() for admin in self.liste_admins.split(",")]

    def is_production(self) -> bool:
        """Vérifie si on est en production (Azure FileShare monté)"""
        return os.path.exists(self.azure_fileshare_mount_point)

    @property
    def session_max_age(self) -> int:
        """Retourne la durée de session en secondes"""
        return self.session_lifetime_hours * 3600

    def is_local_auth_mode(self) -> bool:
        """Vérifie si on est en mode authentification local (sans SSL)"""
        return self.auth_mode.lower() == "local"

    def is_production_auth_mode(self) -> bool:
        """Vérifie si on est en mode authentification production (avec SSL)"""
        return self.auth_mode.lower() == "production"

    def get_auth_ssl_verify(self) -> bool:
        """
        Retourne la configuration SSL pour l'authentification selon le mode.

        - Mode local : SSL désactivé (False)
        - Mode production : SSL activé (True)
        """
        if self.is_local_auth_mode():
            return False
        return self.gauthiq_ssl_verify


@lru_cache()
def get_settings() -> Settings:
    """Retourne les paramètres de configuration (cached)"""
    return Settings()
