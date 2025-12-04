"""
Tests des modèles Pydantic
"""
import pytest
from pydantic import ValidationError

from app.models.chat import ChatMessage, ChatResponse
from app.models.profile import ProfileRequest
from app.models.rating import UserRating
from app.models.habilitations import HabilitationsConfig


def test_chat_message_validation():
    """Test validation du message de chat"""
    # Message valide
    msg = ChatMessage(message="Bonjour")
    assert msg.message == "Bonjour"

    # Message vide devrait échouer
    with pytest.raises(ValidationError):
        ChatMessage(message="")

    # Message trop long devrait échouer
    with pytest.raises(ValidationError):
        ChatMessage(message="x" * 6000)


def test_profile_request_validation():
    """Test validation de la requête de profil"""
    # Profil valide
    profile = ProfileRequest(profile_type="Particulier")
    assert profile.profile_type == "Particulier"
    assert profile.nb_caracteristiques == 2  # Valeur par défaut

    # Type de profil invalide
    with pytest.raises(ValidationError):
        ProfileRequest(profile_type="InvalidType")


def test_user_rating_validation():
    """Test validation de la note utilisateur"""
    # Note valide
    rating = UserRating(note=5, commentaire="Excellent")
    assert rating.note == 5
    assert rating.commentaire == "Excellent"

    # Note hors limites
    with pytest.raises(ValidationError):
        UserRating(note=0)

    with pytest.raises(ValidationError):
        UserRating(note=6)


def test_habilitations_config():
    """Test du modèle de configuration des habilitations"""
    config = HabilitationsConfig(
        groupes_habilites=["GR_SIMSAN_UTILISATEURS_PVL", "GR_SIMSAN_ADMIN"]
    )
    assert len(config.groupes_habilites) == 2
    assert "GR_SIMSAN_ADMIN" in config.groupes_habilites
