import logging

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Category, Product
from app.db.session import constraint_name
from app.exceptions import Conflict, InvalidInput, NotFound
from app.schemas import CategoryWrite, PageParams
from app.services.pagination import paginate

logger = logging.getLogger(__name__)


def list_categories(session: Session, params: PageParams) -> dict:
    return paginate(session, select(Category).where(Category.deleted_at.is_(None)).order_by(Category.id), params)


def get_category(session: Session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None or category.deleted_at is not None:
        raise NotFound("Category not found")
    return category


def create_category(session: Session, data: CategoryWrite) -> Category:
    check_parent_exists(session, data.parent_id)
    category = Category(**data.model_dump())
    session.add(category)
    commit(session)
    session.refresh(category)  # load timestamps set by Postgres
    logger.info("Created category %s", category.id)
    return category


def update_category(session: Session, category_id: int, data: CategoryWrite) -> Category:
    category = get_category(session, category_id)
    check_parent_exists(session, data.parent_id)
    check_not_moved_under_itself(session, category_id, data.parent_id)
    for field, value in data.model_dump().items():
        setattr(category, field, value)
    commit(session)
    session.refresh(category)
    logger.info("Updated category %s", category.id)
    return category


def delete_category(session: Session, category_id: int) -> None:
    category = get_category(session, category_id)
    has_subcategories = exists().where(Category.parent_id == category_id, Category.deleted_at.is_(None))
    has_products = exists().where(Product.category_id == category_id, Product.deleted_at.is_(None))
    if session.scalar(select(has_subcategories)) or session.scalar(select(has_products)):
        raise Conflict("Category still has subcategories or products")
    category.deleted_at = func.now()
    session.commit()
    logger.info("Deleted category %s", category_id)


def commit(session: Session) -> None:
    """Commit, turning a rejected name or parent into the matching error."""
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        name = constraint_name(error)
        if name == "uq_categories_name":
            raise Conflict("A category with this name already exists") from error
        if name == "fk_categories_parent_id_categories":
            raise InvalidInput("parent_id", "Parent category does not exist") from error
        raise


def check_parent_exists(session: Session, parent_id: int | None) -> None:
    if parent_id is None:
        return
    parent = session.get(Category, parent_id)
    if parent is None or parent.deleted_at is not None:
        raise InvalidInput("parent_id", "Parent category does not exist")


def check_not_moved_under_itself(session: Session, category_id: int, parent_id: int | None) -> None:
    current = parent_id
    while current is not None:
        if current == category_id:
            raise InvalidInput("parent_id", "A category can't be moved under itself or its subcategory")
        current = session.scalar(select(Category.parent_id).where(Category.id == current))
