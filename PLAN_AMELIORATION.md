# Plan d'action priorisé — RFID Printing

Ce document synthétise l'analyse du projet (import CSV → sélection de biens →
génération de fichier `.cmd` → historisation) et propose un plan d'action
priorisé : sécurité/bugs bloquants, suppressions de code mort, puis
améliorations fonctionnelles et qualité.

Chaque item indique : fichiers concernés, action, effort estimé (S = petit,
M = moyen, L = gros). Les items traités sont cochés ✅.

---

## Décisions actées

**Architecture d'interface : Jinja2 (serveur), pas de SPA React.** ✅ *(fait)*
Le proxy d'entreprise ne permet pas l'usage de Node.js/npm, ce qui rend la
SPA React/Vite (`frontend/`) impossible à installer, développer ou builder
dans l'environnement cible. L'interface officielle est désormais l'UI
server-side Jinja2 (`web_router.py` + `templates/`), qui ne dépend que de
Python/FastAPI. `web_router.py` a été mis à niveau (authentification par
cookie, contrôle de rôle, anti-doublon) puis `frontend/` a été supprimé.

**Authentification web : cookie HttpOnly réutilisant le JWT existant.** ✅ *(fait)*
`POST /login` pose un cookie `access_token` (HttpOnly, `SameSite=Lax`,
`Secure` configurable via `COOKIE_SECURE`) signé avec le même mécanisme
JWT que l'API. `get_current_user_web` le lit sur chaque route Jinja2 et
redirige vers `/login?next=...` si absent/invalide (exception
`WebAuthRequired` + handler dans `main.py`). L'API garde son
authentification par header `Authorization: Bearer` pour d'éventuels
clients externes.

**Délimiteur CSV : auto-détection (`;` puis `,`).** ✅ *(fait)*
Le code, le fichier d'exemple et les tests utilisaient tous `;`, ce qui
laissait penser que la mention « virgule » décrivait le format CSV de façon
générique plutôt qu'un séparateur littéral. Plutôt que trancher sur une
hypothèse, `import_router.py` détecte maintenant automatiquement le bon
délimiteur (voir `parse_inventory_csv`).

---

## P0 — Sécurité et bugs bloquants

| # | Action | Fichiers | Effort | Statut |
|---|--------|----------|--------|--------|
| P0-1 | Séparateur CSV : auto-détection `;`/`,` | `backend/app/routers/import_router.py` | S | ✅ fait |
| P0-2 | Protéger tous les endpoints API par `Depends(get_current_user)` | `import_router.py`, `print_router.py`, `history_router.py`, `dashboard_router.py` | M | ✅ fait |
| P0-3 | Mettre à niveau `web_router.py` (Jinja2) pour devenir l'interface officielle unique : authentification (login requis), contrôle de rôle sur génération/suppression, garde-fou anti-double génération, puis suppression de `frontend/` | `backend/app/routers/web_router.py`, `backend/app/templates/`, `frontend/` | L | ✅ fait |
| P0-4 | Activer `require_manager()` sur les actions sensibles (génération, suppression de lot) | `backend/app/auth.py`, `print_router.py` | S | ✅ fait |
| P0-5 | Sortir `SECRET_KEY` en variable d'environnement | `backend/app/auth.py` | S | ✅ fait |
| P0-6 | Corriger le `.gitignore` (`backend/generated/*.cmd`) et retirer du suivi git les `.cmd` déjà committés | `.gitignore`, `backend/generated/*.cmd` | S | ✅ fait |
| P0-7 | Ajouter la configuration CORS dans `main.py` | `backend/app/main.py` | S | ✅ fait |

---

## P1 — Gaps fonctionnels liés à l'objectif principal

