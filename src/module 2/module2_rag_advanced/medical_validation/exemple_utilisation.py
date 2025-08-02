#!/usr/bin/env python3
"""
Exemple d'Utilisation Normale du Système de Documentation des Preuves

Cet exemple montre comment utiliser le système de documentation
pour analyser des articles médicaux dans un contexte réel.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue - Validation Médicale
"""

import os
import json
from pathlib import Path
from evidence_documenter import EvidenceDocumenter, CitationFormat

def analyser_article_medical(chemin_fichier: str, metadonnees: dict):
    """
    Analyse un article médical et génère sa documentation
    
    Args:
        chemin_fichier: Chemin vers le fichier à analyser
        metadonnees: Informations sur la source
        
    Returns:
        dict: Rapport d'analyse complet
    """
    print(f"📄 Analyse de: {os.path.basename("D:\cours")}")
    
    # Configuration du système
    config = {
        "citation_format": CitationFormat.VANCOUVER,
        "require_citations": True,
        "track_provenance": True,
        "version_control": True
    }
    
    # Création du documenter
    documenter = EvidenceDocumenter(config)
    
    # Lecture du fichier
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as f:
            contenu = f.read()
    except Exception as e:
        print(f"❌ Erreur lecture fichier: {e}")
        return None
    
    # Documentation automatique
    try:
        rapport = documenter.document_source(
            content=contenu,
            source_metadata=metadonnees,
            content_id=f"article_{os.path.basename(chemin_fichier).replace('.', '_')}"
        )
        
        # Extraction des résultats
        source = rapport.evidence_sources[0]
        
        resultats = {
            "fichier": os.path.basename(chemin_fichier),
            "niveau_preuve": source.evidence_level.value,
            "type_etude": source.study_design.value,
            "score_qualite": round(source.quality_score, 3),
            "taille_echantillon": source.sample_size,
            "significativite_statistique": source.statistical_significance,
            "intervalle_confiance": source.confidence_interval,
            "risque_biais": source.bias_risk,
            "citation_vancouver": documenter.format_citation(source.citation, CitationFormat.VANCOUVER),
            "recommandations": rapport.evidence_summary.recommendations,
            "limitations": rapport.evidence_summary.limitations,
            "force_recommandation": rapport.evidence_summary.strength_of_recommendation,
            "qualite_preuves": rapport.evidence_summary.quality_of_evidence
        }
        
        # Affichage des résultats
        print(f"   🎯 Niveau de preuve: {resultats['niveau_preuve']}")
        print(f"   🔬 Type d'étude: {resultats['type_etude']}")
        print(f"   ⭐ Score qualité: {resultats['score_qualite']}/1.0")
        print(f"   👥 Échantillon: {resultats['taille_echantillon'] or 'Non spécifié'}")
        print(f"   📊 Significativité: {resultats['significativite_statistique'] or 'Non détectée'}")
        print(f"   💪 Recommandation: {resultats['force_recommandation']}")
        
        return resultats
        
    except Exception as e:
        print(f"❌ Erreur analyse: {e}")
        return None

def exemple_article_paludisme():
    """
    Exemple avec un article sur le paludisme
    """
    print("\n🦠 EXEMPLE 1: Article sur le Paludisme")
    print("=" * 50)
    
    # Création d'un fichier exemple
    contenu_exemple = """
Efficacité de l'Artéméther-Luméfantrine dans le Traitement du Paludisme Simple:
Étude Randomisée Contrôlée Multicentrique

Résumé:
Objectif: Évaluer l'efficacité et la sécurité de l'artéméther-luméfantrine (AL) 
comparée à la quinine dans le traitement du paludisme simple à P. falciparum.

Méthodes: Essai contrôlé randomisé en double aveugle mené dans 5 centres 
hospitaliers du Cameroun. 1,200 patients âgés de 18-65 ans avec paludisme 
simple confirmé ont été randomisés (1:1) pour recevoir soit AL (n=600) soit 
quinine (n=600). Le critère principal était la guérison parasitologique à J28.

Résultats: Le taux de guérison était significativement supérieur avec AL 
(97.1%, IC95%: 95.2-98.4) comparé à la quinine (89.3%, IC95%: 86.8-91.5, 
p<0.001). Le risque relatif de guérison était de 1.09 (IC95%: 1.05-1.13). 
Les effets secondaires étaient moins fréquents avec AL (12.3% vs 28.7%, p<0.001).

Conclusion: L'artéméther-luméfantrine démontre une efficacité supérieure 
et un meilleur profil de sécurité comparé à la quinine pour le traitement 
du paludisme simple. Ces résultats supportent son utilisation en première ligne.

Mots-clés: paludisme, artéméther-luméfantrine, essai contrôlé randomisé, 
P. falciparum, Cameroun

Financement: Organisation Mondiale de la Santé, Ministère de la Santé du Cameroun
Conflits d'intérêts: Aucun déclaré
    """
    
    # Métadonnées de l'article
    metadonnees = {
        "title": "Efficacité de l'Artéméther-Luméfantrine dans le Traitement du Paludisme Simple",
        "authors": [
            "Dr. Aminata Sow", 
            "Prof. Jean-Claude Mbarga", 
            "Dr. Marie Dubois",
            "Dr. Paul Nguema"
        ],
        "journal": "The Lancet Global Health",
        "year": 2024,
        "volume": "12",
        "issue": "3",
        "pages": "e234-e242",
        "doi": "10.1016/S2214-109X(24)00123-4",
        "pmid": "38456789",
        "url": "https://www.thelancet.com/journals/langlo/article/PIIS2214-109X(24)00123-4/fulltext",
        "institution": "Hôpital Général de Douala, Cameroun",
        "funding": "OMS, Ministère Santé Cameroun",
        "conflicts": "Aucun"
    }
    
    # Sauvegarde du fichier exemple
    fichier_exemple = "article_paludisme_exemple.txt"
    with open(fichier_exemple, 'w', encoding='utf-8') as f:
        f.write(contenu_exemple)
    
    # Analyse
    resultats = analyser_article_medical(fichier_exemple, metadonnees)
    
    if resultats:
        print(f"\n📋 Citation générée:")
        print(f"   {resultats['citation_vancouver']}")
        
        print(f"\n💡 Recommandations:")
        for rec in resultats['recommandations'][:3]:
            print(f"   • {rec}")
            
        if resultats['limitations']:
            print(f"\n⚠️ Limitations:")
            for lim in resultats['limitations'][:2]:
                print(f"   • {lim}")
    
    # Nettoyage
    if os.path.exists(fichier_exemple):
        os.remove(fichier_exemple)
    
    return resultats

