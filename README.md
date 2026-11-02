# HAMARINO — Hackathon FANILO / IFM

**Version livrée : prototype complet de démonstration, React Native + Expo SDK 55, backend FastAPI, OCR, RAG lexical, suivi des sources.**

**A lire avant tout :** ce ZIP contient les **sources** ; les dépendances Python/JavaScript ne sont pas embarquées. Une connexion Internet est nécessaire pour les installer. L'app mobile n'est pas un `.apk` précompilé. Un backend doit être exécuté sur le PC/serveur : Expo Go ne peut pas exécuter du Python ou Tesseract.

## Démarrage rapide sur Fedora

### 1. Prérequis

```bash
sudo dnf install -y python3 python3-pip nodejs npm tesseract tesseract-langpack-fra tesseract-langpack-eng
node --version
python3 --version
tesseract --list-langs
```

Expo SDK 55 exige une version de Node.js prise en charge (par exemple **Node 22.13+**, ou Node 20.19.4+). Pour OCR Malagasy, installer les données de langue correspondantes si disponibles pour votre distribution ; le français + anglais suffit pour la démo.

### 2. Lancer le backend (terminal 1)

```bash
cd IFM_HAMARINO_SDK55/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# IMPORTANT : changer ADMIN_API_KEY dans backend/.env.
# Démarrage : la base SQLite et les sources de référence sont créées automatiquement.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ouvrir `http://127.0.0.1:8000/docs` pour voir et essayer l'API (Swagger).

Vérifier le serveur depuis le PC :

```bash
curl http://127.0.0.1:8000/api/health
```

### 3. Préparer la connexion du téléphone

PC et téléphone **sur le même Wi-Fi** (ou partage de connexion compatible). Sur Fedora :

```bash
hostname -I
```

Repérer l'IP locale du PC, par exemple `192.168.1.42`. L'API du téléphone sera :

`http://192.168.1.42:8000`

> Sur le téléphone, **ne PAS utiliser `localhost` ni `127.0.0.1`** : ces noms désignent le téléphone, pas Fedora.

Si Fedora bloque le port via firewalld, l'autoriser **uniquement sur le réseau privé de confiance**. Exemple temporaire, à éviter sur un Wi-Fi public :

```bash
sudo firewall-cmd --add-port=8000/tcp
# À retirer après la démonstration :
sudo firewall-cmd --remove-port=8000/tcp
```

### 4. Lancer l'application mobile (terminal 2)

```bash
cd IFM_HAMARINO_SDK55/mobile
cp .env.example .env
# Editer mobile/.env ; remplacer l'IP d'exemple par l'IP réelle du PC Fedora :
nano .env
npm install
# Aligne automatiquement les versions des bibliothèques avec SDK 55 :
npx expo install --fix
npx expo start --lan -c
```

Sur Android, installer **Expo Go compatible SDK 55** à partir de **https://expo.dev/go**, puis scanner le QR affiché par Expo. Vérifier que la version sélectionnée est SDK 55. Sur iPhone, Expo Go standard de l'App Store ne prend pas en charge SDK 55 ; voir la section « Cas de l'iPhone ».

Dans l'app : **Réglages → Tester la connexion**, puis **Analyser → Texte / Lien / Capture**.

Si l'on modifie `.env`, relancer `npx expo start --lan -c`. L'URL peut aussi être modifiée temporairement dans **Réglages**.

## Démo hors connexion aux API externes (pour le jury)

Le démarrage du backend crée le **catalogue des sources** mais **pas de faux articles présentés comme réels**. Pour montrer le RAG local sans accès externe, charger un corpus EXPLICITEMENT FICTIF :

```bash
cd IFM_HAMARINO_SDK55/backend
source .venv/bin/activate
python -m app.demo_seed
```

Puis saisir dans le mobile :

> Le marché de Ville-Exemple ouvre le vendredi à 8 heures et ferme à 16 heures.

Le backend remonte le passage fictif correspondant et conclut **« À vérifier »**, car une similarité de texte ne suffit pas pour établir la vérité. Les documents `example.org/demo/*` sont imaginaires et ne doivent jamais être cités comme preuves réelles.

