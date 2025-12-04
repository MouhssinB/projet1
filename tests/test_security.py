"""
Tests des fonctions de sécurité
"""
from core.security import (
    sanitize_user_input,
    validate_message_format,
    sanitize_filename,
    sanitize_path,
)


def test_sanitize_user_input():
    """Test de la sanitisation des inputs utilisateur"""
    # Test de base
    result = sanitize_user_input("Hello world")
    assert result == "Hello world"

    # Test HTML escaping
    result = sanitize_user_input("<script>alert('xss')</script>")
    assert "<script>" not in result

    # Test longueur max
    long_text = "x" * 10000
    result = sanitize_user_input(long_text, max_length=100)
    assert len(result) <= 100


def test_validate_message_format():
    """Test de validation du format de message"""
    # Message valide
    valid, error = validate_message_format("Bonjour")
    assert valid is True
    assert error is None

    # Message vide
    valid, error = validate_message_format("")
    assert valid is False
    assert error is not None


def test_sanitize_filename():
    """Test de sanitisation des noms de fichiers"""
    # Nom normal
    result = sanitize_filename("document.pdf")
    assert result == "document.pdf"

    # Caractères dangereux
    result = sanitize_filename("../../../etc/passwd")
    assert "../" not in result

    # Espaces
    result = sanitize_filename("mon document.pdf")
    assert " " not in result


def test_sanitize_path():
    """Test de sanitisation des chemins"""
    # Chemin normal
    result = sanitize_path("data/conversations/file.json")
    assert result == "data/conversations/file.json"

    # Path traversal
    result = sanitize_path("../../../etc/passwd")
    assert "../" not in result

    # Slashes multiples
    result = sanitize_path("data//conversations///file.json")
    assert "//" not in result