def exemple_revue_systematique():
    """
    Exemple avec une revue systématique
    """
    print("\n📚 EXEMPLE 2: Revue Systématique")
    print("=" * 50)
    
    contenu_revue = """
Prévention du Paludisme chez la Femme Enceinte en Afrique Subsaharienne:
Revue Systématique et Méta-analyse

Objectif: Évaluer l'efficacité des interventions de prévention du paludisme 
chez la femme enceinte en Afrique subsaharienne.

Méthodes: Recherche systématique dans PubMed, Embase, Cochrane Library et 
African Index Medicus (janvier 2000 - décembre 2023). Inclusion d'essais 
contrôlés randomisés évaluant les moustiquaires imprégnées d'insecticide (MII), 
le traitement préventif intermittent (TPI) et les combinaisons.

Résultats: 24 études incluses (n=45,678 femmes enceintes). Les MII réduisent 
le risque de paludisme de 62% (RR=0.38, IC95%: 0.28-0.52, I²=15%). Le TPI 
avec sulfadoxine-pyriméthamine réduit le risque de 58% (RR=0.42, IC95%: 
0.31-0.57, I²=22%). La combinaison MII+TPI offre une protection de 78% 
(RR=0.22, IC95%: 0.15-0.32, I²=8%).

Conclusion: La combinaison MII+TPI est l'approche la plus efficace pour 
la prévention du paludisme chez la femme enceinte. Recommandation forte 
basée sur des preuves de haute qualité.

Hétérogénéité: Faible à modérée entre les études
Biais de publication: Test d'Egger non significatif (p=0.23)
Qualité des preuves: Haute (GRADE)
    """
    
    metadonnees_revue = {
        "title": "Prévention du Paludisme chez la Femme Enceinte: Revue Systématique",
        "authors": [
            "Dr. Fatima Al-Hassan",
            "Prof. Sarah Johnson",
            "Dr. Emmanuel Kouam"
        ],
        "journal": "Cochrane Database of Systematic Reviews",
        "year": 2024,
        "volume": "2",
        "doi": "10.1002/14651858.CD013456.pub2",
        "pmid": "38234567",
        "study_type": "systematic_review",
        "grade_assessment": "high"
    }
    
    fichier_revue = "revue_systematique_exemple.txt"
    with open(fichier_revue, 'w', encoding='utf-8') as f:
        f.write(contenu_revue)
    
    resultats = analyser_article_medical(fichier_revue, metadonnees_revue)
    
    if os.path.exists(fichier_revue):
        os.remove(fichier_revue)
    
    return resultats

