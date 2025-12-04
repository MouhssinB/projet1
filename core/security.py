import re
import html
from typing import Optional

def sanitize_user_input(text: str, max_length: int = 5000, allow_newlines: bool = True) -> str:
    """
    Nettoie et sécurise une chaîne de caractères contre les injections.
    
    Args:
        text: Texte à nettoyer
        max_length: Longueur maximale autorisée
        allow_newlines: Autoriser les retours à la ligne
    
    Returns:
        Texte nettoyé et sécurisé
    
    Protections appliquées:
    - Normalisation des apostrophes et guillemets
    - Suppression des caractères de contrôle dangereux
    - Protection contre XSS (HTML encoding)
    - Protection contre SQL injection
    - Suppression des séquences d'échappement
    - Limitation de longueur
    """
    
    if not text or not isinstance(text, str):
        return ""
    
    # 1. Limitation de longueur (DoS protection)
    text = text[:max_length]
    
    # 2. Normalisation des espaces multiples
    text = re.sub(r'\s+', ' ', text) if not allow_newlines else text
    
    # 3. Normalisation des apostrophes typographiques
    replacements = {
        ''': "'",  # Apostrophe courbe gauche
        ''': "'",  # Apostrophe courbe droite
        '"': '"',  # Guillemet courbe gauche
        '"': '"',  # Guillemet courbe droit
        '«': '"',  # Guillemet français ouvrant
        '»': '"',  # Guillemet français fermant
        '`': "'",  # Backtick
        '´': "'",  # Accent aigu
        '′': "'",  # Prime
        '″': '"',  # Double prime
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 4. Suppression des caractères de contrôle dangereux (sauf \n, \r, \t si autorisés)
    if allow_newlines:
        # Garder uniquement \n, \r, \t
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    else:
        # Supprimer tous les caractères de contrôle
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 5. Protection contre les séquences d'échappement ANSI
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    
    # 6. Suppression des balises HTML/XML (protection XSS)
    text = re.sub(r'<[^>]*>', '', text)
    
    # 7. Échappement HTML des caractères spéciaux restants
    text = html.escape(text, quote=True)
    
    # 8. Protection contre SQL injection - suppression de patterns dangereux
    sql_patterns = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM',
        r';\s*UPDATE\s+',
        r';\s*INSERT\s+INTO',
        r'UNION\s+SELECT',
        r'--\s*$',
        r'/\*.*?\*/',
        r';\s*EXEC\s*\(',
        r';\s*EXECUTE\s*\(',
        r'xp_cmdshell',
    ]
    
    for pattern in sql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 9. Suppression des apostrophes/guillemets en début/fin
    text = re.sub(r"^['\"\s]+", "", text)
    text = re.sub(r"['\"\s]+$", "", text)
    
    # 10. Suppression des doubles apostrophes/guillemets consécutifs
    text = re.sub(r"'{2,}", "'", text)
    text = re.sub(r'"{2,}', '"', text)
    
    # 11. Nettoyage final
    text = text.strip()
    
    return text


def validate_message_format(text: str) -> tuple[bool, Optional[str]]:
    """
    Valide le format d'un message utilisateur.
    
    Returns:
        (is_valid, error_message)
    """
    
    if not text:
        return False, "Le message ne peut pas être vide"
    
    if len(text) > 5000:
        return False, "Le message est trop long (maximum 5000 caractères)"
    
    # Vérifier qu'il reste du contenu après nettoyage
    if len(text.strip()) < 1:
        return False, "Le message ne contient pas de contenu valide"
    
    # Vérifier les caractères suspects répétés
    if re.search(r'(.)\1{50,}', text):
        return False, "Le message contient des séquences de caractères suspectes"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sécurise un nom de fichier.
    
    Args:
        filename: Nom de fichier à nettoyer
    
    Returns:
        Nom de fichier sécurisé
    """
    
    if not filename:
        return "unnamed_file"
    
    # Supprimer les caractères dangereux
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Supprimer les espaces multiples
    filename = re.sub(r'\s+', '_', filename)
    
    # Limiter la longueur
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    name = name[:200]
    
    return f"{name}.{ext}" if ext else name


def sanitize_path(path: str) -> str:
    """
    Sécurise un chemin de fichier contre path traversal.
    
    Args:
        path: Chemin à nettoyer
    
    Returns:
        Chemin sécurisé
    """
    
    if not path:
        return ""
    
    # Normaliser les séparateurs
    path = path.replace('\\', '/')
    
    # Supprimer les tentatives de path traversal
    path = re.sub(r'\.\./+', '', path)
    path = re.sub(r'/\.\.', '', path)
    
    # Supprimer les doubles slashes
    path = re.sub(r'/+', '/', path)
    
    # Supprimer les slashes au début/fin
    path = path.strip('/')
    
    return path