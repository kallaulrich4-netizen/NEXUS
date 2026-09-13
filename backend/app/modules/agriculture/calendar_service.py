"""
Génération du calendrier agricole automatique.

Référentiel de départ, simple et extensible : pour chaque culture,
un ensemble de décalages en jours par rapport à la date de semis,
associés à un type de tâche. À enrichir progressivement (agronomie
régionale) sans jamais changer le schéma de la table CalendarTask.
"""
from datetime import date, timedelta

DEFAULT_SCHEDULE_OFFSETS = [
    (15, "fertilisation", "Première fertilisation"),
    (30, "traitement_phytosanitaire", "Traitement préventif"),
    (45, "desherbage", "Désherbage"),
    (60, "controle_sol", "Contrôle de l'état du sol"),
]

CROP_SCHEDULE_OVERRIDES = {
    "riz": [
        (10, "fertilisation", "Fertilisation de fond"),
        (25, "traitement_phytosanitaire", "Traitement anti-pyriculariose"),
        (50, "fertilisation", "Fertilisation d'entretien"),
    ],
    "tomate": [
        (7, "fertilisation", "Fertilisation starter"),
        (20, "traitement_phytosanitaire", "Traitement anti-mildiou"),
        (35, "traitement_phytosanitaire", "Traitement de rappel"),
    ],
}


def build_calendar_tasks(crop_name: str, planting_date: date, expected_harvest_date: date | None) -> list[dict]:
    """
    Retourne une liste de {task_type, title, due_date} à créer pour un
    cycle de culture qui démarre. La récolte prévue, si connue, est
    toujours ajoutée comme dernière tâche du calendrier.
    """
    schedule = CROP_SCHEDULE_OVERRIDES.get(crop_name.lower(), DEFAULT_SCHEDULE_OFFSETS)

    tasks = [
        {
            "task_type": task_type,
            "title": title,
            "due_date": planting_date + timedelta(days=offset_days),
        }
        for offset_days, task_type, title in schedule
    ]

    if expected_harvest_date:
        tasks.append({
            "task_type": "recolte",
            "title": "Récolte prévue",
            "due_date": expected_harvest_date,
        })

    return tasks
