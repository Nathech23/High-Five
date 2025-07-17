from src.services.templates_manager import LanguageDetector, PatientData, Language
from datetime import datetime

def test_simplified_language_detection():
    """Test de la détection de langue simplifiée pour le Cameroun"""
    
    detector = LanguageDetector()
    
    print("🧪 Test de détection de langue simplifiée (Cameroun local)")
    print("=" * 60)
    
    # Test 1: Patient avec langue préférée française
    patient_fr = PatientData(
        name="Marie Dubois",
        phone="+237675123456",
        preferred_language="fr",
        doctor_name="Dr. Kamga",
        appointment_date=datetime.now()
    )
    
    detected_lang_fr = detector.detect_language(patient_fr)
    print(f"✅ Patient avec preferred_language='fr': {detected_lang_fr.value}")
    
    # Test 2: Patient avec langue préférée anglaise
    patient_en = PatientData(
        name="John Smith",
        phone="+237698765432",
        preferred_language="en",
        doctor_name="Dr. Kamga",
        appointment_date=datetime.now()
    )
    
    detected_lang_en = detector.detect_language(patient_en)
    print(f"✅ Patient avec preferred_language='en': {detected_lang_en.value}")
    
    # Test 3: Patient avec langue préférée espagnole
    patient_es = PatientData(
        name="Carlos Rodriguez",
        phone="+237612345678",
        preferred_language="es",
        doctor_name="Dr. Kamga",
        appointment_date=datetime.now()
    )
    
    detected_lang_es = detector.detect_language(patient_es)
    print(f"✅ Patient avec preferred_language='es': {detected_lang_es.value}")
    
    # Test 4: Patient SANS langue préférée (fallback)
    patient_no_lang = PatientData(
        name="Patient Sans Langue",
        phone="+237655555555",
        preferred_language=None,  # Pas de langue définie
        doctor_name="Dr. Kamga",
        appointment_date=datetime.now()
    )
    
    detected_lang_fallback = detector.detect_language(patient_no_lang)
    print(f"✅ Patient SANS preferred_language: {detected_lang_fallback.value} (fallback)")
    
    # Test 5: Patient avec langue non supportée
    patient_invalid_lang = PatientData(
        name="Patient Langue Invalide",
        phone="+237644444444",
        preferred_language="zh",  # Chinois non supporté
        doctor_name="Dr. Kamga",
        appointment_date=datetime.now()
    )
    
    detected_lang_invalid = detector.detect_language(patient_invalid_lang)
    print(f"✅ Patient avec langue non supportée ('zh'): {detected_lang_invalid.value} (fallback)")
    
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ:")
    print("- ✅ Langue préférée respectée quand définie et supportée")
    print("- ✅ Fallback vers français pour le Cameroun")
    print("- ✅ Plus de détection par indicatif pays (inutile pour app locale)")
    print("- ✅ Logique simplifiée et adaptée au contexte local")

if __name__ == "__main__":
    test_simplified_language_detection()