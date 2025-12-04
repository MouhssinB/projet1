"""
Modèles pour les profils utilisateur
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class PersonDetails(BaseModel):
    """Détails d'une personne"""
    Nom: str
    Age: int
    Sexe: str
    Profession: str
    Localisation: str
    situation_maritale: Optional[str] = None
    nombre_enfants: Optional[int] = None
    profil_passerelle: Optional[bool] = None
    aidant: Optional[bool] = None
    a_deja_contrat_gma: Optional[bool] = None
    hobby: Optional[str] = None


class ProfileData(BaseModel):
    """Données de profil complètes"""
    type_de_personne: str
    personne: PersonDetails
    caracteristiques: List[str]
    objections: List[str]
    aleas: List[str]


class ProfileRequest(BaseModel):
    """Requête pour définir un profil"""
    profile_type: str = Field(..., pattern="^(Particulier|ACPS|Agriculteur)$")
    nb_caracteristiques: int = Field(default=2, ge=1, le=5)
    nb_objections: int = Field(default=1, ge=1, le=5)
    nb_aleas: int = Field(default=1, ge=1, le=5)
