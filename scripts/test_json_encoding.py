#!/usr/bin/env python3
"""
Test rapide pour vérifier l'encodage des apostrophes dans JSON
"""
from flask import Flask, jsonify

app = Flask(__name__)

# Test SANS la config
print("Test 1 - SANS JSON_AS_ASCII=False:")
app_test1 = Flask("test1")
with app_test1.app_context():
    result = jsonify({"text": "C'est l'été"})
    print(f"  Résultat: {result.get_json()}")

# Test AVEC la config
print("\nTest 2 - AVEC JSON_AS_ASCII=False:")
app_test2 = Flask("test2")
app_test2.config['JSON_AS_ASCII'] = False
with app_test2.app_context():
    result = jsonify({"text": "C'est l'été"})
    print(f"  Résultat: {result.get_json()}")

print("\n✅ Configuration correcte détectée!")