def exemple_serie_cas():
    """
    Exemple avec une série de cas
    """
    print("\n🏥 EXEMPLE 3: Série de Cas Cliniques")
    print("=" * 50)
    
    contenu_serie = """
Prise en Charge du Paludisme Grave par Artésunate Intraveineux:
Série de 45 Cas à l'Hôpital Général de Douala

Introduction: Le paludisme grave reste une urgence médicale avec mortalité 
élevée. L'artésunate IV est recommandé en première ligne.

Patients et Méthodes: Série rétrospective de 45 patients adultes admis 
pour paludisme grave (janvier 2023 - décembre 2023). Critères: parasitémie 
>4%, troubles de conscience, insuffisance rénale ou détresse respiratoire.
Traitement: artésunate IV 2.4mg/kg à H0, H12, H24 puis quotidien.

Résultats: Âge moyen 34±12 ans, 60% hommes. Parasitémie moyenne 8.2±3.1%. 
Guérison complète: 38/45 (84.4%). Décès: 7/45 (15.6%). Durée moyenne 
d'hospitalisation: 7.3±2.8 jours. Clairance parasitaire: 48±12 heures.
Complications: insuffisance rénale transitoire (n=3), convulsions (n=2).

Conclusion: L'artésunate IV montre une bonne efficacité dans cette série 
avec mortalité acceptable. Surveillance rénale recommandée.

Limitations: Série monocentrique, effectif limité, pas de groupe contrôle.
    """
    
    metadonnees_serie = {
        "title": "Prise en Charge du Paludisme Grave par Artésunate: Série de 45 Cas",
        "authors": [
            "Dr. Martin Dupont",
            "Dr. Célestine Mballa"
        ],
        "journal": "Médecine Tropicale et Santé Internationale",
        "year": 2024,
        "volume": "34",
        "pages": "78-85",
        "institution": "Hôpital Général de Douala",
        "study_type": "case_series"
    }
    
    fichier_serie = "serie_cas_exemple.txt"
    with open(fichier_serie, 'w', encoding='utf-8') as f:
        f.write(contenu_serie)
    
    resultats = analyser_article_medical(fichier_serie, metadonnees_serie)
    
    if os.path.exists(fichier_serie):
        os.remove(fichier_serie)
    
    return resultats

def generer_rapport_complet(resultats_liste: list):
    """
    Génère un rapport comparatif de tous les articles analysés
    """
    print("\n📊 RAPPORT COMPARATIF")
    print("=" * 50)
    
    if not resultats_liste:
        print("Aucun résultat à analyser")
        return
    
    # Tableau comparatif
    print(f"{'Article':<30} {'Niveau':<8} {'Type':<20} {'Qualité':<8} {'Recommandation':<12}")
    print("-" * 85)
    
    for res in resultats_liste:
        if res:
            fichier = res['fichier'][:27] + "..." if len(res['fichier']) > 30 else res['fichier']
            print(f"{fichier:<30} {res['niveau_preuve']:<8} {res['type_etude'][:17]:<20} {res['score_qualite']:<8} {res['force_recommandation']:<12}")
    
    # Statistiques globales
    niveaux = [r['niveau_preuve'] for r in resultats_liste if r]
    scores = [r['score_qualite'] for r in resultats_liste if r]
    
    print(f"\n📈 Statistiques:")
    print(f"   Articles analysés: {len(resultats_liste)}")
    print(f"   Score qualité moyen: {sum(scores)/len(scores):.3f}")
    print(f"   Distribution niveaux: {dict(zip(*zip(*[(n, niveaux.count(n)) for n in set(niveaux)])))}") 
    
    # Sauvegarde du rapport
    rapport_final = {
        "timestamp": "2024-12-20T10:30:00",
        "articles_analyses": len(resultats_liste),
        "score_qualite_moyen": sum(scores)/len(scores),
        "distribution_niveaux": {n: niveaux.count(n) for n in set(niveaux)},
        "details_articles": resultats_liste
    }
    
    with open("rapport_analyse_complete.json", 'w', encoding='utf-8') as f:
        json.dump(rapport_final, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Rapport sauvegardé: rapport_analyse_complete.json")

def main():
    """
    Fonction principale - Exemples d'utilisation normale
    """
    print("🏥 SYSTÈME DE DOCUMENTATION DES PREUVES MÉDICALES")
    print("Hôpital Général de Douala - Exemples d'Utilisation")
    print("=" * 60)
    
    resultats = []
    
    # Exemple 1: Article ECR sur paludisme
    try:
        res1 = exemple_article_paludisme()
        resultats.append(res1)
    except Exception as e:
        print(f"Erreur exemple 1: {e}")
    
    # Exemple 2: Revue systématique
    try:
        res2 = exemple_revue_systematique()
        resultats.append(res2)
    except Exception as e:
        print(f"Erreur exemple 2: {e}")
    
    # Exemple 3: Série de cas
    try:
        res3 = exemple_serie_cas()
        resultats.append(res3)
    except Exception as e:
        print(f"Erreur exemple 3: {e}")
    
    # Rapport final
    generer_rapport_complet(resultats)
    
    print("\n✅ Analyse terminée avec succès!")
    print("\n💡 Pour analyser vos propres fichiers:")
    print("   1. Placez vos articles dans un dossier")
    print("   2. Adaptez les métadonnées selon vos sources")
    print("   3. Utilisez la fonction analyser_article_medical()")
    print("   4. Consultez le rapport JSON généré")

if __name__ == "__main__":
    main()