## Ajouter de VRAIES sources et indexer des documents

Le corpus doit être constitué **avant** qu'une vérification puisse retrouver des passages pertinents. Des domaines de référence sont déjà déclarés (RFI Afrique, Météo Madagascar, AFP Factuel, OMS). Le statut de référence d'un organisme ne garantit pas l'exactitude d'un article.

### Méthode 1 — Actualiser un flux RSS (connectivité Internet nécessaire)

Le fichier `backend/.env` contient `ADMIN_API_KEY`. Prenez la valeur que vous y avez mise.

```bash
curl -X POST http://127.0.0.1:8000/api/sources/refresh \
  -H 'X-Admin-Key: VOTRE_CLE_ADMIN'
```

Cette opération essaye notamment le flux RSS RFI Afrique et indexe ses **titres + résumés**, en affichant les erreurs individuelles. Ce n'est pas une exploration libre du Web.

### Méthode 2 — Importer une page institutionnelle (le domaine doit correspondre)

Exemple à essayer lorsque l'accès réseau fonctionne :

```bash
curl -X POST http://127.0.0.1:8000/api/corpus/import-url \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Key: VOTRE_CLE_ADMIN' \
  -d '{"source_id":"meteomadagascar","url":"https://www.meteomadagascar.mg/"}'
```

Le lecteur HTML est simplifié : certains sites dynamiques, pages inaccessibles ou redirections sont bloqués. Dans ce cas, passer par l'import manuel ci-dessous.

### Méthode 3 — Ajouter un extrait vérifié par le journaliste

Via `http://127.0.0.1:8000/docs` → `POST /api/corpus/document`, renseigner `source_id`, `url`, `title`, `content` et éventuellement `published_at` ; envoyer l'en-tête `X-Admin-Key`. Le contenu doit provenir de la vraie source citée. **Ne jamais inventer un passage.**

Vous pouvez ajouter un nouveau domaine via `POST /api/sources`.

## Fonctionnalités livrées

| Domaine | Livré |
|---|---|
| Application React Native TypeScript, Expo SDK 55 | Oui (code source) |
| Analyse d'une affirmation textuelle | Oui |
| Lecture d'URL publique (HTML serveur) | Oui, suivant accessibilité |
| Capture caméra ou galerie (JPG/PNG/WEBP) | Oui |
| OCR Tesseract sur serveur, langues installées | Oui |
| PDF contenant du texte (API seulement) | Oui ; pas OCR d'un PDF scanné |
| RAG local : recherche TF-IDF, extraits/citations/URL | Oui |
| Actualisation RSS (selon la réponse du site) | Oui |
| Fact-check tiers Google Fact Check Tools | Optionnel : nécessite une clé valide |
| Extraction d'affirmation via LLM OpenAI | Optionnel : nécessite une clé valide |
| Historique SQLite, rapport JSON et partage texte | Oui |
| Validation humaine de chaque conclusion | Obligatoire en pratique |
| Véritable modèle de classification fine-tuné | Non ; non justifiable sans corpus annoté |
| Détection automatique universelle vrai/faux | Non ; une telle garantie serait trompeuse |
| Déploiement public, authentification multi-utilisateurs | Non, prototype de hackathon |

### Statuts affichés

- **À vérifier** : absence de revue tierce concluante, résultat RAG lexical seulement, ou évaluations externes contradictoires.
- **Corroboré par fact-check** / **Contesté par fact-check** : uniquement lorsqu'une revue tierce disponible via Google Fact Check API a fourni un avis interprétable. Attention : l'API effectue une recherche de similarité de *claims*, donc la correspondance exacte doit être vérifiée manuellement !

## Structure

