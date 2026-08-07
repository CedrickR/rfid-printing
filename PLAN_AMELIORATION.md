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

## P3 — Qualité, infra, maintenabilité

| # | Action | Fichiers | Effort | Statut |
|---|--------|----------|--------|--------|
| P3-1 | Remplacer `migrate_sprint5.py` (ALTER TABLE manuel) par Alembic | `backend/alembic/`, `backend/app/main.py` | M | ✅ fait |
| P3-2 | Figer les versions de dépendances Python (`requirements.txt` avec `==`) | `backend/requirements.txt` | S | ✅ fait — a aussi révélé un bug bloquant (voir note) |
| P3-3 | Ajouter un handler d'exception global FastAPI pour un format d'erreur cohérent (JSON pour l'API, page HTML pour l'UI Jinja2) | `backend/app/main.py` | S | ✅ fait |
| P3-4 | Ajouter des tests pour `cmd_generator.py` / `CommandGenerator` | `backend/tests/test_cmd_generator.py` | S | ✅ fait |
| P3-5 | Mettre en place une CI (GitHub Actions) exécutant `pytest` à chaque push/PR | `.github/workflows/tests.yml` | S | ✅ fait |

**P3-2 — bug bloquant découvert et corrigé.** En testant `requirements.txt`
sur une installation 100 % neuve (sans aucun venv réutilisé) : `passlib
1.7.4` est incompatible avec `bcrypt>=4.1` (bug connu upstream), ce qui
faisait planter `hash_password()`/`verify_password()` avec une `ValueError`
dès le premier login. Corrigé en épinglant `bcrypt==4.0.1` en plus du
pin de toutes les dépendances. Un `requirements-dev.txt` (pytest, httpx)
a aussi été ajouté pour ne pas mélanger dépendances runtime et tests.

**P3-3 — comportement avant/après.** `GET /jobs/999` (lot inexistant)
renvoyait `{"detail": "Lot introuvable"}` en JSON brut même en visitant la
page dans un navigateur. Un handler d'exception dédié route désormais les
erreurs vers du JSON pour `/api/*`/`/auth/*` et vers une page HTML
(`error.html`, cohérente avec le reste de l'UI) pour les autres routes ;
un filet de sécurité supplémentaire évite qu'une exception non prévue
n'expose un traceback au client.

**P3-5 — CI.** `.github/workflows/tests.yml` installe
`requirements-dev.txt` et lance `pytest` sur chaque push et pull request.

**P3-1 (Alembic) — décision actée.** `migrate_sprint5.py` était un script
SQLite brut, avec un chemin de base de données codé en dur (indépendant de
`DATABASE_URL`) et aucune traçabilité de ce qui était appliqué où — un
risque réel vu que le nom laissait présager `migrate_sprint6.py`, etc. à
chaque sprint. Mis en place :
- `backend/alembic/` (config + `env.py` branché sur `app.database.Base` et
  `DATABASE_URL`) et une migration `baseline` reflétant l'intégralité du
  schéma actuel (vérifié : un `autogenerate` après application ne détecte
  plus aucune différence).
- `main.py` applique `alembic upgrade head` au démarrage à la place de
  `Base.metadata.create_all()` : toujours zéro-config à l'usage, mais avec
  un historique versionné et rejouable.
- `migrate_sprint5.py` supprimé (son contenu — colonnes `generated_file`/
  `generated_at` — fait déjà partie de la migration `baseline`).

Pour un futur changement de schéma : modifier les modèles SQLAlchemy puis
lancer, depuis `backend/` :
```
alembic revision --autogenerate -m "description du changement"
alembic upgrade head
```
et committer le fichier généré dans `alembic/versions/`.

---

## État global

**Tous les items du plan (P0, P1, P2, P3) sont traités.** 40 tests passent,
vérifiés sur une installation 100 % neuve. Une CI GitHub Actions les
exécute désormais sur chaque push/PR.
