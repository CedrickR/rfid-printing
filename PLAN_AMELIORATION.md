# Plan d'action priorisé — RFID Printing

Ce document synthétise l'analyse du projet (import CSV → sélection de biens →
génération de fichier `.cmd` → historisation) et propose un plan d'action
priorisé : sécurité/bugs bloquants, suppressions de code mort, puis
améliorations fonctionnelles et qualité.

Chaque item indique : fichiers concernés, action, effort estimé (S = petit,
M = moyen, L = gros).

---

## Point à clarifier avant exécution

Le CSV est décrit comme délimité par une **virgule**, mais tout le code
(`import_router.py:46`), le fichier d'exemple `inventaire.csv` et les tests
utilisent le **point-virgule**. À trancher avant de toucher au parsing
(voir P0-1).

---

## P0 — Sécurité et bugs bloquants (à traiter en premier)

| # | Action | Fichiers | Effort |
|---|--------|----------|--------|
| P0-1 | Confirmer le séparateur CSV réel et corriger `pd.read_csv(sep=...)` en conséquence (ou détecter automatiquement `,` vs `;`) | `backend/app/routers/import_router.py` | S |
| P0-2 | Protéger tous les endpoints API par `Depends(get_current_user)` : `GET /api/import/assets`, `/assets/search`, `/assets/active`, `/assets-count`, `GET /api/print/jobs`, `DELETE /api/print/jobs/{id}`, `GET /api/history*` | `backend/app/routers/import_router.py`, `print_router.py`, `history_router.py` | M |
| P0-3 | Supprimer `web_router.py` et les templates Jinja2 associés **ou** y ajouter la même authentification/logique anti-doublon que l'API (choix architecture, voir P1-1) | `backend/app/routers/web_router.py`, `backend/app/templates/` | M |
| P0-4 | Activer réellement le contrôle de rôle `require_manager()` sur les actions sensibles (génération de lot, suppression de lot) | `backend/app/auth.py`, `print_router.py` | S |
| P0-5 | Sortir `SECRET_KEY` du code en variable d'environnement (`.env` + `pydantic-settings` ou `os.environ`) | `backend/app/auth.py` | S |
| P0-6 | Corriger le `.gitignore` pour exclure réellement `backend/generated/*.cmd` (pattern actuel non ancré) et retirer du suivi git les fichiers `.cmd` déjà committés | `.gitignore`, `backend/generated/*.cmd` | S |
| P0-7 | Ajouter la configuration CORS dans `main.py` pour permettre au frontend React d'appeler l'API en dehors du dev local | `backend/app/main.py` | S |

---

## P1 — Gaps fonctionnels liés à l'objectif principal

| # | Action | Fichiers | Effort |
|---|--------|----------|--------|
| P1-1 | Décider de l'interface cible unique (SPA React **ou** pages Jinja2) et supprimer l'autre pour arrêter la double maintenance | `backend/app/routers/web_router.py`, `frontend/` | L |
| P1-2 | Ajouter une pagination réelle dans `AssetsPage.jsx` (page suivante/précédente, taille de page) — actuellement bloqué à 100 biens visibles/sélectionnables | `frontend/src/pages/AssetsPage.jsx`, `frontend/src/api/assetApi.js` | M |
| P1-3 | Ajouter une limite/pagination sur `GET /api/import/assets/search` (actuellement sans limite) | `backend/app/routers/import_router.py` | S |
| P1-4 | Ajouter des filtres de sélection (statut actif/inactif, plage de date de sortie) avant génération du lot d'impression | `frontend/src/pages/AssetsPage.jsx`, `backend/app/routers/import_router.py` | M |
| P1-5 | Ajouter un aperçu du CSV avant validation de l'import (colonnes détectées, nombre de lignes actives/exclues) — le parcours utilisateur documenté prévoit un « contrôle du fichier » absent du code actuel | `frontend/src/pages/ImportPage.jsx`, `backend/app/routers/import_router.py` | M |
| P1-6 | Renforcer la validation du CSV : encodage non-UTF-8, colonnes en trop, doublons de `bien_id`, lignes vides — remonter des erreurs explicites plutôt que l'exception pandas brute | `backend/app/routers/import_router.py` | M |

