"""
Aide à la pagination, partagée par tous les modules.

Plutôt que chaque module réimplémente son propre `skip`/`limit`, les
endpoints de listage peuvent utiliser `paginate(query, page, page_size)`
pour obtenir une page de résultats et le total, de façon cohérente sur
toute la plateforme.

Note d'optimisation : sur les tables volumineuses (ex: `notifications`,
`audit_log`, `livestock_weight_records`), pensez à toujours trier sur une
colonne indexée (voir les `Index(...)` déjà déclarés dans les modèles
correspondants) avant de paginer, pour éviter un tri complet en mémoire.
"""
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.orm import Query

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass
class Page:
    items: list
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)


def paginate(query: Query, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> Page:
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)

    total = query.order_by(None).count()  # order_by(None) : le tri ne sert pas au COUNT, on l'évite pour la perf
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return Page(items=items, total=total, page=page, page_size=page_size)