*(mis à jour pour cibler l'UI Jinja2, `frontend/` étant retiré — voir P0-3)*

| # | Action | Fichiers | Effort | Statut |
|---|--------|----------|--------|--------|
| P1-1 | ~~Décider de l'interface cible unique~~ → tranché : Jinja2 (voir « Décisions actées ») | — | — | ✅ fait |
| P1-2 | Persister la sélection de biens d'une page à l'autre (localStorage + injection de champs cachés au submit) | `backend/app/templates/assets.html` | M | ✅ fait |
| P1-3 | Ajouter une limite/pagination sur `GET /api/import/assets/search` | `backend/app/routers/import_router.py` | S | ✅ fait |
| P1-4 | Ajouter un filtre par plage de date de sortie (`date_from`/`date_to`) | `backend/app/routers/web_router.py`, `backend/app/templates/assets.html` | M | ✅ fait |
| P1-5 | Ajouter un aperçu du CSV avant validation de l'import (colonnes détectées, compteurs) | `backend/app/routers/web_router.py`, `backend/app/templates/import.html` | M | ✅ fait — a aussi corrigé un manque : `web_router.py` n'avait **aucune** route d'import après suppression de `frontend/` |
| P1-6 | Renforcer la validation du CSV : encodage non-UTF-8, `bien_id`/désignation manquants, doublons de `bien_id` | `backend/app/services/import_service.py` | M | ✅ fait |

---

## P2 — Nettoyage / suppression de code mort

| # | Action | Fichiers | Effort | Statut |
|---|--------|----------|--------|--------|
| P2-1 | Supprimer `legacy_models.py` (doublon exact de `models/user_model.py`) | `backend/app/legacy_models.py` | S | ✅ fait |
| P2-2 | Déplacer `models/test_history.py` vers `backend/tests/` | `backend/app/models/test_history.py` → `backend/tests/` | S | ✅ fait |
| P2-3 | Nettoyer les imports/déclarations dupliqués en fin de `auth_router.py` | `backend/app/routers/auth_router.py` | S | ✅ fait |
| P2-4 | Factoriser la génération de fichier CMD dupliquée entre API et web | `backend/app/services/print_job_service.py` | M | ✅ fait |
| P2-5 | Supprimer la classe `client(TestClient)` non utilisée dans `conftest.py` | `backend/tests/conftest.py` | S | ✅ fait |
| P2-6 | Uniformiser `datetime.utcnow()` → `datetime.now(UTC)` dans `import_model.py` | `backend/app/models/import_model.py` | S | ✅ fait |
| P2-7 | Supprimer `frontend/` (React/Vite) | `frontend/` | S | ✅ fait |
| P2-8 | Supprimer `backend/app/templates/jobs.zip` (archive égarée dans les templates) | `backend/app/templates/jobs.zip` | S | ✅ fait |

**P0, P1 et P2 sont entièrement traités.**

---

## P3 — Qualité, infra, maintenabilité (restant)

| # | Action | Fichiers | Effort | Statut |
|---|--------|----------|--------|--------|
| P3-1 | Remplacer `migrate_sprint5.py` (ALTER TABLE manuel) par un vrai outil de migration (Alembic) | `backend/app/migrate_sprint5.py` | M | à décider — voir note ci-dessous |
| P3-2 | Figer les versions de dépendances Python (`requirements.txt` avec `==`) | `backend/requirements.txt` | S | `jinja2` ajouté ✅, pin des versions restant à faire |
| P3-3 | Ajouter un handler d'exception global FastAPI pour un format d'erreur cohérent (JSON pour l'API, page HTML pour l'UI Jinja2) | `backend/app/main.py` | S | |
| P3-4 | Ajouter des tests pour `cmd_generator.py` / `CommandGenerator` (aucun test direct actuellement, seulement via les routes) | `backend/tests/` | S | tests routes web/API ✅ (nombreux ajouts cette session), reste `cmd_generator.py` isolé |
| P3-5 | Mettre en place une CI (GitHub Actions) exécutant `pytest` à chaque push/PR | `.github/workflows/` | S | |

**Note sur P3-1 (Alembic)** : pour un outil interne sur SQLite avec un schéma
qui évolue rarement, Alembic peut être disproportionné. À valider avec vous
avant de l'ajouter — l'alternative light est de garder des scripts de
migration ponctuels comme `migrate_sprint5.py`, mais nommés et documentés de
façon cohérente.

---

## État global

Tout le **P0** (sécurité), tout le **P1** (gaps fonctionnels : import CSV
manquant après suppression du frontend, pagination, sélection multi-pages,
filtres, validation CSV) et tout le **P2** (nettoyage) sont traités et
testés (30 tests passent). Il reste uniquement des items **P3** de
qualité/infra, dont aucun n'est bloquant pour l'usage de l'application.
