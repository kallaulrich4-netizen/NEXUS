"""
Fonctions IA du module Agriculture V2 : recommandations de culture et
diagnostic de maladies.

Comme partout ailleurs dans Nexus, ce fichier ne parle JAMAIS directement
à un fournisseur d'IA externe : il passe uniquement par l'abstraction
`AIProvider` déjà utilisée par Nexus AI (voir app/modules/ai_assistant/provider.py).
Changer de moteur d'IA en production ne demande donc aucune modification
ici, uniquement dans `get_ai_provider()`.
"""
from app.modules.ai_assistant.provider import AIProvider

# Référentiel de départ, volontairement simple et extensible sans changer
# le schéma de données : associe une culture à des besoins indicatifs.
# À enrichir progressivement (base agronomique régionale, etc.).
CROP_PROFILES = {
    "maïs": {"soils": {"argilo-sableux", "limoneux", "argileux"}, "seasons": {"pluies", "saison des pluies"}},
    "manioc": {"soils": {"sableux", "argilo-sableux", "latéritique"}, "seasons": {"toute saison"}},
    "riz": {"soils": {"argileux", "hydromorphe"}, "seasons": {"pluies", "saison des pluies"}},
    "tomate": {"soils": {"limoneux", "argilo-sableux"}, "seasons": {"saison sèche", "contre-saison"}},
    "haricot": {"soils": {"limoneux", "argilo-sableux"}, "seasons": {"pluies"}},
    "arachide": {"soils": {"sableux", "argilo-sableux"}, "seasons": {"pluies"}},
    "oignon": {"soils": {"limoneux", "sableux"}, "seasons": {"saison sèche"}},
}


def generate_crop_recommendations(
    provider: AIProvider,
    *,
    soil_type: str | None,
    country: str,
    region: str | None,
    season: str | None,
    budget_amount: float | None,
    user_language: str = "fr",
) -> list[dict]:
    """
    Retourne une liste de recommandations {crop_name, score, rationale}.

    Le score est calculé par un premier filtre déterministe sur le
    référentiel CROP_PROFILES (correspondance sol/saison), puis la
    justification textuelle est reformulée par Nexus AI pour rester
    naturelle et contextualisée (parcelle, pays, région, budget).
    """
    candidates = []
    for crop_name, profile in CROP_PROFILES.items():
        score = 40.0  # score de base : toute culture reste théoriquement possible
        if soil_type and soil_type.lower() in {s.lower() for s in profile["soils"]}:
            score += 35
        if season and any(season.lower() in s.lower() or s.lower() in season.lower() for s in profile["seasons"]):
            score += 25
        candidates.append((crop_name, min(score, 100.0)))

    candidates.sort(key=lambda item: item[1], reverse=True)
    top_candidates = candidates[:3]

    recommendations = []
    for crop_name, score in top_candidates:
        prompt = (
            f"Explique en 2 phrases pourquoi la culture '{crop_name}' est pertinente pour une "
            f"parcelle de type de sol '{soil_type or 'non précisé'}' au {country}"
            f"{f' ({region})' if region else ''}, pour la saison '{season or 'non précisée'}'"
            f"{f' avec un budget de {budget_amount}' if budget_amount else ''}."
        )
        rationale = provider.generate_reply(
            [{"role": "user", "content": prompt}], user_language=user_language
        )
        recommendations.append({"crop_name": crop_name, "score": score, "rationale": rationale})

    return recommendations


def diagnose_disease(
    provider: AIProvider,
    *,
    crop_name: str,
    symptoms_description: str,
    photo_reference: str | None,
    user_language: str = "fr",
) -> dict:
    """
    Retourne {diagnosis_text, recommended_actions, confidence}.

    Tant qu'aucun fournisseur d'IA à vision réelle n'est branché
    (`get_ai_provider()` retourne un fournisseur texte de test dans cet
    environnement), l'analyse de la photo elle-même reste indicative :
    seule la description des symptômes est réellement exploitée. En
    production, branchez ici un fournisseur multimodal pour que la photo
    soit analysée pixel par pixel.
    """
    prompt = (
        f"Un agriculteur cultivant '{crop_name}' décrit les symptômes suivants sur ses plants : "
        f"« {symptoms_description} »"
        f"{' Une photo a également été fournie.' if photo_reference else ''} "
        "Propose un diagnostic probable en une phrase, puis des actions recommandées en une phrase."
    )
    diagnosis_text = provider.generate_reply(
        [{"role": "user", "content": prompt}], user_language=user_language
    )

    return {
        "diagnosis_text": diagnosis_text,
        "recommended_actions": (
            "Isoler les plants atteints, éviter l'excès d'irrigation, et consulter un technicien "
            "agricole local si les symptômes persistent au-delà de quelques jours."
        ),
        # Confiance volontairement modeste tant qu'aucune analyse d'image réelle n'est branchée.
        "confidence": 55.0 if photo_reference else 40.0,
    }
