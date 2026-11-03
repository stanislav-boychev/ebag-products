from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import Category, Product
from app.schemas import SearchParams
from app.services.pagination import paginate


def search_products(session: Session, params: SearchParams) -> dict:
    """Find live products that match every filter given."""
    query = select(Product).where(Product.deleted_at.is_(None))
    if params.q is not None:
        query = query.where(Product.title.icontains(params.q, autoescape=True))
    if params.sku is not None:
        query = query.where(Product.sku == params.sku)
    if params.category_id is not None:
        query = query.where(Product.category_id.in_(category_and_subcategories(params.category_id)))
    if params.currency is not None:
        query = query.where(Product.currency == params.currency)
    if params.min_price is not None:
        query = query.where(Product.price >= params.min_price)
    if params.max_price is not None:
        query = query.where(Product.price <= params.max_price)

    return paginate(session, query.order_by(Product.id), params)


def category_and_subcategories(category_id: int) -> Select:
    category_ids = select(Category.id).where(Category.id == category_id).cte(recursive=True)
    category_ids = category_ids.union(select(Category.id).join(category_ids, Category.parent_id == category_ids.c.id))
    return select(category_ids.c.id)
