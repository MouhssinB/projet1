#!/usr/bin/env python3
"""
Script de test de la configuration Azure Speech
À exécuter dans Azure Web App pour diagnostiquer l'erreur HTTP 400
"""
import os
import requests
import sys

def test_speech_config():
    """Teste la configuration Azure Speech et la génération de token"""
    
    print("=" * 60)
    print("DIAGNOSTIC AZURE SPEECH - ERREUR HTTP 400")
    print("=" * 60)
    
    # 1. Vérifier les variables d'environnement
    print("\n📋 ÉTAPE 1: Vérification des variables d'environnement")
    print("-" * 60)
    
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SERVICE_REGION")
    speech_endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")
    
    print(f"AZURE_SPEECH_KEY: {'✅ Définie' if speech_key else '❌ MANQUANTE'}")
    if speech_key:
        print(f"  - Longueur: {len(speech_key)} caractères")
        print(f"  - Début: {speech_key[:3]}...")
        print(f"  - Fin: ...{speech_key[-3:]}")
    
    print(f"AZURE_SERVICE_REGION: {'✅ ' + service_region if service_region else '❌ MANQUANTE'}")
    print(f"AZURE_SPEECH_ENDPOINT: {'✅ ' + speech_endpoint if speech_endpoint else '❌ MANQUANTE'}")
    
    if not speech_key or not service_region:
        print("\n❌ ERREUR: Variables d'environnement manquantes!")
        return False
    
    # 2. Construire les URLs de test
    print("\n🔗 ÉTAPE 2: URLs de test")
    print("-" * 60)
    
    urls_to_test = []
    
    if speech_endpoint:
        endpoint_base = speech_endpoint.rstrip('/')
        url_endpoint = f"{endpoint_base}/sts/v1.0/issueToken"
        urls_to_test.append(("Endpoint configuré", url_endpoint))
        print(f"URL depuis endpoint: {url_endpoint}")
    
    url_region = f"https://{service_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    urls_to_test.append(("URL région", url_region))
    print(f"URL depuis région: {url_region}")
    
    # 3. Tester chaque URL
    print("\n🧪 ÉTAPE 3: Test des requêtes")
    print("-" * 60)
    
    headers = {
        'Ocp-Apim-Subscription-Key': speech_key,
        'Content-Length': '0'
    }
    
    success = False
    for name, url in urls_to_test:
        print(f"\n📡 Test: {name}")
        print(f"   URL: {url}")
        
        try:
            response = requests.post(url, headers=headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                token = response.text
                print(f"   ✅ SUCCÈS!")
                print(f"   Token reçu (début): {token[:20]}...")
                print(f"   Token longueur: {len(token)} caractères")
                success = True
                break
            else:
                print(f"   ❌ ÉCHEC: HTTP {response.status_code}")
                print(f"   Response body: {response.text}")
                print(f"   Response headers: {dict(response.headers)}")
                
                # Analyser les erreurs courantes
                if response.status_code == 400:
                    print("\n   💡 ANALYSE ERREUR 400:")
                    if "InvalidSubscriptionKey" in response.text or "Access denied" in response.text:
                        print("      → La clé API est invalide ou expirée")
                        print("      → Vérifiez que AZURE_SPEECH_KEY correspond à votre ressource Speech")
                    elif "Resource not found" in response.text:
                        print("      → L'endpoint ou la région est incorrecte")
                        print("      → Vérifiez que la région et l'endpoint correspondent à votre ressource")
                    else:
                        print(f"      → Erreur: {response.text}")
                
                elif response.status_code == 401:
                    print("\n   💡 ANALYSE ERREUR 401:")
                    print("      → Authentification échouée")
                    print("      → La clé API est probablement incorrecte")
                
                elif response.status_code == 403:
                    print("\n   💡 ANALYSE ERREUR 403:")
                    print("      → Accès refusé")
                    print("      → Vérifiez les permissions de la clé API")
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ ERREUR RÉSEAU: {str(e)}")
    
    # 4. Recommandations
    print("\n" + "=" * 60)
    if success:
        print("✅ CONFIGURATION VALIDE - Le token a été généré avec succès")
    else:
        print("❌ CONFIGURATION INVALIDE - Recommandations:")
        print("-" * 60)
        print("1. Vérifiez dans le portail Azure:")
        print("   - Allez sur votre ressource Azure Speech")
        print("   - Copiez la clé depuis 'Keys and Endpoint'")
        print("   - Vérifiez que la région correspond (ex: westeurope)")
        print("   - Notez l'endpoint complet")
        print("\n2. Dans Azure Web App Configuration:")
        print("   - AZURE_SPEECH_KEY doit correspondre exactement")
        print("   - AZURE_SERVICE_REGION doit être le nom de région (ex: westeurope)")
        print("   - AZURE_SPEECH_ENDPOINT doit être l'URL complète")
        print("\n3. Redémarrez l'application après modification")
    
    print("=" * 60)
    return success

if __name__ == "__main__":
    try:
        success = test_speech_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
