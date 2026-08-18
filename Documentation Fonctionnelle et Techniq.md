# Documentation Fonctionnelle et Technique
# Projet RFID PRINTING
## Application de gestion d'inventaire et d'impression d'étiquettes RFID

**Version documentaire :** 1.0
**Stack technique :** FastAPI (Python) · SQLAlchemy · Alembic · SQLite · Jinja2 (UI) · JWT

---

## Sommaire

1. [Présentation générale](#1-présentation-générale)
2. [Fonctionnalités de l'application](#2-fonctionnalités-de-lapplication)
3. [Profils utilisateurs et droits d'accès](#3-profils-utilisateurs-et-droits-daccès)
4. [Architecture technique](#4-architecture-technique)
5. [Modèle de données](#5-modèle-de-données)
6. [Référence des appels API](#6-référence-des-appels-api)
7. [Installation en mode test](#7-installation-en-mode-test)
8. [Installation en mode production sous Windows + XAMPP](#8-installation-en-mode-production-sous-windows--xampp)
9. [Exploitation et maintenance](#9-exploitation-et-maintenance)
10. [Annexes](#10-annexes)

---

## 1. Présentation générale

### 1.1 Contexte

RFID PRINTING permet aux utilisateurs autorisés de :

1. Importer l'inventaire des biens depuis un fichier CSV issu du logiciel de gestion d'inventaire.
2. Consulter, rechercher et filtrer cet inventaire.
3. Sélectionner des biens et créer des **lots d'impression**.
4. Générer, à partir d'un lot, un **fichier de commande (.cmd)** consommé par le logiciel/matériel d'impression RFID.
5. Gérer les **fichiers bruts issus d'un lecteur RFID** (chargement, édition, export).
6. Générer des exports CSV dédiés (inventaire immatériel, alimentation d'un lecteur RFID, résultats de recherche, contenu d'un lot).
7. Assurer la traçabilité complète des opérations (imports, générations, réimpressions).
8. Gérer les comptes utilisateurs et leurs profils d'habilitation.

### 1.2 Stack technique

| Composant | Choix |
|---|---|
| Langage / Framework backend | Python 3.11+ / FastAPI |
| Serveur d'application | Uvicorn (ASGI) |
| Base de données | SQLite (fichier `rfid.db`) |
| ORM / migrations | SQLAlchemy 2.x / Alembic |
| Interface utilisateur | Jinja2 (rendu serveur) + Bootstrap 4 (thème SB Admin 2) |
| Authentification UI | Cookie de session (JWT signé, HttpOnly) |
| Authentification API | JWT porté en en-tête `Authorization: Bearer <token>` |
| Génération de fichiers | Module Python interne (gabarits à placeholders) |

L'UI est **entièrement rendue côté serveur** (pas de framework JS / pas de build Node) : cela évite toute dépendance à npm/Node, incompatible avec le proxy d'entreprise de l'exploitant.

---

## 2. Fonctionnalités de l'application

### 2.1 Authentification

- Connexion par identifiant/mot de passe (`/login`), mot de passe stocké hashé (bcrypt via `passlib`).
- Session UI : cookie `access_token` (JWT, HttpOnly, `SameSite=Lax`), durée de vie **60 minutes**.
- API : jeton JWT obtenu via `POST /auth/login`, à transmettre en `Authorization: Bearer`.
- Après connexion, redirection automatique adaptée au profil (voir §3) : `/dashboard` pour administrateur/gestionnaire, `/assets` (Inventaire) pour le profil lecteur.

### 2.2 Tableau de bord (`/dashboard`)

- Compteurs : nombre d'imports, de biens actifs, de lots, d'entrées d'historique.
- Panneau **« Zone sensible »** (administrateur uniquement) : réinitialisation complète de la base de données métier (biens, imports, lots, historique — les comptes utilisateurs sont conservés). Action irréversible, confirmation JavaScript obligatoire.

### 2.3 Import de l'inventaire (`/import`)

- Chargement d'un fichier CSV issu du logiciel de gestion d'inventaire.
- **Détection automatique du séparateur** : `;` puis `,` en repli.
- **Mappage des colonnes obligatoires** :

  | Colonne source | Champ interne | Règle |
  |---|---|---|
  | `numero` | Bien ID | Identifiant du bien (obligatoire) |
  | `libelle` | Désignation | Libellé du bien (obligatoire) |
  | `sortie` | Date de sortie | Vide ⇒ bien **actif** ; renseignée ⇒ bien **exclu** |

- **Colonnes optionnelles** (utilisées si présentes dans le fichier, sans faire échouer l'import si absentes) : `local_numero`, `immeuble_libelle`, `niveau_libelle`, `local_libelle`.
- Les autres colonnes du fichier sont ignorées.
- **Import incrémental** : seuls les biens dont le Bien ID est absent de la base sont ajoutés ; les biens déjà présents sont comptabilisés (« déjà existants ») mais non réimportés/écrasés.
- Aperçu Ajax avant import définitif (colonnes détectées, compteurs) via `POST /import/preview`.
- Résumé après import : total de lignes, actifs, exclus, lignes invalides (Bien ID ou désignation manquants), doublons déjà en base.

### 2.4 Inventaire (`/assets`)

- Tableau paginé de tous les biens, avec :
  - Recherche texte sur la désignation.
  - Filtre « actifs uniquement ».
  - Filtre par **plage de Bien ID** (numérique, ex. de `20260001` à `20260020`).
  - Filtres par **immeuble**, **niveau**, **local** (listes déroulantes alimentées par les valeurs distinctes présentes en base).
  - Choix du nombre de lignes affichées par page (10 / 25 / 50).
- **Sélection multiple** de biens (case à cocher par ligne + case « tout sélectionner » sur la page courante), **persistante entre les pages** (stockée côté navigateur, `localStorage`) et entre les recherches.
- Affichage, à droite du titre, de la **date/heure et de l'utilisateur de la dernière importation**.
- Actions sur la sélection :
  - **Créer un lot d'impression** (`POST /jobs/create`) à partir des biens cochés.
  - **Inventaire immatériel** (`POST /assets/export-immateriel`) : génère un CSV (`;`, sans en-tête, 2 colonnes) à partir des biens cochés — colonne 1 = `L261` + numéro local, colonne 2 = `261` + Bien ID (biens sans numéro local ignorés). Même format que les fichiers de lecteur RFID (§2.6).
- Actions indépendantes de la sélection :
  - **Export lecteur RFID** (`GET /assets/export-rfid-reader`) : CSV (`;`, sans en-tête) de **tous les biens actifs**, colonnes Bien ID + désignation, destiné à alimenter le lecteur RFID.
  - **Exporter le résultat en CSV** (`GET /assets/export-csv`, en bas du tableau) : CSV (`;`, avec en-tête) de **l'intégralité** des biens correspondant aux critères de recherche courants (pas seulement la page affichée). Colonnes : Bien ID, Désignation, Numéro local, Immeuble, Niveau, Local, Actif.
- Pour le profil **lecteur**, les boutons « Export lecteur RFID », « Inventaire immatériel » et « Créer un lot d'impression » sont désactivés à l'écran **et** refusés côté serveur (403) s'ils sont sollicités directement.

### 2.5 Lots d'impression (`/jobs`)

- Liste des lots, recherche par Bien ID (retrouve les lots contenant un bien donné) via `GET /jobs/search`.
- Détail d'un lot (`/jobs/{id}`) : statut, nombre d'étiquettes, créateur, liste des biens associés.
- **Génération du fichier .cmd** (`POST /jobs/{id}/generate`) à partir du gabarit courant (§2.7) : un lot ne peut être généré qu'une seule fois (sinon utiliser la réimpression via l'API, `POST /api/print/jobs/{id}/reprint`) ; un lot vide ne peut pas être généré.
- **Export du tableau du lot** :
  - **Exporter en PDF** : bouton déclenchant l'impression navigateur (`window.print()`) sur une mise en page dédiée (menu, boutons et bannières masqués via une feuille de style `@media print`) — l'utilisateur choisit « Enregistrer au format PDF » dans la boîte de dialogue d'impression.
  - **Exporter en CSV** (`GET /jobs/{id}/export-csv`) : CSV (`;`, avec en-tête Bien ID/Désignation) de la liste des biens du lot.

### 2.6 Fichiers RFID (`/rfid-scans`)

Gestion des fichiers CSV bruts **issus d'un lecteur RFID physique** : 2 colonnes, **sans en-tête**, séparateur `;` :

- Colonne 1 : `L261` + numéro de lieu (8 chiffres), ex. `L26100000001`.
- Colonne 2 : `261` + Bien ID (8 chiffres), ex. `26120260001`.

Fonctions :

- **Chargement** d'un fichier (`POST /rfid-scans`) : les lignes valides sont enregistrées en base ; les lignes dont un des deux préfixes est absent sont ignorées et comptabilisées (l'import du reste n'échoue pas). Une même étiquette relue plusieurs fois dans un seul fichier ne produit qu'une seule ligne (dernière lecture retenue).
- **Jamais de doublon de Bien ID** : un Bien ID déjà présent en base (chargé via un fichier précédent, quel qu'il soit) est **mis à jour** avec son nouveau numéro de lieu — au lieu d'être dupliqué — et rattaché au fichier qui vient de le fournir. Le compte-rendu après chargement indique le nombre de biens ajoutés et mis à jour.
- **Édition** des lignes d'un fichier chargé (`/rfid-scans/{id}`) : ajout, modification, suppression de lignes individuelles ; l'ajout ou la modification d'une ligne vers un Bien ID déjà utilisé par une autre ligne est refusé.
- **Export horodaté** (`GET /rfid-scans/{id}/export`) : reconstruit le CSV 2 colonnes/`;`/sans en-tête à partir des lignes (éditées ou non), nom de fichier `export_rfid_AAAAMMJJ_HHMMSS.csv`.

### 2.7 Mise à jour des codes lieux (`/glpi-locations`, administrateur uniquement)

Compare le **numéro local** enregistré dans l'inventaire avec le **numéro de la pièce** connu dans **GLPI**, pour détecter et corriger les écarts.

- **Import GLPI** (`POST /glpi-locations`) : un fichier CSV par type de bien (`;`, avec en-tête) — **ordinateur, moniteur, périphérique, logiciel, imprimante**. Colonnes exploitées :

  | Colonne GLPI | Usage |
  |---|---|
  | `Numéro d'inventaire` | Bien ID (clé de rapprochement avec l'inventaire) |
  | `Numéro de la pièce` | Comparé au `local_numero` de l'inventaire |
  | `Lieu` | Affichage uniquement (informatif) |
  | `Statut` | Affichage uniquement (informatif) |

  Toutes les autres colonnes du fichier sont ignorées ; `Lieu`/`Statut` n'entrent pas dans la comparaison et restent vides s'ils sont absents du fichier. Le numéro de la pièce fait toujours 8 caractères dans l'inventaire (ex. `00600001`) ; GLPI l'exporte parfois sans les zéros non significatifs (ex. `600001`) — il est donc **complété à gauche par des zéros** à l'import (`600001` → `00600001`, `1101043` → `01101043`). **Jamais de doublon** : si le Bien ID existe déjà (import précédent, même ou autre type), ses informations sont **mises à jour** ; sinon une nouvelle ligne est créée. Un fichier contenant plusieurs fois le même Bien ID est rejeté (import à corriger).
- **Tableau des écarts** : liste les biens présents à la fois dans l'inventaire et dans un import GLPI dont le numéro local diffère du numéro de la pièce GLPI, avec Bien ID, désignation, numéro local actuel (survolé, une infobulle affiche la désignation du local), statut actif/exclu, lieu GLPI, numéro de la pièce GLPI et statut GLPI.
  - **Filtre Actif** : trois boutons dans l'en-tête de la colonne « Actif » — « Tous » (`?active_filter=tous`, défaut), « Actif » (`?active_filter=actif`, uniquement les biens actifs) et « Exclu » (`?active_filter=exclu`, uniquement les biens exclus).
  - **Filtre texte** sur « Numéro de la pièce (GLPI) » et « Statut (GLPI) » (recherche insensible à la casse, sous-chaîne), via un formulaire au-dessus du tableau (`GET /glpi-locations?numero_piece=...&statut=...`), avec un lien « Réinitialiser les filtres ».
  - **Tri** : cliquer sur l'en-tête « Numéro de la pièce (GLPI) » ou « Statut (GLPI) » trie le tableau par cette colonne (`?sort=numero_piece` ou `?sort=statut`), un second clic inverse le sens (`&dir=desc`). Par défaut, tri par Bien ID croissant.
  - Ces filtres et ce tri se combinent et restent actifs lors de la navigation (chaque lien conserve les autres paramètres en cours).
- **Sélection multiple** des lignes (case à cocher par ligne + « tout sélectionner »). Le nombre de lignes sélectionnées sur le nombre total s'affiche à côté du titre du tableau (ex. « 2 / 5 sélectionné(s) »).
- **Correction** : chaque ligne propose une liste déroulante des lieux connus dans l'inventaire, affichant à la fois le **numéro local et sa désignation** (ex. `01100021 - 021-ENTREPOT`), présélectionnée sur le lieu actuel du bien ; le choix détermine le numéro local correspondant. Modifier cette liste déroulante coche automatiquement la ligne correspondante.
- **Génération d'un fichier CSV**, deux formats au choix, à partir des lignes cochées et du numéro local corrigé (ou l'actuel si la liste déroulante n'a pas été changée) :
  - **Générer un fichier CSV** (`POST /glpi-locations/export-csv`, `;`, en-tête `Bien ID;Numéro local`).
  - **Générer un fichier CSV (avec colonnes de lieu)** (`POST /glpi-locations/export-csv-complet`, `;`, en-tête `Bien ID;Numéro local;Immeuble;Niveau;Local`) : ajoute les colonnes immeuble/niveau/local correspondant au numéro local retenu (celui du lieu corrigé, pas celui — potentiellement obsolète — du bien).

  Destinés à la mise à jour du logiciel de gestion d'inventaire.
- **Vider la table des données GLPI** (`POST /glpi-locations/reset`, zone sensible) : supprime définitivement tous les imports et biens GLPI chargés (les 5 types). N'affecte pas l'inventaire ni les autres données de l'application. Action irréversible, confirmation JavaScript obligatoire.

### 2.8 Modèle du fichier CMD (`/settings/cmd-template`, administrateur uniquement)

- Gabarit **d'en-tête** (une fois par lot) et **de ligne** (répétée par bien), avec substitution de placeholders `{{Placeholder}}` :

  | Placeholder | Portée | Valeur |
  |---|---|---|
  | `{{JobId}}` | En-tête | Identifiant du lot |
  | `{{BienId}}` | Ligne | Bien ID |
  | `{{Designation}}` | Ligne | Désignation du bien |
  | `{{DateSortie}}` | Ligne | Date de sortie |
  | `{{Statut}}` | Ligne | `Actif` / `Exclu` |
  | `{{NumeroLocal}}` | Ligne | Numéro local |
  | `{{Immeuble}}` | Ligne | Libellé immeuble |
  | `{{Niveau}}` | Ligne | Libellé niveau |
  | `{{Local}}` | Ligne | Libellé local |

- Un placeholder inconnu (faute de frappe) est laissé tel quel dans le fichier généré, pour rester visible plutôt que de disparaître silencieusement.
- Aperçu en direct (`POST /settings/cmd-template/preview`) avec un bien réel de la base si disponible, sinon un bien fictif d'exemple.
- Le gabarit actif est toujours **le dernier enregistré** (historique conservé en base, une ligne par modification).

### 2.9 Historique (`/history`)

- Journal de toutes les générations (`GENERATED`) et réimpressions (`REPRINTED`) de fichiers `.cmd`, avec utilisateur, date, nombre d'étiquettes.

### 2.10 Gestion des utilisateurs et profils (`/admin/users`, administrateur uniquement)

- Liste des comptes existants.
- Création de compte (identifiant, mot de passe ≥ 8 caractères, profil).
- Changement de profil d'un compte existant.
- Réinitialisation du mot de passe d'un compte.
- Suppression d'un compte.
- Garde-fous : impossible de supprimer son propre compte, impossible de supprimer/rétrograder le **dernier administrateur restant** (empêche de couper l'accès à la gestion des utilisateurs).

---

## 3. Profils utilisateurs et droits d'accès

Trois profils (champ `role` de la table `users`) :

| Profil | Description |
|---|---|
| `administrateur` | Toutes les fonctions, y compris le modèle CMD, la gestion des utilisateurs/profils et la réinitialisation de la base. |
| `gestionnaire` | Usage courant : import, inventaire, lots, historique, fichiers RFID. **Sans** le modèle CMD, la mise à jour des codes lieux (GLPI), la gestion des utilisateurs, ni la réinitialisation de la base. |
| `lecteur` | Consultation de l'inventaire uniquement (`/assets`). Toute autre page renvoie une erreur 403. Les boutons d'export/création de lot y sont désactivés. |

### Matrice d'accès (pages Web)

| Page / action | administrateur | gestionnaire | lecteur |
|---|:---:|:---:|:---:|
| Tableau de bord | ✅ | ✅ | ❌ |
| Import CSV | ✅ | ✅ | ❌ |
| Inventaire (consultation) | ✅ | ✅ | ✅ |
| Export résultat de recherche (CSV) | ✅ | ✅ | ✅ |
| Créer un lot / Inventaire immatériel / Export lecteur RFID | ✅ | ✅ | ❌ |
| Lots (liste, détail, génération CMD, export PDF/CSV) | ✅ | ✅ | ❌ |
| Historique | ✅ | ✅ | ❌ |
| Fichiers RFID | ✅ | ✅ | ❌ |
| Mise à jour des codes lieux (GLPI) | ✅ | ❌ | ❌ |
| Modèle CMD | ✅ | ❌ | ❌ |
| Utilisateurs et profils | ✅ | ❌ | ❌ |
| Réinitialiser la base de données | ✅ | ❌ | ❌ |

Chaque restriction est appliquée **côté serveur** (403 explicite), l'affichage conditionnel du menu et des boutons n'étant qu'un confort d'usage, pas la seule protection.

---

## 4. Architecture technique

### 4.1 Arborescence des fichiers

```text
rfid-printing/
├── DEPLOIEMENT.md                     Guide détaillé de mise en production (Linux)
├── Documentation Fonctionnelle et Techniq.md   Ce document
├── PLAN_AMELIORATION.md               Historique du plan d'amélioration du projet
├── .gitignore
└── backend/
    ├── .env.example                   Modèle de configuration (à copier en .env)
    ├── alembic.ini                    Configuration Alembic
    ├── requirements.txt                Dépendances de production
    ├── requirements-dev.txt            Dépendances additionnelles de test (pytest, httpx)
    │
    ├── alembic/
    │   ├── env.py                     Point d'entrée des migrations (charge tous les modèles)
    │   └── versions/                  Historique des migrations (une par évolution de schéma)
    │
    ├── app/
    │   ├── main.py                    Point d'entrée FastAPI, montage des routeurs,
    │   │                               gestion centralisée des erreurs, migrations au démarrage
    │   ├── database.py                Connexion SQLAlchemy (SQLite), session
    │   ├── auth.py                    JWT, cookie de session, hachage mot de passe,
    │   │                               profils (ROLE_ADMIN/ROLE_MANAGER/ROLE_READER),
    │   │                               garde-fous require_admin()/require_manager()
    │   ├── schemas.py                  Schémas Pydantic (requêtes API)
    │   ├── seed.py                     Script de création du tout premier compte administrateur
    │   │
    │   ├── models/                    Un fichier par table (SQLAlchemy)
    │   │   ├── user_model.py              users
    │   │   ├── import_model.py            imports
    │   │   ├── asset_model.py             assets
    │   │   ├── print_job_model.py         print_jobs
    │   │   ├── print_job_line_model.py    print_job_lines
    │   │   ├── print_history_model.py     print_history
    │   │   ├── cmd_template_model.py      cmd_templates
    │   │   ├── rfid_scan_model.py         rfid_scan_files, rfid_scan_lines
    │   │   └── glpi_asset_model.py         glpi_imports, glpi_assets
    │   │
    │   ├── routers/
    │   │   ├── web_router.py          Pages Jinja2 (UI), auth cookie — la quasi-totalité
    │   │   │                           des fonctionnalités utilisateur
    │   │   ├── auth_router.py         API : /auth/login, /auth/me (JWT)
    │   │   ├── import_router.py       API : /api/import/* (import CSV, consultation biens)
    │   │   ├── print_router.py        API : /api/print/* (lots, génération, réimpression)
    │   │   ├── history_router.py      API : /api/history/*
    │   │   └── dashboard_router.py    API : /api/dashboard (statistiques)
    │   │
    │   ├── services/                  Logique métier, partagée entre API et UI
    │   │   ├── import_service.py          Lecture/validation/import du CSV inventaire
    │   │   ├── print_job_service.py       Génération du fichier .cmd d'un lot
    │   │   ├── reprint_service.py         Réimpression + historique
    │   │   ├── cmd_generator.py            Moteur de gabarits à placeholders
    │   │   ├── cmd_template_service.py    Lecture/mise à jour du gabarit courant
    │   │   ├── rfid_scan_service.py       Parsing/export des fichiers lecteur RFID
    │   │   ├── glpi_service.py             Import GLPI (5 types), rapprochement codes lieux
    │   │   └── user_service.py            CRUD utilisateurs, garde-fous last-admin
    │   │
    │   ├── templates/                 Pages Jinja2 (étendent base.html)
    │   │   ├── base.html                  Gabarit commun (menu latéral dynamique par profil)
    │   │   ├── login.html, error.html
    │   │   ├── dashboard.html
    │   │   ├── import.html
    │   │   ├── assets.html                Page Inventaire
    │   │   ├── jobs.html, job_detail.html
    │   │   ├── history.html
    │   │   ├── rfid_scans.html, rfid_scan_detail.html
    │   │   ├── glpi_locations.html         Mise à jour des codes lieux
    │   │   ├── cmd_template.html
    │   │   └── users.html                 Gestion des utilisateurs
    │   │
    │   └── static/
    │       └── css/app.css            Styles additionnels + mise en page d'impression (@media print)
    │
    ├── generated/                     Fichiers .cmd générés (créé au premier lancement, ignoré par git)
    ├── rfid.db                        Base SQLite (créée au premier lancement, ignorée par git)
    │
    └── tests/                         Suite de tests automatisés (pytest)
        ├── conftest.py                 Fixtures partagées (client de test, base de test,
        │                                utilisateurs admin_user/manager_user/standard_user)
        └── test_*.py                   ~20 fichiers de tests (API, pages Web, services)
```

### 4.2 Principe de fonctionnement

- **Deux façades d'authentification** pour une même logique métier (services partagés) :
  - **UI Jinja2** (`web_router.py`) : cookie de session HttpOnly, redirection vers `/login` si absent/expiré.
  - **API REST** (`*_router.py` sous `/api/*` et `/auth/*`) : jeton JWT en en-tête `Authorization: Bearer`.
- **Gestion des erreurs centralisée** (`main.py`) : réponse JSON pour les routes `/api/*` et `/auth/*`, page HTML (`error.html`, cohérente avec le reste de l'UI) pour toutes les autres routes.
- **Migrations appliquées automatiquement au démarrage** de l'application (`command.upgrade(alembic_cfg, "head")` dans `main.py`) : pas d'étape manuelle à oublier lors d'un déploiement.
- **Répertoire de travail obligatoire : `backend/`** — la base SQLite (`sqlite:///./rfid.db`) et les fichiers statiques (`app/static`) sont référencés en chemin relatif ; l'application (et Alembic) doivent toujours être lancés depuis ce dossier.

---

## 5. Modèle de données

| Table | Rôle | Colonnes principales |
|---|---|---|
| `users` | Comptes et profils | `id`, `username` (unique), `password_hash`, `role` |
| `imports` | Historique des imports CSV inventaire | `id`, `filename`, `imported_by`, `imported_at`, `total_rows`, `active_assets`, `excluded_assets` |
| `assets` | Biens de l'inventaire | `id`, `bien_id`, `bien_designation`, `bien_amort_date_sortie`, `local_numero`, `immeuble_libelle`, `niveau_libelle`, `local_libelle`, `is_active`, `import_id` (FK → `imports`) |
| `print_jobs` | Lots d'impression | `id`, `created_by`, `created_at`, `status` (`PENDING`/`GENERATED`), `labels_count`, `generated_file`, `generated_at` |
| `print_job_lines` | Association bien ↔ lot | `id`, `job_id` (FK), `asset_id` (FK) |
| `print_history` | Journal des générations/réimpressions | `id`, `job_id`, `username`, `action` (`GENERATED`/`REPRINTED`), `file_name`, `labels_count`, `created_at` |
| `cmd_templates` | Historique des gabarits de fichier `.cmd` | `id`, `header_template`, `line_template`, `updated_by`, `updated_at` |
| `rfid_scan_files` | Fichiers de scan RFID chargés | `id`, `filename`, `imported_by`, `imported_at` |
| `rfid_scan_lines` | Lignes d'un fichier de scan | `id`, `scan_file_id` (FK), `lieu_numero`, `bien_id` |
| `glpi_imports` | Historique des imports GLPI | `id`, `glpi_type`, `filename`, `imported_by`, `imported_at`, `total_rows`, `added_count`, `updated_count` |
| `glpi_assets` | Informations GLPI par Bien ID (unique, mises à jour à chaque import) | `id`, `bien_id` (unique), `numero_piece`, `lieu`, `statut`, `glpi_type`, `import_id` (FK → `glpi_imports`), `updated_at` |

Schéma versionné avec Alembic (`backend/alembic/versions/`) ; aucune modification manuelle du schéma ne doit être faite hors migration.

---

## 6. Référence des appels API

### 6.1 Authentification

| Méthode | Chemin | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | — | `{ "username", "password" }` → `{ "access_token", "token_type": "bearer" }` |
| `GET` | `/auth/me` | Bearer | Renvoie le contenu du jeton (`sub`, `role`, `exp`) |

### 6.2 API REST (JSON, `Authorization: Bearer <token>`)

#### Imports / inventaire — préfixe `/api/import`

| Méthode | Chemin | Description |
|---|---|---|
| `POST` | `/api/import/` | Importe un fichier CSV inventaire (`multipart/form-data`, champ `file`) |
| `GET` | `/api/import/assets-count` | Nombre total de biens |
| `GET` | `/api/import/assets` | Liste paginée des biens (`page`, `size`) |
| `GET` | `/api/import/assets/active` | Nombre de biens actifs |
| `GET` | `/api/import/assets/search` | Recherche par désignation (`q`, `page`, `size`) |

#### Impression / lots — préfixe `/api/print`

| Méthode | Chemin | Rôle requis | Description |
|---|---|---|---|
| `POST` | `/api/print/jobs` | gestionnaire+ | Crée un lot (`{ "asset_ids": [...] }`) |
| `GET` | `/api/print/jobs` | authentifié | Liste des lots (filtre optionnel `bien_id`) |
| `GET` | `/api/print/jobs/{job_id}` | authentifié | Détail d'un lot + biens associés |
| `DELETE` | `/api/print/jobs/{job_id}` | gestionnaire+ | Supprime un lot |
| `POST` | `/api/print/jobs/{job_id}/generate` | gestionnaire+ | Génère le fichier `.cmd` du lot |
| `GET` | `/api/print/jobs/{job_id}/file` | authentifié | Télécharge le fichier `.cmd` généré (`text/plain`) — **point d'intégration avec le logiciel/matériel d'impression** |
| `POST` | `/api/print/jobs/{job_id}/reprint` | authentifié | Enregistre une réimpression dans l'historique |

#### Historique — préfixe `/api/history`

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/api/history/` | Historique complet |
| `GET` | `/api/history/me` | Historique de l'utilisateur connecté |
| `GET` | `/api/history/{job_id}` | Historique d'un lot donné |

#### Tableau de bord — préfixe `/api/dashboard`

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Statistiques globales (imports, biens actifs, lots, générations, réimpressions, lots en attente) |
| `GET` | `/api/dashboard/recent` | 10 dernières entrées d'historique |

#### Divers

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/` | Ping applicatif (`{ "application", "version", "status" }`), sans authentification |
| `GET` | `/docs` | Documentation interactive Swagger (générée automatiquement par FastAPI) |

### 6.3 Pages Web (Jinja2, cookie de session)

Toutes les routes ci-dessous rendent du HTML et s'appuient sur le cookie `access_token`. Voir la matrice d'accès (§3) pour le profil minimal requis.

| Méthode | Chemin | Description |
|---|---|---|
| `GET`/`POST` | `/login` | Formulaire de connexion |
| `GET` | `/logout` | Déconnexion (purge du cookie) |
| `GET` | `/dashboard` | Tableau de bord |
| `POST` | `/admin/reset-database` | Réinitialisation de la base métier (administrateur) |
| `GET` | `/admin/users` | Liste des utilisateurs (administrateur) |
| `POST` | `/admin/users` | Création d'un utilisateur (administrateur) |
| `POST` | `/admin/users/{id}/role` | Changement de profil (administrateur) |
| `POST` | `/admin/users/{id}/password` | Réinitialisation de mot de passe (administrateur) |
| `POST` | `/admin/users/{id}/delete` | Suppression d'un utilisateur (administrateur) |
| `GET`/`POST` | `/settings/cmd-template` | Consultation/mise à jour du gabarit CMD (administrateur) |
| `POST` | `/settings/cmd-template/preview` | Aperçu Ajax du gabarit (administrateur) |
| `GET` | `/import` | Page d'import CSV |
| `POST` | `/import/preview` | Aperçu Ajax avant import |
| `POST` | `/import` | Import définitif |
| `GET` | `/assets` | Page Inventaire (recherche, filtres, sélection) |
| `GET` | `/assets/export-csv` | Export CSV du résultat de recherche |
| `POST` | `/assets/export-immateriel` | Export CSV « inventaire immatériel » de la sélection |
| `GET` | `/assets/export-rfid-reader` | Export CSV de tous les biens actifs (lecteur RFID) |
| `POST` | `/jobs/create` | Création d'un lot depuis l'inventaire |
| `GET` | `/jobs` | Liste des lots |
| `GET` | `/jobs/search` | Recherche/ouverture directe d'un lot par Bien ID |
| `GET` | `/jobs/{id}` | Détail d'un lot |
| `GET` | `/jobs/{id}/export-csv` | Export CSV des biens du lot |
| `POST` | `/jobs/{id}/generate` | Génération du fichier `.cmd` |
| `GET` | `/history` | Historique |
| `GET` | `/rfid-scans` | Liste des fichiers de scan RFID chargés |
| `POST` | `/rfid-scans` | Chargement d'un fichier de scan |
| `GET` | `/rfid-scans/{id}` | Détail/édition d'un fichier de scan |
| `POST` | `/rfid-scans/{id}/lines` | Ajout d'une ligne |
| `POST` | `/rfid-scans/{id}/lines/{line_id}` | Modification d'une ligne |
| `POST` | `/rfid-scans/{id}/lines/{line_id}/delete` | Suppression d'une ligne |
| `GET` | `/rfid-scans/{id}/export` | Export horodaté du fichier de scan |
| `GET` | `/glpi-locations` | Page de mise à jour des codes lieux (import GLPI + tableau des écarts) |
| `POST` | `/glpi-locations` | Chargement d'un export GLPI (un des 5 types) |
| `POST` | `/glpi-locations/export-csv` | Export CSV (Bien ID, numéro local) des corrections pour les lignes sélectionnées |
| `POST` | `/glpi-locations/export-csv-complet` | Idem, avec en plus les colonnes immeuble/niveau/local du lieu retenu |
| `POST` | `/glpi-locations/reset` | Vide les données GLPI importées (administrateur) |

---

## 7. Installation en mode test

Objectif : disposer rapidement d'une instance locale pour développer/tester, sans configuration réseau ni service permanent.

### 7.1 Prérequis

- **Python 3.11 ou supérieur** (le code utilise `datetime.UTC`, introduit en 3.11).
- Windows : télécharger sur [python.org](https://www.python.org/downloads/) — cocher **« Add python.exe to PATH »** à l'installation.
- Le code source de l'application (clone Git ou copie du dossier).

### 7.2 Mise en place (Windows — PowerShell)

```powershell
cd C:\rfid-printing\backend

# Environnement virtuel
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Dépendances (dont pytest/httpx pour les tests)
pip install -r requirements-dev.txt

# Configuration
copy .env.example .env
# Ouvrir .env et renseigner RFID_SECRET_KEY, par ex. :
python -c "import secrets; print(secrets.token_hex(32))"

# Schéma de base de données
alembic upgrade head

# Premier compte administrateur
python -m app.seed
```

> Si PowerShell refuse l'exécution du script d'activation (`Activate.ps1`), lancer une fois :
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 7.3 Lancer l'application

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Accéder ensuite à `http://127.0.0.1:8000/login` (identifiant/mot de passe définis dans `app/seed.py`, à changer immédiatement via `/admin/users`). L'option `--reload` recharge automatiquement le serveur à chaque modification du code (pratique en développement, à ne **jamais** utiliser en production).

### 7.4 Lancer les tests automatisés

```powershell
$env:RFID_SECRET_KEY = "test"
python -m pytest -q
```

> Utiliser impérativement `python -m pytest` (et non `pytest` seul) : la résolution du chemin des modules (`app.*`) en dépend.

### 7.5 Mise en place (Linux/macOS, pour référence)

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env    # puis éditer RFID_SECRET_KEY
alembic upgrade head
python -m app.seed
RFID_SECRET_KEY=test python -m pytest -q
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 8. Installation en mode production sous Windows + XAMPP

### 8.1 Principe

Cette application est un service **Python/FastAPI** autonome (base SQLite embarquée) : elle **n'utilise pas** le moteur MySQL/MariaDB ni PHP fournis par XAMPP. Dans ce contexte, **XAMPP sert uniquement de serveur web frontal (Apache)** : Apache reçoit les requêtes des navigateurs sur le port 80/443 et les **retransmet (reverse proxy)** au service Python, qui tourne en arrière-plan sur un port local non exposé (ex. `127.0.0.1:8000`).

```text
Navigateur ──HTTPS/HTTP──▶ Apache (XAMPP, port 443/80)
                                │  mod_proxy / mod_proxy_http
                                ▼
                    Uvicorn (service Windows, 127.0.0.1:8000)
                                │
                                ▼
                       SQLite (rfid.db) + fichiers .cmd
```

Ce montage permet de réutiliser une infrastructure Apache/XAMPP déjà en place (certificat HTTPS, nom de domaine interne...) sans avoir à installer un serveur web supplémentaire.

### 8.2 Prérequis

- Windows Server ou Windows 10/11, avec **XAMPP installé** (module Apache démarré via le panneau de contrôle XAMPP).
- **Python 3.11+** installé séparément (indépendamment de XAMPP), avec l'option **« Add python.exe to PATH »** cochée.
- Droits administrateur sur la machine (installation de service, configuration Apache, pare-feu).
- Le code source de l'application copié localement, par exemple dans `C:\rfid-printing`.

### 8.3 Installation de l'application

```powershell
cd C:\rfid-printing\backend

py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
```

Éditer `C:\rfid-printing\backend\.env` :

```ini
RFID_SECRET_KEY=<valeur générée aléatoirement, à garder secrète>
COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=
```

> `COOKIE_SECURE=true` impose que le cookie de session ne soit transmis qu'en HTTPS : ne l'activer qu'une fois le HTTPS effectivement configuré sur Apache (§8.5), sinon la connexion à l'application échouera.

```powershell
alembic upgrade head
python -m app.seed
```

Se connecter une première fois en local (`uvicorn app.main:app --host 127.0.0.1 --port 8000`, puis `http://127.0.0.1:8000/login`) pour vérifier que tout fonctionne, créer les comptes réels de l'équipe via `/admin/users`, puis arrêter ce serveur temporaire (Ctrl+C) avant de passer à l'installation en service (§8.4).

### 8.4 Exécuter l'application comme service Windows permanent

Un simple `uvicorn` lancé dans une fenêtre console s'arrête à la fermeture de la session. En production, utiliser **NSSM** (*Non-Sucking Service Manager*, gratuit) pour l'exécuter comme un véritable service Windows, démarré automatiquement et relancé en cas de plantage.

1. Télécharger NSSM ([nssm.cc](https://nssm.cc/)) et extraire `nssm.exe` (version 64 bits) dans un dossier, ex. `C:\nssm\`.
2. Installer le service :

   ```powershell
   C:\nssm\nssm.exe install RfidPrinting
   ```

   Dans la fenêtre qui s'ouvre :
   - **Path** : `C:\rfid-printing\backend\venv\Scripts\uvicorn.exe`
   - **Startup directory** : `C:\rfid-printing\backend` *(essentiel : c'est le dossier de travail attendu par l'application)*
   - **Arguments** : `app.main:app --host 127.0.0.1 --port 8000`
   - Onglet **Details** : *Startup type* = `Automatic`.
   - Onglet **I/O** : rediriger la sortie standard/erreur vers des fichiers de log, ex. `C:\rfid-printing\logs\stdout.log` / `stderr.log` (créer le dossier au préalable).

3. Démarrer le service :

   ```powershell
   nssm start RfidPrinting
   ```

4. Vérifier qu'il répond en local : `Invoke-WebRequest http://127.0.0.1:8000/` doit renvoyer un JSON `{"application": "RFID PRINTING", ...}`.

Commandes utiles :

```powershell
nssm stop RfidPrinting
nssm restart RfidPrinting
nssm remove RfidPrinting confirm   # désinstalle le service
```

> Alternative sans outil tiers : une tâche planifiée (Planificateur de tâches Windows) déclenchée « au démarrage de l'ordinateur », exécutant `uvicorn.exe` avec les mêmes arguments, avec l'option de relance automatique en cas d'échec. NSSM reste préférable (gestion native en tant que service, logs, arrêt propre).

### 8.5 Configurer Apache (XAMPP) en reverse proxy

1. Activer les modules nécessaires dans `C:\xampp\apache\conf\httpd.conf` : décommenter (retirer le `#`) les lignes suivantes si elles ne le sont pas déjà :

   ```apache
   LoadModule proxy_module modules/mod_proxy.so
   LoadModule proxy_http_module modules/mod_proxy_http.so
   ```

2. Ajouter la configuration du reverse proxy — soit directement dans `httpd.conf`, soit (recommandé) dans un VirtualHost dédié (`C:\xampp\apache\conf\extra\httpd-vhosts.conf`) :

   ```apache
   <VirtualHost *:80>
       ServerName rfid.mondomaine.local

       ProxyPreserveHost On
       ProxyPass        /  http://127.0.0.1:8000/
       ProxyPassReverse /  http://127.0.0.1:8000/
   </VirtualHost>
   ```

   Si les VirtualHosts ne sont pas encore activés, vérifier dans `httpd.conf` que la ligne suivante est bien décommentée :

   ```apache
   Include conf/extra/httpd-vhosts.conf
   ```

3. Redémarrer Apache depuis le panneau de contrôle XAMPP (bouton **Stop** puis **Start** sur la ligne Apache).

4. Vérifier l'accès via l'adresse configurée (`http://rfid.mondomaine.local/login`, ou l'IP/nom de la machine si aucun nom de domaine interne n'est utilisé).

### 8.6 Activer HTTPS

Deux approches, selon l'infrastructure existante :

- **Certificat déjà géré par XAMPP/Apache** (cas le plus fréquent en environnement d'entreprise) : réutiliser la configuration `mod_ssl` existante (`httpd-ssl.conf`), et dupliquer le bloc `ProxyPass`/`ProxyPassReverse` du §8.5 dans le `<VirtualHost *:443>` correspondant.
- **Aucun certificat existant** : générer un certificat interne (autorité de certification d'entreprise) ou, si la machine est exposée sur Internet, un certificat [Let's Encrypt](https://letsencrypt.org/) via un outil compatible Windows tel que [win-acme](https://www.win-acme.com/).

Une fois HTTPS actif, repasser `COOKIE_SECURE=true` dans `.env` (§8.3) si ce n'était pas déjà fait, puis redémarrer le service (`nssm restart RfidPrinting`).

### 8.7 Pare-feu Windows

- Autoriser les ports **80** et/ou **443** (Apache) en entrée pour les postes clients concernés.
- Le port **8000** (Uvicorn) ne doit **jamais** être exposé au-delà de `127.0.0.1` : Apache est l'unique point d'entrée réseau. Ne pas créer de règle de pare-feu entrante pour ce port.

### 8.8 Démarrage automatique après redémarrage du serveur

- Le service `RfidPrinting` (NSSM, *Startup type* = Automatic) démarre seul après redémarrage de Windows.
- Vérifier également que le service Apache de XAMPP est configuré pour démarrer automatiquement (panneau de contrôle XAMPP → case à cocher *Service* sur la ligne Apache, ou installation du module Apache comme service Windows via `httpd.exe -k install`).

---

## 9. Exploitation et maintenance

### 9.1 Sauvegardes

À sauvegarder régulièrement (les deux éléments suivants suffisent à reconstituer entièrement l'état applicatif) :

1. `backend/rfid.db` (base de données complète).
2. `backend/generated/` (fichiers `.cmd` déjà générés).

**Tester la restauration** au moins une fois avant la mise en production réelle.

### 9.2 Mise à jour de l'application

```powershell
nssm stop RfidPrinting
cd C:\rfid-printing
git pull                          # ou copie de la nouvelle version du code
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt   # si les dépendances ont changé
alembic upgrade head              # au cas où (les migrations s'appliquent aussi seules au démarrage)
nssm start RfidPrinting
```

### 9.3 Journaux

- Sortie standard/erreur du service : fichiers configurés à l'étape §8.4 (onglet *I/O* de NSSM).
- Journal applicatif interne (`logging`) : actions sensibles tracées (réinitialisation de base, modification du gabarit CMD, création de comptes...).

### 9.4 Dépannage courant

| Symptôme | Piste |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Le service/la commande n'est pas lancé(e) depuis `backend/` — vérifier le *Startup directory* du service NSSM. |
| Connexion impossible après login (page blanche/erreur) | `COOKIE_SECURE=true` sans HTTPS actif : soit désactiver temporairement, soit finaliser la configuration HTTPS (§8.6). |
| 502/504 côté Apache | Le service `RfidPrinting` (Uvicorn) n'est pas démarré, ou écoute sur un port différent de celui configuré dans `ProxyPass` — vérifier `nssm status RfidPrinting` et le port dans les arguments du service. |
| Erreur bcrypt au premier login (`password cannot be longer than 72 bytes`) | Incompatibilité `passlib`/`bcrypt` : vérifier que `requirements.txt` a bien été utilisé tel quel (`bcrypt==4.0.1` explicitement épinglé). |

---

## 10. Annexes

### 10.1 Variables d'environnement (`.env`)

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `RFID_SECRET_KEY` | Clé de signature des jetons JWT — **obligatoire en production** (sans elle, une clé aléatoire temporaire est générée à chaque démarrage, invalidant toutes les sessions) | *(aucune — avertissement au démarrage si absente)* |
| `CORS_ALLOWED_ORIGINS` | Origines externes autorisées à appeler l'API depuis un navigateur (liste séparée par des virgules) ; inutile pour l'UI Jinja2, servie en same-origin | *(vide)* |
| `COOKIE_SECURE` | `true` pour restreindre le cookie de session aux connexions HTTPS | `false` |

### 10.2 Commandes de référence

| Action | Commande (depuis `backend/`, venv activé) |
|---|---|
| Lancer l'application (dev) | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Lancer l'application (prod, sans reload) | `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Appliquer les migrations | `alembic upgrade head` |
| Créer une migration | `alembic revision --autogenerate -m "description"` |
| Créer le premier administrateur | `python -m app.seed` |
| Lancer les tests | `python -m pytest -q` |

### 10.3 Documentation interactive de l'API

Une fois l'application démarrée, la documentation Swagger générée automatiquement par FastAPI est disponible sur `/docs` (et le schéma OpenAPI brut sur `/openapi.json`).
