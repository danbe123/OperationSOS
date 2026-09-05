# api/sos/ai_terms.py
"""UK medical keyword list shared by the AI health router, the medical disclaimer and the search intent boost.

Terms are stored in *tokenised* form: lowercase, alphanumerics only, phrases joined by single spaces
(so "co-codamol" is "co codamol"), matching what sos.query.tokenize produces.
"""
from __future__ import annotations

from typing import Iterable

MEDICAL_TERMS: frozenset[str] = frozenset({
    # symptoms
    "pain", "fever", "temperature", "cough", "rash", "vomiting", "vomit", "diarrhoea", "nausea", "dizzy", "dizziness",
    "faint", "fainting", "headache", "migraine", "swelling", "swollen", "bleeding", "bleed", "bruise", "bruising", "itch",
    "itching", "wheeze", "wheezing", "breathless", "breathing", "unconscious", "confusion", "confused", "seizure",
    "convulsion", "numb", "numbness", "tingling", "chest", "chest pain", "shortness of breath", "sore throat", "stiff neck",
    "stomach ache", "tummy ache", "cramp", "cramps", "dehydrated", "dehydration", "sweating", "shivering", "chills",
    "jaundice", "constipation", "constipated", "blister", "blisters", "pus", "infected", "infection", "sepsis",
    "allergic", "allergy", "hives", "anaphylaxis", "asthma", "stroke", "heart attack", "cardiac arrest", "angina",
    "palpitations", "choking", "choke", "drowning", "hypothermia", "frostbite", "heatstroke", "heat stroke",
    "heat exhaustion", "sunburn", "sunstroke", "unresponsive", "not breathing", "collapsed",
    # injuries
    "burn", "burns", "scald", "scalds", "wound", "wounds", "laceration", "fracture", "fractures", "broken bone",
    "broken arm", "broken leg", "sprain", "sprained", "dislocated", "dislocation", "concussion", "head injury",
    "spinal injury", "neck injury", "bite", "bites", "sting", "stings", "snake bite", "adder", "tick", "ticks",
    "splinter", "shock", "amputation", "crush injury", "crushed", "electric shock", "electrocution", "poisoning",
    "poisoned", "overdose", "carbon monoxide", "radiation sickness", "chemical burn", "eye injury", "nosebleed",
    "toothache", "abscess", "frostnip", "trench foot",
    # first aid
    "first aid", "cpr", "resuscitation", "recovery position", "tourniquet", "bandage", "dressing", "plaster", "splint",
    "sling", "defibrillator", "aed", "pulse", "airway", "chest compressions", "rescue breaths", "epipen", "adrenaline",
    "auto injector", "inhaler", "insulin", "glucose", "hypo", "hypoglycaemia", "hyperglycaemia", "diabetes", "diabetic",
    "antiseptic", "sterilise", "stitches", "suture", "steri strips", "burn gel", "cling film", "rehydration",
    "oral rehydration", "rehydration salts", "dioralyte",
    # conditions
    "pregnant", "pregnancy", "labour", "childbirth", "miscarriage", "contraception", "menstrual", "uti", "cystitis",
    "thrush", "chickenpox", "measles", "flu", "influenza", "covid", "pneumonia", "bronchitis", "tuberculosis", "cholera",
    "typhoid", "dysentery", "norovirus", "gastroenteritis", "food poisoning", "tetanus", "rabies", "lyme disease",
    "meningitis", "malaria", "scabies", "lice", "worms", "ringworm", "impetigo", "cellulitis", "eczema", "psoriasis",
    "hay fever", "hayfever", "arthritis", "gout", "kidney infection", "appendicitis", "hernia", "ulcer", "epilepsy",
    "epileptic", "depression", "anxiety", "panic attack", "psychosis", "suicidal", "self harm", "withdrawal",
    "alcohol withdrawal", "hypertension", "blood pressure", "cholesterol", "anaemia", "dementia", "asthmatic",
    # medicines (UK names)
    "paracetamol", "ibuprofen", "aspirin", "codeine", "co codamol", "naproxen", "morphine", "tramadol", "dihydrocodeine",
    "antibiotic", "antibiotics", "amoxicillin", "flucloxacillin", "doxycycline", "penicillin", "phenoxymethylpenicillin",
    "clarithromycin", "metronidazole", "trimethoprim", "nitrofurantoin", "ciprofloxacin", "antihistamine", "cetirizine",
    "loratadine", "chlorphenamine", "piriton", "loperamide", "imodium", "salbutamol", "ventolin", "prednisolone",
    "hydrocortisone", "omeprazole", "lansoprazole", "gaviscon", "antacid", "metformin", "levothyroxine", "warfarin",
    "clopidogrel", "statin", "atorvastatin", "ramipril", "amlodipine", "bisoprolol", "diazepam", "sertraline",
    "citalopram", "fluoxetine", "amitriptyline", "gabapentin", "potassium iodide", "iodine tablets", "iodide",
    "chlorhexidine", "clotrimazole", "aciclovir", "fluconazole", "mebendazole", "permethrin", "lidocaine",
    "glyceryl trinitrate", "gtn", "naloxone", "glucagon", "vaccine", "vaccination", "dose", "dosage", "medicine",
    "medicines", "medication", "prescription", "pharmacy", "pharmacist", "gp", "nhs", "ambulance", "hospital",
    "doctor", "nurse", "paramedic", "midwife", "dentist",
    # body words that appear in symptom questions
    "heart", "lungs", "lung", "stomach", "bowel", "bladder", "spine", "skull", "ribs", "ankle", "wrist", "knee", "hip",
    "shoulder", "elbow", "finger", "toe", "eye", "eyes", "ear", "ears", "throat", "skin", "bone", "bones", "muscle",
    "tendon", "artery", "vein", "nerve",
})


def is_medical(tokens: Iterable[str]) -> bool:
    """True when any token, its singular form, or an adjacent bigram/trigram is a medical term."""
    toks = [t.lower() for t in tokens]
    for i, tok in enumerate(toks):
        if tok in MEDICAL_TERMS:
            return True
        if len(tok) > 3 and tok.endswith("s") and tok[:-1] in MEDICAL_TERMS:
            return True
        if i + 1 < len(toks) and f"{tok} {toks[i + 1]}" in MEDICAL_TERMS:
            return True
        if i + 2 < len(toks) and f"{tok} {toks[i + 1]} {toks[i + 2]}" in MEDICAL_TERMS:
            return True
    return False
