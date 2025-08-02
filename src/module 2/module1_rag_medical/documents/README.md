# Documents Médicaux

Ce dossier contient les documents sources pour la base de connaissances médicales.

## Structure recommandée

```
documents/
├── protocols/          # Protocoles médicaux
├── guidelines/         # Guides de bonnes pratiques
├── research/          # Articles de recherche
├── procedures/        # Procédures cliniques
├── specialties/       # Documents par spécialité
│   ├── cardiology/
│   ├── neurology/
│   ├── pediatrics/
│   └── ...
└── emergency/         # Protocoles d'urgence
```

## Formats supportés

- **PDF** (.pdf)
- **Word** (.docx)
- **Texte** (.txt)
- **Markdown** (.md)
- **HTML** (.html)

## Bonnes pratiques

1. **Nommage des fichiers**:
   - Utilisez des noms descriptifs
   - Incluez la spécialité si pertinent
   - Exemple: `cardio_hypertension_protocol_2024.pdf`

2. **Organisation**:
   - Classez par spécialité ou type de document
   - Maintenez une structure cohérente

3. **Métadonnées**:
   - Incluez des informations dans le nom de fichier
   - Date de création/mise à jour
   - Version du document

4. **Qualité du contenu**:
   - Assurez-vous que les documents sont lisibles
   - Évitez les documents scannés de mauvaise qualité
   - Préférez le texte sélectionnable

## Traitement automatique

Les documents placés dans ce dossier peuvent être traités automatiquement par le système RAG pour:

- Extraction du texte
- Segmentation en chunks
- Génération d'embeddings
- Indexation dans la base vectorielle
- Stockage des métadonnées

## Commandes utiles

```bash
# Traiter tous les nouveaux documents
python scripts/process_documents.py

# Traiter un document spécifique
python scripts/process_documents.py --file "path/to/document.pdf"

# Traiter par spécialité
python scripts/process_documents.py --specialty "cardiology"
```

## Sécurité et confidentialité

⚠️ **Important**: Assurez-vous que tous les documents respectent:
- Les règles de confidentialité médicale
- Les réglementations RGPD
- Les politiques de l'hôpital
- L'anonymisation des données patients

## Support

Pour toute question sur l'ajout ou le traitement de documents, contactez l'équipe technique du projet RAG médical.