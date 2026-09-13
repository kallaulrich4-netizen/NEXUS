"""
Calcul du plan alimentaire recommandé pour un troupeau.

Référentiel de départ, simple et extensible : besoin journalier moyen en
kilogrammes par tête et par espèce, avec un coût indicatif au kilogramme.
À enrichir progressivement (rations précises par âge/poids/production)
sans changer le schéma de la table FeedPlan.
"""

# {espèce: (aliment par défaut, kg/tête/jour, coût indicatif/kg en XOF)}
SPECIES_FEED_PROFILES = {
    "bovins": ("fourrage + complément", 12.0, 150.0),
    "ovins": ("fourrage", 2.5, 120.0),
    "caprins": ("fourrage", 2.0, 120.0),
    "porcins": ("aliment concentré", 2.8, 250.0),
    "volailles": ("aliment complet volaille", 0.12, 350.0),
    "lapins": ("granulés + fourrage", 0.15, 300.0),
    "poissons": ("aliment aquacole", 0.03, 500.0),
    "abeilles": ("sirop de nourrissement (hors saison)", 0.05, 400.0),
}

DEFAULT_PROFILE = ("aliment standard", 1.5, 200.0)


def compute_feed_plan(species: str, current_count: int, feed_type_override: str | None = None) -> dict:
    """Retourne {feed_type, daily_quantity_kg, estimated_daily_cost, currency}."""
    default_feed_type, per_head_kg, cost_per_kg = SPECIES_FEED_PROFILES.get(species.lower(), DEFAULT_PROFILE)

    daily_quantity_kg = per_head_kg * max(current_count, 0)
    estimated_daily_cost = daily_quantity_kg * cost_per_kg

    return {
        "feed_type": feed_type_override or default_feed_type,
        "daily_quantity_kg": daily_quantity_kg,
        "estimated_daily_cost": estimated_daily_cost,
        "currency": "XOF",
    }
