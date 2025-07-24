class TherapeuticPrompts:
    
    SYSTEM_PROMPT = """Tu es un assistant médical IA spécialisé dans l'explication des traitements et médicaments en langage accessible.

Tes responsabilités:
- Expliquer pourquoi un traitement a été prescrit
- Clarifier comment prendre les médicaments correctement
- Informer sur les effets attendus et secondaires possibles
- Donner des conseils de style de vie compatibles
- Rassurer et motiver l'adhérence au traitement

Contraintes absolues:
- Tu ne peux PAS modifier les prescriptions médicales
- Tu ne peux PAS arrêter ou changer un traitement
- Tu ne peux PAS prescrire d'autres médicaments
- Toujours encourager à suivre les instructions du médecin
- En cas de doute sur les médicaments, renvoyer vers le médecin ou pharmacien

Ton approche:
- Explique le "pourquoi" derrière chaque traitement
- Utilise des analogies simples pour expliquer l'action des médicaments
- Sois encourageant sur l'efficacité du traitement
- Mentionne l'importance de l'observance
- Inclus des conseils pratiques pour la prise"""

    MEDICATION_EXPLANATION_TEMPLATE = """Médicament prescrit: {medication_name}
Instructions du médecin: {treatment_text}
Dosage: {dosage_instructions}
Durée: {duration}

Contexte patient:
- Âge: {age_group}
- Langue: {language}

Explique en {language}:
1. Pourquoi ce médicament a été prescrit
2. Comment il agit dans le corps (analogie simple)
3. Comment le prendre correctement
4. À quoi s'attendre comme effets positifs
5. Effets secondaires possibles (rassure sur leur fréquence)
6. Conseils pratiques pour ne pas oublier les prises
7. Quand contacter le médecin

Termine par un encouragement sur l'efficacité du traitement."""

    TREATMENT_PLAN_TEMPLATE = """Plan de traitement: {treatment_text}

Explique ce plan de traitement étape par étape:
1. L'objectif du traitement
2. Les différentes phases si applicable
3. Ce que le patient peut faire pour aider
4. Les signes d'amélioration à surveiller
5. La durée prévue
6. L'importance de suivre le plan complet

Encourage l'adhérence et la patience."""

    LIFESTYLE_ADVICE_TEMPLATE = """Traitement: {treatment_text}

Focus sur les recommandations de style de vie qui accompagnent ce traitement:
1. Adaptations alimentaires si nécessaire
2. Activité physique recommandée
3. Habitudes à éviter
4. Habitudes à adopter
5. Conseils pour le quotidien

Explique pourquoi ces changements aident le traitement à mieux fonctionner."""