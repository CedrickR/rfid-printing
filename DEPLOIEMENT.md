# Guide de mise en production — RFID Printing

Ce document liste, dans l'ordre, toutes les actions nécessaires pour passer
de l'état actuel (code fonctionnel, testé, CI verte sur `main`) à une
application réellement utilisée en production par l'équipe.

Chaque section indique **qui** agit typiquement (vous / l'IT / le
fournisseur de l'imprimante) et **pourquoi** l'action est nécessaire, pas
seulement la commande à taper.

---

## 0. Décisions préalables (à trancher avant de commencer)

Ces questions bloquent plusieurs sections plus bas — à clarifier en premier.

| # | Question | Pourquoi ça compte |
|---|----------|---------------------|
| 0.1 | Où l'application va-t-elle tourner ? (VM interne, serveur physique existant, poste dédié...) | Détermine toutes les étapes d'installation système (§1-4) |
| 0.2 | **Comment le logiciel d'impression RFID récupère-t-il les fichiers `.cmd` générés ?** Lit-il un dossier réseau partagé, une clé/chemin local, ou faut-il qu'il interroge l'API (`GET /api/print/jobs/{id}/file`) ? | C'est le point d'intégration final de tout le projet — sans réponse, les étiquettes ne sortent jamais de l'imprimante. Voir §6. |
| 0.3 | Nom de domaine ou adresse interne pour accéder à l'application (ex. `rfid.mondomaine.local`) | Nécessaire pour le certificat HTTPS et la configuration du reverse proxy (§4) |
| 0.4 | Qui sont les utilisateurs réels et quels profils (`administrateur` / `gestionnaire` / `lecteur`) leur attribuer ? | Le premier compte administrateur est créé par script, les suivants via la page Utilisateurs de l'application (§8) |

---

## 1. Serveur et environnement système

*(IT / infra)*

1. Provisionner une machine (VM ou serveur) avec accès réseau à l'imprimante RFID (ou au partage réseau qu'elle surveille) et accessible en HTTPS par les utilisateurs.
2. Installer **Python 3.11+** (seule dépendance système requise — aucun Node/npm nécessaire, confirmé compatible avec un environnement dont le proxy d'entreprise bloque ces outils).
3. Créer un utilisateur système dédié, non privilégié, pour faire tourner l'application (ex. `rfid-app`) — ne jamais lancer le service en `root`.
4. Choisir un répertoire de déploiement fixe (ex. `/opt/rfid-printing`) et cloner le dépôt :
   ```bash
   git clone https://github.com/CedrickR/rfid-printing.git /opt/rfid-printing
   cd /opt/rfid-printing
   git checkout main
   ```

---

## 2. Installation de l'application

*(IT / développeur)*

1. Créer l'environnement virtuel et installer les dépendances (versions figées dans `requirements.txt`, testées sur installation neuve) :
   ```bash
   cd /opt/rfid-printing/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Créer le fichier de configuration :
   ```bash
   cp .env.example .env
   ```
3. Renseigner **`RFID_SECRET_KEY`** dans `.env` avec une vraie valeur secrète, générée une fois et **jamais commitée** :
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   ⚠️ Sans cette variable, l'application démarre quand même (clé aléatoire de secours) mais **tous les utilisateurs sont déconnectés à chaque redémarrage** — inutilisable en production.
4. Mettre `COOKIE_SECURE=true` dans `.env` (nécessite le HTTPS mis en place en §4 — sinon les cookies de session ne seront jamais envoyés et personne ne pourra rester connecté).
5. Laisser `CORS_ALLOWED_ORIGINS` vide, sauf si un système externe doit appeler l'API `/api/*` directement depuis un navigateur.
6. **Point d'attention technique** : `app/database.py` (`sqlite:///./rfid.db`) et `app/main.py` (dossier `app/static`) utilisent des chemins **relatifs au répertoire courant**. L'application doit donc toujours être démarrée avec `backend/` comme répertoire de travail — c'est ce que fixe `WorkingDirectory` dans l'unité systemd du §3. Ne pas lancer la commande depuis un autre dossier, sous peine de créer une base vide au mauvais endroit ou de planter au démarrage.

---

## 3. Lancement en production (gestion du process)

*(IT)*

**Ne jamais utiliser `--reload`** en production (c'est un mode développeur qui recharge le code à chaque modification de fichier, pénalise les performances et n'est pas fait pour tourner en continu).

Exemple d'unité systemd (`/etc/systemd/system/rfid-printing.service`) :

```ini
[Unit]
Description=RFID Printing
After=network.target

[Service]
Type=simple
User=rfid-app
Group=rfid-app
WorkingDirectory=/opt/rfid-printing/backend
EnvironmentFile=/opt/rfid-printing/backend/.env
ExecStart=/opt/rfid-printing/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rfid-printing
sudo systemctl status rfid-printing
```

Notes :
- `--host 127.0.0.1` : l'application n'écoute qu'en local, jamais exposée directement — c'est le reverse proxy (§4) qui reçoit le trafic externe.
- `--workers 2` : nombre de process suffisant pour un outil interne à faible trafic ; à ajuster selon le nombre d'utilisateurs simultanés observé.
- `EnvironmentFile` charge `RFID_SECRET_KEY`, `COOKIE_SECURE`, etc. définis en §2.
- Les migrations Alembic s'appliquent **automatiquement à chaque démarrage** (`command.upgrade(cfg, "head")` dans `main.py`) : rien à faire manuellement après un `git pull` incluant une nouvelle migration, juste redémarrer le service.

---

## 4. Reverse proxy et HTTPS

*(IT)*

L'application doit être servie en HTTPS (obligatoire pour que `COOKIE_SECURE=true` fonctionne, et pour ne pas faire transiter identifiants/mots de passe en clair).

Exemple avec Nginx :

```nginx
server {
    listen 443 ssl;
    server_name rfid.mondomaine.local;

    ssl_certificate     /etc/ssl/certs/rfid.mondomaine.local.crt;
    ssl_certificate_key /etc/ssl/private/rfid.mondomaine.local.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name rfid.mondomaine.local;
    return 301 https://$host$request_uri;
}
```

- Certificat : Let's Encrypt (`certbot`) si la machine est joignable publiquement, sinon l'autorité de certification interne de l'entreprise.
- Une fois HTTPS actif, mettre à jour `CORS_ALLOWED_ORIGINS` si nécessaire avec l'URL `https://` finale.

---

## 5. Sécurité — actions immédiates avant ouverture aux utilisateurs

*(vous)*

1. **Changer le mot de passe admin par défaut.** Le script `seed.py` crée `admin` / `Admin123!` — ce mot de passe est visible dans le code source public. À changer dès la première connexion, ou mieux, créer directement les comptes réels avec des mots de passe forts (§8) sans jamais utiliser le mot de passe par défaut en production.
2. Vérifier que `.env` n'est **jamais commité** (déjà exclu par `.gitignore`) et que ses permissions fichier sont restreintes (`chmod 600 .env`, lisible uniquement par l'utilisateur `rfid-app`).
3. Restreindre le pare-feu : seul le port 443 (HTTPS) doit être exposé à l'extérieur de la machine ; le port 8000 (uvicorn) ne doit être joignable qu'en local (déjà garanti par `--host 127.0.0.1`).
4. Vérifier les permissions sur `backend/rfid.db` et `backend/generated/` : lecture/écriture réservées à l'utilisateur `rfid-app`.
5. **Lacune connue, à évaluer** : aucune limite de tentatives de connexion sur `/login` et `/auth/login` (pas de protection anti brute-force). Acceptable pour un outil interne avec accès réseau restreint, mais à surveiller si l'application devient accessible plus largement.

---

## 6. Intégration avec l'imprimante RFID (point critique)

*(vous + fournisseur/mainteneur du logiciel d'impression)*

Les fichiers `.cmd` sont écrits dans `backend/generated/` au moment de la génération d'un lot. **Comment le logiciel d'impression les récupère n'a jamais été formalisé dans ce projet** — c'est la dernière étape à sécuriser avant une vraie mise en service :

- **Option A — partage de fichiers** : monter `backend/generated/` sur un partage réseau (SMB/NFS) que le logiciel d'impression surveille. Le plus simple si ce logiciel sait déjà lire un dossier local/réseau.
- **Option B — téléchargement via l'API** : le logiciel d'impression appelle `GET /api/print/jobs/{id}/file` avec un jeton (`Authorization: Bearer ...`) pour récupérer le fichier à la demande. Nécessite de créer un compte de service dédié (§8) pour ce logiciel, avec un jeton renouvelé selon `ACCESS_TOKEN_EXPIRE_MINUTES` (60 minutes actuellement — à revoir si un accès de longue durée est nécessaire pour ce cas d'usage).
- Dans les deux cas, prévoir un test de bout en bout avec l'imprimante physique **avant** la bascule définitive (voir §9).

---

## 7. Sauvegardes

*(IT)*

Toute la donnée métier vit dans un seul fichier SQLite (`backend/rfid.db`) plus les fichiers déjà générés (`backend/generated/*.cmd`, nécessaires pour le re-téléchargement d'un lot déjà imprimé).

1. Sauvegarde de la base — utiliser la commande de backup SQLite plutôt qu'une simple copie (évite un fichier corrompu si une écriture est en cours) :
   ```bash
   sqlite3 /opt/rfid-printing/backend/rfid.db ".backup /chemin/sauvegardes/rfid-$(date +%Y%m%d-%H%M%S).db"
   ```
   À planifier en cron (quotidien a minima), avec une rétention définie (ex. 30 jours) et une **copie hors de la machine** (autre serveur, stockage réseau, etc.).
2. Sauvegarde de `backend/generated/` (mêmes fréquence/rétention).
3. **Tester la restauration** au moins une fois avant la mise en production réelle — une sauvegarde jamais restaurée n'est pas une sauvegarde fiable.

---

## 8. Comptes utilisateurs

*(vous)*

La gestion des comptes se fait désormais dans l'application, page **Utilisateurs** (`/admin/users`, réservée au profil `administrateur`) : création de compte, changement de profil, réinitialisation de mot de passe et suppression. `seed.py` ne sert plus qu'à amorcer le tout premier compte administrateur d'une installation neuve :

```bash
cd /opt/rfid-printing/backend
source venv/bin/activate
python -c "
from app.database import SessionLocal
from app.models.user_model import User
from app.auth import hash_password

db = SessionLocal()
db.add(User(username='j.dupont', password_hash=hash_password('UnMotDePasseFort!'), role='administrateur'))
db.commit()
print('Compte créé')
"
```

Trois profils :

- `administrateur` : accès complet, y compris le modèle CMD, la gestion des utilisateurs/profils et le bouton **« Vider la base de données »** (action irréversible — informer les administrateurs de sa portée avant l'ouverture).
- `gestionnaire` : usage courant (import, inventaire, lots, historique, fichiers RFID), sans le modèle CMD, la gestion des utilisateurs ni la réinitialisation de la base.
- `lecteur` : uniquement la page Inventaire, en lecture — les boutons d'export et de création de lot y sont désactivés.

Se connecter avec le compte administrateur créé ci-dessus pour créer ensuite les comptes réels de l'équipe via `/admin/users`.

---

## 9. Vérifications avant bascule (recette)

*(vous)*

1. Lancer la suite de tests automatisés directement dans l'environnement cible :
   ```bash
   cd /opt/rfid-printing/backend
   source venv/bin/activate
   pip install -r requirements-dev.txt
   RFID_SECRET_KEY=test python -m pytest -q
   ```
2. Parcours utilisateur complet en conditions réelles, avec un vrai compte (pas admin/test) :
   - Connexion → Import d'un vrai fichier export du logiciel de gestion d'inventaire (aperçu puis import) → vérifier le nombre de biens actifs/exclus/déjà présents.
   - Sélection de biens sur plusieurs pages → création d'un lot → génération du `.cmd`.
   - Téléchargement du fichier généré et vérification de son contenu (gabarit par défaut ou personnalisé, voir `/settings/cmd-template`).
   - Recherche par Bien ID dans les lots, historique, filtres Immeuble/Niveau/Local.
3. **Test avec le volume réel de l'inventaire** (potentiellement plusieurs milliers de biens) : vérifier les temps de réponse de la liste, de la recherche et de l'import — la pagination existe mais n'a été testée qu'avec de petits jeux de données pendant le développement.
4. **Test de bout en bout avec l'imprimante physique** (§6) : un fichier `.cmd` généré par l'application doit être lu et traité correctement par le logiciel d'impression.
5. Garder le processus manuel existant disponible en parallèle pendant une courte période, le temps de valider que tout fonctionne en conditions réelles.

---

## 10. Monitoring et exploitation

*(IT)*

1. **Logs** : l'application journalise via le module `logging` Python (erreurs non gérées, réinitialisation de base, modification du gabarit CMD). Sous systemd, ils sont consultables via :
   ```bash
   journalctl -u rfid-printing -f
   ```
   Prévoir une rétention/rotation cohérente avec la politique de logs de l'entreprise.
2. **Supervision** : la racine `GET /` répond `{"application": "RFID PRINTING", "status": "running"}` — à utiliser comme point de contrôle pour un outil de monitoring/uptime existant.
3. **Alerte** : définir qui est prévenu en cas d'échec du service (`Restart=on-failure` relance automatiquement, mais un échec répété doit remonter à quelqu'un).
4. **Nettoyage** : `backend/generated/` grossit indéfiniment (aucune purge automatique des vieux fichiers `.cmd`). Prévoir une politique de nettoyage périodique si le volume de lots générés est important, en gardant à l'esprit que le re-téléchargement d'un ancien lot dépend de la présence du fichier sur disque.

---

## 11. CI/CD (amélioration possible, non bloquante)

La CI GitHub Actions existante (`.github/workflows/tests.yml`) exécute déjà la suite de tests sur chaque push/PR. Le déploiement reste manuel (`git pull` + redémarrage du service). Automatiser le déploiement continu est possible une fois l'infrastructure cible connue (ex. étape supplémentaire dans le workflow qui se connecte au serveur et relance le service après un merge sur `main`) — à faire dans un second temps, ce n'est pas un prérequis à la première mise en production.

---

## Récapitulatif — checklist condensée

- [ ] 0. Décisions préalables tranchées (infra, intégration imprimante, domaine, comptes)
- [ ] 1. Serveur provisionné, Python installé, utilisateur système dédié
- [ ] 2. Application installée, `.env` configuré (`RFID_SECRET_KEY` réel, `COOKIE_SECURE=true`)
- [ ] 3. Service systemd en place, démarré sans `--reload`
- [ ] 4. Reverse proxy + HTTPS actif
- [ ] 5. Mot de passe admin par défaut changé, permissions fichiers vérifiées
- [ ] 6. Intégration imprimante définie et testée
- [ ] 7. Sauvegardes automatisées et restauration testée
- [ ] 8. Comptes utilisateurs réels créés
- [ ] 9. Recette complète effectuée dans l'environnement cible
- [ ] 10. Logs et supervision en place
- [ ] 11. (Optionnel) Déploiement continu
