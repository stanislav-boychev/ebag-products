import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Category, Product
from app.db.session import constraint_name
from app.exceptions import Conflict, InvalidInput, NotFound
from app.schemas import PageParams, ProductWrite
from app.services.pagination import paginate

logger = logging.getLogger(__name__)


def list_products(session: Session, params: PageParams) -> dict:
    return paginate(session, select(Product).where(Product.deleted_at.is_(None)).order_by(Product.id), params)


def get_product(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise NotFound("Product not found")
    return product


def create_product(session: Session, data: ProductWrite) -> Product:
    check_category_exists(session, data.category_id)
    product = Product(**data.model_dump(mode="json"))
    session.add(product)
    commit(session)
    session.refresh(product)  # load timestamps set by Postgres
    logger.info("Created product %s (%s)", product.id, product.sku)
    return product


def update_product(session: Session, product_id: int, data: ProductWrite) -> Product:
    product = get_product(session, product_id)
    check_category_exists(session, data.category_id)
    for field, value in data.model_dump(mode="json").items():
        setattr(product, field, value)
    commit(session)
    session.refresh(product)
    logger.info("Updated product %s", product.id)
    return product


def delete_product(session: Session, product_id: int) -> None:
    product = get_product(session, product_id)
    product.deleted_at = func.now()
    session.commit()
    logger.info("Deleted product %s", product_id)


def check_category_exists(session: Session, category_id: int) -> None:
    category = session.get(Category, category_id)
    if category is None or category.deleted_at is not None:
        raise InvalidInput("category_id", "Category does not exist")


def commit(session: Session) -> None:
    """Commit, turning a rejected SKU or category into the matching error."""
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        name = constraint_name(error)
        if name == "uq_products_sku":
            raise Conflict("A product with this SKU already exists") from error
        if name == "fk_products_category_id_categories":
            raise InvalidInput("category_id", "Category does not exist") from error
        raise
