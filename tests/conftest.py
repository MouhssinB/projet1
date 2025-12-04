"""
Configuration des tests pytest
"""
import pytest
import os
from fastapi.testclient import TestClient

# Configuration des variables d'environnement pour les tests
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long-for-security"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
os.environ["AZURE_OPENAI_API_KEY"] = "test-api-key"
os.environ["AZURE_OPENAI_DEPLOYMENT_m"] = "test-deployment-m"
os.environ["AZURE_OPENAI_DEPLOYMENT_n"] = "test-deployment-n"
os.environ["GAUTHIQ_CLIENT_ID"] = "test-client-id"
os.environ["GAUTHIQ_CLIENT_SECRET"] = "test-client-secret"
os.environ["GAUTHIQ_DISCOVERY_URL"] = "https://test.gauthiq.com/.well-known/openid-configuration"
os.environ["GAUTHIQ_REDIRECT_URI"] = "https://test.app.com/oauth2callback"
os.environ["GAUTHIQ_HABILITATION"] = "https://test.gauthiq.com/habilitations"
os.environ["GAUTHIQ_HABILITATION_FILTRE"] = "test-filter"
os.environ["GAUTHIQ_SSL_VERIFY"] = "false"


@pytest.fixture
def client():
    """
    Client de test FastAPI
    """
    from main_fastapi import app

    return TestClient(app)


@pytest.fixture
def authenticated_client(client):
    """
    Client de test avec session authentifiée
    """
    # Simuler une session authentifiée
    with client.session_transaction() as session:
        session["user"] = {
            "sub": "test-user-id",
            "preferred_username": "test_user",
            "email": "test@example.com",
            "name": "Test User"
        }
        session["access_token"] = "test-access-token"
        session["habilitations"] = {
            "roles": {
                "GR_SIMSAN_UTILISATEURS_PVL": ["USER"]
            }
        }
        session["auth_timestamp"] = "2025-01-01T00:00:00"
        session["user_name"] = "test_user"
        session["user_email"] = "test@example.com"
        session["user_id"] = "test-user-id"

    return client
