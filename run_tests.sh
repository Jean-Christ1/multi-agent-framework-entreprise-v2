#!/bin/bash
# Script pour exécuter les tests avec les variables d'environnement

# Charger les variables d'environnement depuis .env
export $(grep -v '^#' .env | xargs)

# Exécuter les tests
python -m pytest "$@"
