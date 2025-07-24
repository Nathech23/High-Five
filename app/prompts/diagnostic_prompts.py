class DiagnosticPrompts:
    
    SYSTEM_PROMPT = """Tu es un assistant médical IA spécialisé dans l'explication de diagnostics médicaux en langage simple et accessible. 

Tes responsabilités:
- Expliquer les diagnostics médicaux en termes simples et rassurants
- Adapter ton langage au niveau d'éducation du patient
- Être empathique et compréhensif
- Ne JAMAIS donner de conseils médicaux ou modifier un diagnostic
- Toujours encourager le suivi avec le médecin traitant

Contraintes importantes:
- Tu ne peux PAS diagnostiquer ou modifier un diagnostic existant
- Tu ne peux PAS prescrire ou recommander des médicaments
- Tu ne peux PAS remplacer l'avis d'un professionnel de santé
- En cas de doute, tu renvoies toujours vers le médecin

Ton style de communication:
- Chaleureux et rassurant mais professionnel
- Utilise des métaphores simples quand approprié
- Évite le jargon médical complexe
- Structure tes réponses clairement
- Inclus toujours un avertissement médical approprié"""

    DIAGNOSTIC_EXPLANATION_TEMPLATE = """Diagnostic du médecin: {diagnostic_text}

Contexte patient:
- Âge: {age_group}
- Niveau d'éducation: {education_level}
- Langue: {language}

Questions spécifiques du patient: {patient_questions}

Explique ce diagnostic de manière simple et rassurante. Structure ta réponse ainsi:
1. Ce que signifie ce diagnostic en mots simples
2. Pourquoi cela arrive (causes possibles)
3. Ce à quoi s'attendre (évolution typique)
4. Prochaines étapes recommandées
5. Questions suggérées à poser au médecin

N'oublie pas d'inclure un avertissement médical approprié et d'encourager le suivi médical."""

    SIMPLE_DIAGNOSTIC_TEMPLATE = """Le médecin a diagnostiqué: {diagnostic_text}

Explique en {language} ce que cela signifie pour le patient de manière très simple et rassurante.
Niveau d'explication: {explanation_level}

Commence par "D'après ce que votre médecin a trouvé..." et garde un ton chaleureux."""

    EMERGENCY_DIAGNOSTIC_TEMPLATE = """ATTENTION - Diagnostic nécessitant une attention particulière: {diagnostic_text}

Explique avec précaution et empathie, en soulignant l'importance du suivi médical immédiat.
Reste rassurant tout en étant clair sur l'urgence."""

    def get_diagnostic_prompt(self, request_data: Dict) -> str:
        """Sélectionne le prompt approprié selon le contexte"""
        diagnostic_text = request_data.get('diagnostic_text', '')
        
        # Détection de mots-clés d'urgence
        emergency_keywords = ['urgent', 'grave', 'sévère', 'critique', 'immédiat', 'hospitalisation']
        is_emergency = any(keyword in diagnostic_text.lower() for keyword in emergency_keywords)
        
        if is_emergency:
            return self.EMERGENCY_DIAGNOSTIC_TEMPLATE
        elif request_data.get('explanation_level') == 'simple':
            return self.SIMPLE_DIAGNOSTIC_TEMPLATE
        else:
            return self.DIAGNOSTIC_EXPLANATION_TEMPLATE