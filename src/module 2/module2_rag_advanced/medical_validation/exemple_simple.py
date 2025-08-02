#!/usr/bin/env python3
"""
Exemple Simple d'Utilisation du Système de Documentation des Preuves

Ce script montre comment analyser un seul article médical
de manière simple et directe.

Auteur: Équipe Hackathon Hôpital Général de Douala
"""

from evidence_documenter import EvidenceDocumenter, CitationFormat, EvidenceLevel

# 1. CRÉATION D'UN ARTICLE MÉDICAL EXEMPLE
print("🏥 EXEMPLE SIMPLE - DOCUMENTATION DES PREUVES MÉDICALES")
print("=" * 60)

# Contenu de l'article à analyser
contenu_article = """
Efficacité et Sécurité de l'Artéméther-Luméfantrine dans le Traitement
du Paludisme Non Compliqué chez l'Adulte au Cameroun

Résumé:
Objectif: Évaluer l'efficacité et la sécurité de l'artéméther-luméfantrine (AL)
dans le traitement du paludisme non compliqué à P. falciparum chez l'adulte.

Méthodes: Essai contrôlé randomisé en double aveugle mené à l'Hôpital Général
de Douala. 500 patients adultes avec paludisme confirmé ont été randomisés pour
recevoir soit AL (n=250) soit quinine (n=250). Critère principal: guérison
parasitologique à J28.

Résultats: Le taux de guérison était de 95.2% (IC95%: 92.1-97.3) avec AL contre
87.6% (IC95%: 83.2-91.0) avec quinine (p<0.01). Les effets secondaires étaient
moins fréquents avec AL (15% vs 32%, p<0.001).

Conclusion: L'artéméther-luméfantrine est efficace et bien tolérée pour le
traitement du paludisme non compliqué chez l'adulte au Cameroun.
"""

# Métadonnées de l'article
metadonnees = {
    "title": "Efficacité et Sécurité de l'Artéméther-Luméfantrine dans le Traitement du Paludisme",
    "authors": ["Dr. Jean Mbarga", "Dr. Marie Nkodo", "Prof. Paul Essomba"],
    "journal": "The Lancet Infectious Diseases",
    "year": 2024,
    "volume": "24",
    "issue": "3",
    "pages": "345-352",
    "doi": "10.1016/S1473-3099(24)00123-4"
}

# 2. CONFIGURATION DU SYSTÈME DE DOCUMENTATION
config = {
    "citation_format": CitationFormat.VANCOUVER,  # Format de citation
    "require_citations": True,                   # Exiger des citations
    "track_provenance": True,                    # Tracer la provenance
    "version_control": True                      # Contrôle de version
}

# 3. CRÉATION DU SYSTÈME
print("\n📋 Création du système de documentation...")
documenter = EvidenceDocumenter(config)

# 4. DOCUMENTATION AUTOMATIQUE
print("\n🔍 Analyse de l'article médical...")
rapport = documenter.document_source(
    content=contenu_article,
    source_metadata=metadonnees,
    content_id="article_exemple_001"
)

# 5. AFFICHAGE DES RÉSULTATS
print("\n✅ RÉSULTATS DE L'ANALYSE:")
print("=" * 60)

# Extraction des informations principales
source = rapport.evidence_sources[0]

print(f"📊 Niveau de preuve: {source.evidence_level.value}")
print(f"🔬 Type d'étude: {source.study_design.value}")
print(f"⭐ Score qualité: {source.quality_score:.3f}/1.0")
print(f"👥 Taille échantillon: {source.sample_size or 'Non détectée'}")

if source.statistical_significance is not None:
    print(f"📈 Significativité statistique: {'Oui' if source.statistical_significance else 'Non'}")

if source.confidence_interval:
    print(f"📏 Intervalle de confiance: {source.confidence_interval}")

# 6. CITATION BIBLIOGRAPHIQUE
print("\n📚 CITATIONS BIBLIOGRAPHIQUES:")
print("=" * 60)

# Générer des citations dans différents formats
vancouver = documenter.format_citation(source.citation, CitationFormat.VANCOUVER)
apa = documenter.format_citation(source.citation, CitationFormat.APA)
harvard = documenter.format_citation(source.citation, CitationFormat.HARVARD)

print(f"Vancouver: {vancouver}")
print(f"APA: {apa}")
print(f"Harvard: {harvard}")

# 7. RECOMMANDATIONS BASÉES SUR LES PREUVES
print("\n💡 RECOMMANDATIONS:")
print("=" * 60)

print(f"Force de recommandation: {rapport.evidence_summary.strength_of_recommendation}")
print(f"Qualité des preuves: {rapport.evidence_summary.quality_of_evidence}")

print("\nRecommandations spécifiques:")
for i, rec in enumerate(rapport.evidence_summary.recommendations, 1):
    print(f"  {i}. {rec}")

if rapport.evidence_summary.limitations:
    print("\nLimitations:")
    for i, lim in enumerate(rapport.evidence_summary.limitations, 1):
        print(f"  {i}. {lim}")

# 8. RECHERCHE PAR NIVEAU DE PREUVE
print("\n🔎 RECHERCHE PAR NIVEAU DE PREUVE:")
print("=" * 60)

# Rechercher toutes les sources de niveau II (essais contrôlés randomisés)
niveau_ii = documenter.search_by_evidence_level(EvidenceLevel.LEVEL_II)
print(f"Sources de niveau II (ECR): {len(niveau_ii)}")

# 9. EXPORT DES DONNÉES
print("\n💾 EXPORT DES DONNÉES:")
print("=" * 60)

# Exporter toutes les données au format JSON
fichier_export = "documentation_exemple_simple.json"
if documenter.export_data(fichier_export):
    print(f"Données exportées avec succès: {fichier_export}")
else:
    print("Erreur lors de l'export des données")

print("\n✅ EXEMPLE TERMINÉ")
print("=" * 60)
print("Pour analyser vos propres articles médicaux:")
print("1. Remplacez 'contenu_article' par le texte de votre article")
print("2. Modifiez 'metadonnees' avec les informations de votre source")
print("3. Exécutez le script pour obtenir l'analyse automatique")
print("4. Consultez le fichier JSON exporté pour les détails complets")