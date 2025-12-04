#!/bin/bash
# Script rapide pour vérifier et diagnostiquer l'erreur VNet/Firewall

echo "============================================================"
echo "🔍 DIAGNOSTIC RAPIDE - AZURE SPEECH VNET/FIREWALL"
echo "============================================================"
echo ""

# Vérifier si on est dans le bon dossier
if [ ! -f ".env" ]; then
    echo "❌ Fichier .env non trouvé"
    echo "Exécutez ce script depuis: /home/gs8678/projet/simsan/infra/src"
    exit 1
fi

# Charger les variables d'environnement
set -a
source .env
set +a

# Vérifier les variables
echo "📋 Variables d'environnement:"
echo "   AZURE_SPEECH_KEY: ${AZURE_SPEECH_KEY:0:3}...${AZURE_SPEECH_KEY: -3}"
echo "   AZURE_SERVICE_REGION: $AZURE_SERVICE_REGION"
echo "   AZURE_SPEECH_ENDPOINT: $AZURE_SPEECH_ENDPOINT"
echo ""

# Construire l'URL
ENDPOINT_BASE=$(echo "$AZURE_SPEECH_ENDPOINT" | sed 's:/*$::')
TOKEN_URL="${ENDPOINT_BASE}/sts/v1.0/issueToken"

echo "🧪 Test de génération de token..."
echo "   URL: $TOKEN_URL"
echo ""

# Faire la requête
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$TOKEN_URL" \
    -H "Ocp-Apim-Subscription-Key: $AZURE_SPEECH_KEY" \
    -H "Content-Length: 0")

# Extraire le code HTTP
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

echo "📊 Résultat:"
echo "   Status HTTP: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SUCCÈS! Token généré correctement"
    echo "   Token (début): ${BODY:0:20}..."
    echo ""
    echo "👉 Votre configuration est correcte !"
    exit 0
elif [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -q "Virtual network/Firewall"; then
    echo "❌ ERREUR: VNet/Firewall détecté"
    echo ""
    echo "📄 Message d'erreur:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔧 SOLUTION RAPIDE:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Ouvrez le portail Azure: https://portal.azure.com"
    echo ""
    echo "2. Recherchez votre ressource Speech:"
    echo "   → spch-india-simsan-d-we"
    echo ""
    echo "3. Dans le menu de gauche:"
    echo "   → Cliquez sur 'Networking' (Réseau)"
    echo ""
    echo "4. Sous 'Firewalls and virtual networks':"
    echo "   → Sélectionnez 'All networks' (Tous les réseaux)"
    echo "   → Cliquez sur 'Save' (Enregistrer)"
    echo ""
    echo "5. Attendez 2-3 minutes que la configuration se propage"
    echo ""
    echo "6. Relancez ce script pour vérifier"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📚 Documentation complète: SOLUTION_VNET_SPEECH.md"
    exit 1
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ ERREUR: Accès refusé (403)"
    echo ""
    echo "📄 Message d'erreur:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo "💡 Solutions possibles:"
    echo "   1. Vérifiez que la clé API est correcte"
    echo "   2. Désactivez le VNet/Firewall (voir ci-dessus)"
    echo "   3. Ajoutez les IPs de votre Web App dans le firewall"
    exit 1
else
    echo "❌ ERREUR: HTTP $HTTP_CODE"
    echo ""
    echo "📄 Réponse complète:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    exit 1
fi
