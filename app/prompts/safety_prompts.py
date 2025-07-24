class SafetyPrompts:
    
    MEDICAL_DISCLAIMERS = {
        Language.FRENCH: {
            "general": " Important: Cette explication est fournie à titre informatif uniquement et ne remplace pas l'avis de votre médecin. Suivez toujours les instructions de votre professionnel de santé.",
            "medication": " Médicament: Ne modifiez jamais votre traitement sans consulter votre médecin ou pharmacien. En cas d'effets indésirables, contactez immédiatement votre professionnel de santé.",
            "urgent": " Urgent: Si vous ressentez des symptômes inquiétants ou une urgence médicale, contactez immédiatement votre médecin ou les services d'urgence (15)."
        },
        Language.ENGLISH: {
            "general": " Important: This explanation is for informational purposes only and does not replace your doctor's advice. Always follow your healthcare professional's instructions.",
            "medication": " Medication: Never modify your treatment without consulting your doctor or pharmacist. In case of adverse effects, contact your healthcare professional immediately.",
            "urgent": " Urgent: If you experience concerning symptoms or a medical emergency, contact your doctor or emergency services immediately."
        }
    }
    
    SAFETY_FILTERS = [
        "Ne jamais conseiller d'arrêter un traitement",
        "Ne jamais modifier une prescription",
        "Ne jamais diagnostiquer",
        "Toujours renvoyer vers le médecin en cas de doute",
        "Inclure les avertissements appropriés",
        "Être vigilant aux interactions médicamenteuses"
    ]
    
    RED_FLAG_KEYWORDS = [
        "arrêter le traitement", "stop medication", 
        "ne prenez pas", "don't take",
        "remplacer par", "replace with",
        "diagnostic", "vous avez", "you have",
        "prescrire", "prescribe"
    ]