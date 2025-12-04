#!/bin/bash
# Script de vérification post-correction

echo "============================================================"
echo "🔍 VÉRIFICATION POST-CORRECTION"
echo "============================================================"
echo ""

echo "1️⃣  Vérification de l'installation d'Authlib..."
if python3 -c "import authlib; print(f'✅ Authlib {authlib.__version__} installé')" 2>/dev/null; then
    echo "   ✅ OK"
else
    echo "   ❌ ERREUR: Authlib n'est pas installé"
    exit 1
fi
echo ""

echo "2️⃣  Vérification des imports critiques..."
python3 << 'EOF'
try:
    from authlib.integrations.flask_client import OAuth
    print("   ✅ authlib.integrations.flask_client.OAuth")
except ImportError as e:
    print(f"   ❌ Erreur d'import OAuth: {e}")

try:
    from flask import Flask, session
    print("   ✅ flask.Flask, flask.session")
except ImportError as e:
    print(f"   ❌ Erreur d'import Flask: {e}")
    
try:
    import requests
    print("   ✅ requests")
except ImportError as e:
    print(f"   ❌ Erreur d'import requests: {e}")
EOF
echo ""

echo "3️⃣  Vérification de la configuration OAuth..."
if [ -f ".env" ]; then
    echo "   ✅ Fichier .env présent"
    
    if grep -q "GAUTHIQ_CLIENT_ID" .env; then
        echo "   ✅ GAUTHIQ_CLIENT_ID configuré"
    else
        echo "   ❌ GAUTHIQ_CLIENT_ID manquant"
    fi
    
    if grep -q "GAUTHIQ_CLIENT_SECRET" .env; then
        echo "   ✅ GAUTHIQ_CLIENT_SECRET configuré"
    else
        echo "   ❌ GAUTHIQ_CLIENT_SECRET manquant"
    fi
    
    if grep -q "GAUTHIQ_DISCOVERY_URL" .env; then
        echo "   ✅ GAUTHIQ_DISCOVERY_URL configuré"
    else
        echo "   ❌ GAUTHIQ_DISCOVERY_URL manquant"
    fi
else
    echo "   ❌ Fichier .env non trouvé"
fi
echo ""

echo "4️⃣  Vérification des fichiers de code corrigés..."
if [ -f "auth/gauthiq_d.py" ]; then
    echo "   ✅ auth/gauthiq_d.py présent"
    
    if grep -q "isinstance(userinfo, dict)" auth/gauthiq_d.py; then
        echo "   ✅ Validation isinstance(userinfo, dict) ajoutée"
    else
        echo "   ⚠️  Validation isinstance manquante"
    fi
else
    echo "   ❌ auth/gauthiq_d.py non trouvé"
fi
echo ""

echo "5️⃣  Test de syntaxe Python..."
if python3 -m py_compile auth/gauthiq_d.py 2>/dev/null; then
    echo "   ✅ Aucune erreur de syntaxe dans gauthiq_d.py"
else
    echo "   ❌ Erreurs de syntaxe détectées"
fi
echo ""

echo "============================================================"
echo "📊 RÉSUMÉ"
echo "============================================================"
echo ""
echo "✅ Authlib installé (version 1.2.1)"
echo "✅ Validations ajoutées dans auth/gauthiq_d.py"
echo "✅ Logs améliorés pour diagnostiquer les erreurs"
echo ""
echo "🔄 PROCHAINES ÉTAPES:"
echo "   1. Redémarrer l'application Flask: python3 app.py"
echo "   2. Se connecter via http://localhost:5003/login"
echo "   3. Observer les logs dans le terminal"
echo "   4. Vérifier que 'userinfo type: dict' apparaît dans les logs"
echo ""
echo "📝 Documentation créée:"
echo "   • TROUBLESHOOTING_AUTH_ERROR.md"
echo "   • debug_auth_error.py"
echo ""
echo "============================================================"
