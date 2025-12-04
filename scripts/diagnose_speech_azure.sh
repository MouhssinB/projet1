#!/bin/bash

# Script de diagnostic pour problème Azure Speech DNS
# Usage: ./diagnose_speech_azure.sh

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                              ║"
echo "║         🔍 DIAGNOSTIC AZURE SPEECH - PROBLÈME DNS                            ║"
echo "║                                                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables d'environnement
SPEECH_ENDPOINT="${AZURE_SPEECH_ENDPOINT:-}"
SPEECH_KEY="${AZURE_SPEECH_KEY:-}"
SPEECH_REGION="${AZURE_SERVICE_REGION:-westeurope}"

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "📋 CONFIGURATION"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

if [ -z "$SPEECH_KEY" ]; then
    echo -e "${RED}❌ AZURE_SPEECH_KEY non définie${NC}"
else
    echo -e "${GREEN}✅ AZURE_SPEECH_KEY définie${NC} (${#SPEECH_KEY} caractères)"
fi

if [ -z "$SPEECH_ENDPOINT" ]; then
    echo -e "${YELLOW}⚠️  AZURE_SPEECH_ENDPOINT non définie (utilisation de la région)${NC}"
else
    echo -e "${GREEN}✅ AZURE_SPEECH_ENDPOINT définie${NC}: $SPEECH_ENDPOINT"
fi

echo -e "${GREEN}ℹ️  AZURE_SERVICE_REGION${NC}: $SPEECH_REGION"
echo ""

# Test DNS
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🔍 TEST DNS"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

DNS_HOSTS=(
    "$SPEECH_REGION.api.cognitive.microsoft.com"
    "$SPEECH_REGION.cognitiveservices.azure.com"
)

if [ -n "$SPEECH_ENDPOINT" ]; then
    # Extraire le host de l'endpoint
    ENDPOINT_HOST=$(echo "$SPEECH_ENDPOINT" | sed -E 's|https?://([^/]+).*|\1|')
    DNS_HOSTS+=("$ENDPOINT_HOST")
fi

for host in "${DNS_HOSTS[@]}"; do
    echo "Test DNS pour: $host"
    if nslookup "$host" > /dev/null 2>&1; then
        IP=$(nslookup "$host" | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
        echo -e "${GREEN}✅ Résolu${NC}: $IP"
    else
        echo -e "${RED}❌ ÉCHEC - DNS ne résout pas${NC}"
    fi
    echo ""
done

# Test Connectivité
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🌐 TEST CONNECTIVITÉ"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

if [ -n "$SPEECH_ENDPOINT" ]; then
    TOKEN_URL="$SPEECH_ENDPOINT/sts/v1.0/issueToken"
else
    TOKEN_URL="https://$SPEECH_REGION.api.cognitive.microsoft.com/sts/v1.0/issueToken"
fi

echo "URL du token: $TOKEN_URL"
echo ""

if [ -z "$SPEECH_KEY" ]; then
    echo -e "${YELLOW}⚠️  Impossible de tester sans AZURE_SPEECH_KEY${NC}"
else
    echo "Test de connexion..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$TOKEN_URL" \
        -H "Ocp-Apim-Subscription-Key: $SPEECH_KEY" \
        --connect-timeout 10 \
        --max-time 30 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ SUCCÈS${NC} - Token obtenu (HTTP $HTTP_CODE)"
    elif [ "$HTTP_CODE" = "000" ]; then
        echo -e "${RED}❌ ÉCHEC${NC} - Impossible de se connecter (timeout ou erreur réseau)"
    elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
        echo -e "${YELLOW}⚠️  Connexion OK mais clé invalide${NC} (HTTP $HTTP_CODE)"
    else
        echo -e "${YELLOW}⚠️  Réponse HTTP inattendue${NC}: $HTTP_CODE"
    fi
fi
echo ""

# Test Réseau
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🔌 TEST RÉSEAU"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

if command -v ping &> /dev/null; then
    echo "Test PING..."
    if ping -c 3 "$SPEECH_REGION.api.cognitive.microsoft.com" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Ping réussi${NC}"
    else
        echo -e "${YELLOW}⚠️  Ping échoué (peut être normal si ICMP bloqué)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Commande ping non disponible${NC}"
fi
echo ""

if command -v traceroute &> /dev/null; then
    echo "Test TRACEROUTE (3 hops max)..."
    traceroute -m 3 "$SPEECH_REGION.api.cognitive.microsoft.com" 2>/dev/null || \
        echo -e "${YELLOW}⚠️  Traceroute non disponible ou échoué${NC}"
else
    echo -e "${YELLOW}⚠️  Commande traceroute non disponible${NC}"
fi
echo ""

# Recommandations
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "💡 RECOMMANDATIONS"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

if [ -z "$SPEECH_ENDPOINT" ]; then
    echo -e "${YELLOW}1.${NC} Définir AZURE_SPEECH_ENDPOINT avec l'URL complète:"
    echo "   export AZURE_SPEECH_ENDPOINT=https://votre-ressource.cognitiveservices.azure.com"
    echo ""
fi

if [ -z "$SPEECH_KEY" ]; then
    echo -e "${YELLOW}2.${NC} Définir AZURE_SPEECH_KEY:"
    echo "   export AZURE_SPEECH_KEY=votre_clé_api"
    echo ""
fi

echo -e "${GREEN}3.${NC} Redémarrer l'application après modification des variables"
echo ""

echo -e "${GREEN}4.${NC} Vérifier les logs de l'application:"
echo "   tail -f log/application.log | grep -i speech"
echo ""

echo -e "${GREEN}5.${NC} Si problème persiste, vérifier:"
echo "   - Restrictions réseau (NSG, Firewall)"
echo "   - Configuration VNet Integration"
echo "   - DNS personnalisé"
echo ""

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "✅ Diagnostic terminé"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Pour plus d'informations, consulter: RESOLUTION_DNS_AZURE.md"
echo ""
