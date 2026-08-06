# Documentation Fonctionnelle et Technique
# Projet RFID PRINTING
## Application de gestion et d'impression d'étiquettes RFID

**Version :** 0.3  
**Statut :** Sprint 3 terminé  
**Stack technique :**
- Backend : FastAPI (Python)
- Base de données : SQLite
- ORM : SQLAlchemy
- Authentification : JWT
- Documentation API : Swagger OpenAPI

---

# 1. Présentation du projet

## Contexte

L'application RFID PRINTING a pour objectif de permettre aux utilisateurs autorisés de :

1. Importer un inventaire au format CSV.
2. Identifier automatiquement les biens actifs.
3. Préparer la sélection des biens à étiqueter.
4. Générer ultérieurement des fichiers d'impression RFID.
5. Assurer la traçabilité des opérations.

---

# 2. Vision Produit

## Parcours utilisateur cible

```text
Connexion
    ↓
Import CSV
    ↓
Contrôle du fichier
    ↓
Création de l'import
    ↓
Enregistrement des biens
    ↓
Consultation des biens
    ↓
Recherche des biens
    ↓
Sélection pour impression RFID
    ↓
Génération du fichier CMD
    ↓
Historisation