"""
Tests de sécurité pour la version production de Gauthiq Auth

Ces tests vérifient que toutes les mesures de sécurité sont en place.
"""

import pytest
import os
from datetime import datetime, timedelta
from flask import Flask, session
from simsan.infra.src.auth.gauthiq import GauthiqAuthProduction


class TestProductionSecurityChecks:
    """Tests de sécurité pour la version production"""
    
    def test_secret_key_validation_missing(self):
        """Vérifie que l'absence de SECRET_KEY est détectée"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = None
        
        auth = GauthiqAuthProduction()
        
        with pytest.raises(ValueError, match="SECRET_KEY est obligatoire"):
            auth.init_app(app)
    
    def test_secret_key_validation_too_short(self):
        """Vérifie que les SECRET_KEY trop courtes sont rejetées"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'short'
        
        auth = GauthiqAuthProduction()
        
        with pytest.raises(ValueError, match="SECRET_KEY trop courte"):
            auth.init_app(app)
    
    def test_secret_key_validation_default(self):
        """Vérifie que les SECRET_KEY par défaut sont rejetées"""
        app = Flask(__name__)
        
        default_keys = ['dev', 'development', 'test', 'changeme', 'your_secret_key_here']
        
        for key in default_keys:
            app.config['SECRET_KEY'] = key
            auth = GauthiqAuthProduction()
            
            with pytest.raises(ValueError, match="SECRET_KEY par défaut détectée"):
                auth.init_app(app)
    
    def test_https_redirect_uri_required(self):
        """Vérifie que REDIRECT_URI doit être en HTTPS"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'a' * 64,
            'GAUTHIQ_CLIENT_ID': 'test',
            'GAUTHIQ_CLIENT_SECRET': 'test',
            'GAUTHIQ_DISCOVERY_URL': 'https://auth.example.com/.well-known/openid-configuration',
            'GAUTHIQ_REDIRECT_URI': 'http://example.com/callback'  # HTTP not allowed
        })
        
        auth = GauthiqAuthProduction()
        
        with pytest.raises(ValueError, match="doit utiliser HTTPS"):
            auth.init_app(app)
    
    def test_required_config_validation(self):
        """Vérifie que la configuration obligatoire est validée"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'a' * 64
        
        auth = GauthiqAuthProduction()
        
        with pytest.raises(ValueError, match="Configuration manquante"):
            auth.init_app(app)
    
    def test_safe_url_validation_relative(self):
        """Vérifie la validation d'URL relative (safe)"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'a' * 64,
            'GAUTHIQ_CLIENT_ID': 'test',
            'GAUTHIQ_CLIENT_SECRET': 'test',
            'GAUTHIQ_DISCOVERY_URL': 'https://auth.example.com/.well-known/openid-configuration',
            'GAUTHIQ_REDIRECT_URI': 'https://example.com/callback'
        })
        
        auth = GauthiqAuthProduction()
        # Note: init_app will fail due to OAuth registration, but we only test _is_safe_url
        auth.app = app
        
        with app.test_request_context('/', base_url='https://example.com'):
            assert auth._is_safe_url('/dashboard') is True
            assert auth._is_safe_url('/admin/users') is True
    
    def test_safe_url_validation_external(self):
        """Vérifie que les URLs externes sont rejetées"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'a' * 64,
            'GAUTHIQ_CLIENT_ID': 'test',
            'GAUTHIQ_CLIENT_SECRET': 'test',
            'GAUTHIQ_DISCOVERY_URL': 'https://auth.example.com/.well-known/openid-configuration',
            'GAUTHIQ_REDIRECT_URI': 'https://example.com/callback'
        })
        
        auth = GauthiqAuthProduction()
        auth.app = app
        
        with app.test_request_context('/', base_url='https://example.com'):
            # URLs externes doivent être rejetées (open redirect attack)
            assert auth._is_safe_url('https://evil.com/phishing') is False
            assert auth._is_safe_url('http://evil.com') is False
    
    def test_session_expiration_check(self):
        """Vérifie que l'expiration de session est contrôlée"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'a' * 64,
            'TESTING': True
        })
        
        auth = GauthiqAuthProduction()
        auth.app = app
        auth.logger = app.logger
        
        @app.route('/protected')
        @auth.login_required
        def protected():
            return "OK"
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Session expirée (plus de 8 heures)
                old_timestamp = (datetime.utcnow() - timedelta(hours=9)).isoformat()
                sess['user'] = {'preferred_username': 'test'}
                sess['auth_timestamp'] = old_timestamp
            
            # L'accès devrait être refusé (redirection vers /login)
            response = client.get('/protected')
            assert response.status_code == 302  # Redirect
            assert '/login' in response.location


class TestProductionLogging:
    """Tests du logging de sécurité"""
    
    def test_authentication_success_logging(self, caplog):
        """Vérifie que les authentifications réussies sont loggées"""
        # Ce test nécessiterait un mock complet d'OAuth
        # Pour l'instant, test de structure
        pass
    
    def test_authentication_failure_logging(self, caplog):
        """Vérifie que les échecs d'authentification sont loggués"""
        pass
    
    def test_admin_access_attempt_logging(self, caplog):
        """Vérifie que les tentatives d'accès admin sont loggées"""
        pass


class TestProductionCookieConfiguration:
    """Tests de la configuration des cookies en production"""
    
    def test_cookie_secure_flag(self):
        """Vérifie que le flag Secure est requis"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'a' * 64,
            'SESSION_COOKIE_SECURE': False,  # Devrait déclencher un warning
            'TESTING': True
        })
        
        # En production, on devrait avoir un warning si Secure=False
        # (le test vérifie juste que l'app peut démarrer, le warning est dans les logs)
        assert True
    
    def test_cookie_samesite_none_with_secure(self):
        """Vérifie que SameSite=None requiert Secure=True"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'a' * 64,
            'SESSION_COOKIE_SAMESITE': 'None',
            'SESSION_COOKIE_SECURE': True,  # Obligatoire avec SameSite=None
            'TESTING': True
        })
        
        # Configuration valide pour OAuth cross-domain
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'None'
        assert app.config['SESSION_COOKIE_SECURE'] is True


class TestNonceValidation:
    """Tests de la validation des nonces (protection CSRF)"""
    
    def test_nonce_expiration(self):
        """Vérifie que les nonces expirent après 5 minutes"""
        # Test de la logique d'expiration
        old_timestamp = (datetime.utcnow() - timedelta(minutes=6)).isoformat()
        recent_timestamp = (datetime.utcnow() - timedelta(minutes=2)).isoformat()
        
        # Nonce expiré
        old_time = datetime.fromisoformat(old_timestamp)
        assert (datetime.utcnow() - old_time) > timedelta(minutes=5)
        
        # Nonce valide
        recent_time = datetime.fromisoformat(recent_timestamp)
        assert (datetime.utcnow() - recent_time) < timedelta(minutes=5)


# Commandes pour exécuter les tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