---

## P2 — Nettoyage / suppression de code mort

| # | Action | Fichiers | Effort |
|---|--------|----------|--------|
| P2-1 | Supprimer `legacy_models.py` (doublon exact de `models/user_model.py`) | `backend/app/legacy_models.py` | S |
| P2-2 | Déplacer `models/test_history.py` vers `backend/tests/` (c'est un fichier de test égaré) | `backend/app/models/test_history.py` → `backend/tests/` | S |
| P2-3 | Nettoyer les imports/déclarations dupliqués en fin de `auth_router.py` (ré-import de `Depends`, `HTTPException`, `HTTPBearer`, re-déclaration de `security`) | `backend/app/routers/auth_router.py` | S |
| P2-4 | Factoriser la génération de fichier CMD dupliquée entre `print_router.generate_print_job_file` et `web_router.generate_job` dans un seul service | `backend/app/routers/print_router.py`, `web_router.py`, `services/cmd_generator.py` | M |
| P2-5 | Supprimer la classe `client(TestClient)` non utilisée dans `conftest.py` (la fixture `client` utilise un `TestClient` brut à la place) | `backend/tests/conftest.py` | S |
| P2-6 | Uniformiser `datetime.utcnow()` → `datetime.now(UTC)` dans `import_model.py` | `backend/app/models/import_model.py` | S |
| P2-7 | Sortir les fichiers de notes (`npm-config.txt`, `Navigation principale.txt`, `arborescence.txt`) du code source, vers `docs/` ou hors repo | `frontend/` | S |
| P2-8 | Supprimer `backend/app/templates/jobs.zip` (archive égarée dans les templates) | `backend/app/templates/jobs.zip` | S |

---

## P3 — Qualité, infra, maintenabilité

| # | Action | Fichiers | Effort |
|---|--------|----------|--------|
| P3-1 | Remplacer `migrate_sprint5.py` (ALTER TABLE manuel) par un vrai outil de migration (Alembic) | `backend/app/migrate_sprint5.py` | M |
| P3-2 | Figer les versions de dépendances (`requirements.txt` avec `==`, `package.json` sans `"latest"`) | `backend/requirements.txt`, `frontend/package.json` | S |
| P3-3 | Ajouter un handler d'exception global FastAPI pour un format d'erreur cohérent | `backend/app/main.py` | S |
| P3-4 | Sortir l'URL de base de l'API du frontend en variable d'environnement Vite (`import.meta.env.VITE_API_URL`) au lieu de `http://127.0.0.1:8000` en dur | `frontend/src/api/apiClient.js` | S |
| P3-5 | Ajouter des tests manquants : génération CMD (`cmd_generator.py`), pagination des assets, endpoints désormais protégés, contrôle de rôle `gestionnaire` | `backend/tests/` | M |
| P3-6 | Mettre en place une CI (GitHub Actions) exécutant `pytest` et le build frontend à chaque push/PR | `.github/workflows/` | S |

---

## Ordre d'exécution recommandé

1. **P0** dans l'ordre du tableau (sécurité avant tout — actuellement des
   données sont lisibles/supprimables sans authentification).
2. **P1-2 et P1-3** (pagination) rapidement après, car elles bloquent
   l'usage réel de l'outil sur un inventaire de taille normale.
3. **P2** peut être fait en parallèle par petites PR indépendantes, sans
   risque fonctionnel.
4. **P1-1** (choix d'architecture SPA vs Jinja2) est structurant : à valider
   avec vous avant de lancer la suppression d'une des deux interfaces.
5. **P3** en continu, au fil des autres chantiers.