```text
IFM_HAMARINO_SDK55/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── app/
│   │   ├── main.py            # FastAPI / endpoints
│   │   ├── db.py              # SQLite / sources / historique
│   │   ├── fetcher.py         # URLs publiques / extraction HTML
│   │   ├── ocr.py             # Tesseract / PDF texte
│   │   ├── ai.py              # Extraction claim avec ou sans LLM
│   │   ├── rag.py             # Similarité TF-IDF / citations
│   │   ├── factcheck.py       # Fact Check Tools API (facultatif)
│   │   ├── verification.py    # Agrégation et garde-fous verdicts
│   │   └── demo_seed.py       # Corpus fictif et explicitement marqué
│   └── tests/
└── mobile/
    ├── App.tsx                # UI React Native
    ├── src/{api,types,theme}.ts
    ├── app.json
    ├── package.json
    ├── tsconfig.json
    └── .env.example
```

## Tests

```bash
cd IFM_HAMARINO_SDK55/backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Environnement de préparation : **8 tests sur 8 ont réussi**. Cela ne remplace ni un test d'intégration avec Expo Go sur un téléphone, ni une campagne OCR avec de vraies captures. Les dépendances `npm` n'étaient pas téléchargeables dans l'environnement de génération ; `npm install`, `expo-doctor` et les tests sur appareil doivent être faits sur votre machine.

## Cas de l'iPhone et d'Expo SDK 55

En 2026, Expo Go distribué sur l'App Store iOS s'arrête au SDK 54 ; il n'exécute pas un projet SDK 55. Pour un **iPhone physique**, suivre les instructions officielles de [`eas go` / TestFlight](https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/) ou obtenir une version Expo Go SDK 55 appropriée via un mode de distribution autorisé. Cette procédure peut nécessiter une adhésion Apple Developer pour TestFlight. Sur **Android**, le sélecteur SDK est sur https://expo.dev/go.

Alternative uniquement si vous acceptez plus tard un changement de SDK : migrer le projet vers SDK 54 pour l'Expo Go standard iOS, mais **le ZIP livré reste SDK 55**, comme demandé.

## Problèmes fréquents

1. **Network request failed** : backend non démarré, IP incorrecte, `localhost` utilisé dans le mobile, ports bloqués ou réseaux différents. Tester `http://IP_DU_PC:8000/api/health` dans le navigateur du téléphone.
2. **OCR 503** : vérifier `tesseract --list-langs`, les packs `fra`/`eng` et le binaire Tesseract.
3. **Source vide** : faire `python -m app.demo_seed` pour tester en mode fictif, ou indexer de vraies sources via RSS/import.
4. **Lien inaccessible** : les sites sociaux peuvent exiger connexion ou JavaScript, ou rediriger ; copier le texte ou faire une capture.
5. **Expo Go incompatibilité** : installation de l'application Expo Go compatible **SDK 55** requise, particulièrement sur iOS.
6. **Module not found / conflit npm** : `npm install && npx expo install --fix && npx expo-doctor@latest`, puis `npx expo start -c`.

## Protection des données et licence

- Ne pas collecter de données sensibles personnelles sans consentement. Le texte envoyé est conservé dans la base locale SQLite pour l'historique (pas les images brutes).
- Clés API **côté serveur seulement** (`backend/.env`), jamais `EXPO_PUBLIC_*`.
- Les endpoints de vérification/historique sont ouverts **pour la démo**, à protéger avant un déploiement public (authentification, HTTPS, limitation de débit, filtrage CORS, purge, politique de confidentialité).
- Les URL externes sont filtrées (pas de `localhost`, IP privées ou ports non usuels), les redirections bloquées. Un audit de sécurité reste nécessaire avant exposition publique.
- Stack : React Native (MIT), Expo (MIT), FastAPI (MIT), Tesseract (Apache-2.0), scikit-learn (BSD-3-Clause), SQLite (domaine public) ; vérifier les licences exactes des autres dépendances avant diffusion commerciale. Respecter les droits des contenus indexés.

## Pour le hackathon

La bonne promesse : **HAMARINO assiste le journaliste en retrouvant le texte d'une capture, en rapprochant une affirmation de sources consultables et en conservant les éléments nécessaires à une vérification humaine.** Le système ne prétend ni détecter toutes les intox, ni attribuer un « score de vérité » à une simple ressemblance de mots.
