"""
Tests des endpoints de santé
"""


def test_health_check(client):
    """Test du health check endpoint"""
    response = client.get("/_stcore/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_check_admin_unauthorized(client):
    """Test check_admin sans authentification"""
    response = client.get("/check_admin")
    # Devrait retourner is_admin: false sans erreur
    assert response.status_code == 200
    data = response.json()
    assert "is_admin" in data
    assert data["is_admin"] is False
