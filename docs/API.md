# Référence rapide de l'API HAMARINO

URL locale : `http://127.0.0.1:8000` — Swagger auto-généré : `/docs`.

| Méthode | Chemin | But | Accès |
|---|---|---|---|
| GET | `/api/health` | Etat backend, OCR et fonctions optionnelles | public |
| POST | `/api/verify/text` | Analyse d'un texte `{ "text": "..." }` | public |
| POST | `/api/verify/link` | Récupération d'une page `{ "url": "https://..." }` | public |
| POST | `/api/verify/media` | OCR fichier multipart `file` | public |
| GET | `/api/history` | Liste d'analyses sauvegardées | public |
| GET | `/api/verifications/{id}` | Rapport complet sauvegardé | public |
| GET | `/api/report/{id}` | Rapport JSON simplifié | public |
| GET | `/api/sources` | Référentiel et compteur documents | public |
| POST | `/api/sources` | Définir une nouvelle source | clé admin |
| POST | `/api/corpus/document` | Indexer texte manuel + provenance | clé admin |
| POST | `/api/corpus/import-url` | Import HTML depuis la source reconnue | clé admin |
| POST | `/api/sources/refresh` | Actualisation RSS configurés | clé admin |

**Clé admin** : en-tête HTTP `X-Admin-Key: valeur_de_ADMIN_API_KEY`. Pas de clé dans le code mobile.

Exemple d'analyse :

```bash
curl -sS http://127.0.0.1:8000/api/verify/text \
  -H 'Content-Type: application/json' \
  -d '{"text":"Une publication affirme que le marché de Ville-Exemple ouvre vendredi à 8 heures."}'
```

Exemple OCR :

```bash
curl -sS http://127.0.0.1:8000/api/verify/media \
  -F 'file=@/chemin/vers/capture.png;type=image/png'
```

Exemple RAG de démonstration fictive : `cd backend && python -m app.demo_seed`, puis analyser un texte contenant "marché de Ville-Exemple". Le résultat ne sera jamais classé automatiquement "vrai".

**Limites** : pas de recherche Web générale dans la version de base. Le rapprochement porte sur les documents préalablement indexés et (si clé fournie) les résultats Fact Check Tools. Sans corpus ni Google API, l'analyse est fonctionnelle mais retourne nécessairement `a_verifier`.
