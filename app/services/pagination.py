from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas import PageParams


def paginate(session: Session, query: Select, params: PageParams) -> dict:
    """Run a query for one page, plus a count of all its rows."""
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    offset = (params.page - 1) * params.page_size
    items = session.scalars(query.limit(params.page_size).offset(offset)).all()
    return {"items": items, "total": total, "page": params.page, "page_size": params.page_size}
