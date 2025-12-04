"""
Tests des routes d'authentification
"""


def test_login_redirects(client):
    """Test que /login redirige vers OAuth"""
    response = client.get("/login", follow_redirects=False)
    assert response.status_code in [302, 307]  # Redirect


def test_logout_clears_session(client):
    """Test que /logout efface la session"""
    # Créer une session
    with client.session_transaction() as session:
        session["user"] = {"email": "test@example.com"}

    # Se déconnecter
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code in [302, 307]  # Redirect vers /

    # Vérifier que la session est effacée
    with client.session_transaction() as session:
        assert "user" not in session


def test_protected_route_redirects_to_login(client):
    """Test qu'une route protégée redirige vers /login"""
    response = client.get("/", follow_redirects=False)
    # Sans session, devrait rediriger ou retourner 401
    assert response.status_code in [302, 307, 401]
