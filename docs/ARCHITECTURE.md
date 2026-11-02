# Architecture fonctionnelle et technique

```
[Android/iOS — React Native Expo SDK 55]
  ├── Texte ─────────── POST /api/verify/text
  ├── URL ───────────── POST /api/verify/link
  └── Camera / Galerie ─ POST /api/verify/media (multipart)
                              |
                              v
                    [FastAPI sur le PC]
                       |
         ┌─────────────┼─────────────────────┐
         v             v                     v
     OCR Tesseract  Extracteur URL       Extraction claim
         |          BeautifulSoup        Locale / OpenAI opt.
         └─────────────┴─────────────────────┘
                       |
                    [RAG TF-IDF]
                    corpus SQLite
                       |
             Extraits + URL + date
                       |
              Google Fact Check opt.
                       |
              Rapport avec réserves
                       |
              Historique SQLite
```

## Pourquoi ce n'est pas un classificateur de « vérité »

Le RAG cherche des **passages proches** dans des documents indexés. Une source crédible peut être citée hors contexte, une affirmation peut comporter une négation, et la similarité TF-IDF est particulièrement mauvaise pour la contradiction et les nombres. L'application préfère afficher **« À vérifier »** tant qu'un véritable fact-check externe avec évaluation explicite n'est pas trouvé.

L'API facultative Google Fact Check Tools renvoie les notes textuelles de vérifications déjà publiées. Leur affichage aide le journaliste ; la correspondance de la formulation et de la date doit encore être contrôlée. L'appel LLM OpenAI, s'il est activé, **n'extrait qu'une affirmation**, et ne prononce pas le verdict final.

## OCR

Le mobile envoie l'image à `POST /api/verify/media`. FastAPI valide le format et la taille. Pillow corrige l'orientation et augmente le contraste. Tesseract extrait le texte en langues disponibles (`fra`, `eng`, `mlg`). Le backend ne stocke que le texte extrait dans son historique, pas les octets originaux de l'image.

## Sources et index

Les sources sont gérées dans la base SQLite ; la table `documents` stocke titre, URL, date de publication disponible, date de récupération, texte et nature (`article`, `rss_summary`, `manuel`, `demo`). Le rafraîchissement RSS est volontairement manuel et protégé par clé d'administration. Il ne tourne pas automatiquement en arrière-plan.

## Extension après le hackathon

Pour une version professionnelle : comptes journalistes et responsables, validation éditoriale, collecte de sources en tâche planifiée, stockage structuré de provenance, vérification de contradictions à partir d'un corpus annoté, véritable modèle de recherche multilingue français/malagasy, évaluation sur des faits documentés, chiffrement des données, journal d'audit, protection des endpoints et déploiement HTTPS.
