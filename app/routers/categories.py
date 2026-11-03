from typing import Annotated

from fastapi import APIRouter, Query

from app.db.session import SessionDep
from app.schemas import CategoryRead, CategoryWrite, ErrorRead, Id, Page, PageParams
from app.services import categories as category_service

router = APIRouter(prefix="/categories", tags=["categories"])

NOT_FOUND = {404: {"model": ErrorRead}}
CONFLICT = {409: {"model": ErrorRead}}


@router.get("", response_model=Page[CategoryRead])
def list_categories(session: SessionDep, params: Annotated[PageParams, Query()]):
    return category_service.list_categories(session, params)


@router.get("/{category_id}", response_model=CategoryRead, responses=NOT_FOUND)
def get_category(category_id: Id, session: SessionDep):
    return category_service.get_category(session, category_id)


@router.post("", response_model=CategoryRead, status_code=201, responses=CONFLICT)
def create_category(body: CategoryWrite, session: SessionDep):
    return category_service.create_category(session, body)


@router.put("/{category_id}", response_model=CategoryRead, responses=NOT_FOUND | CONFLICT)
def update_category(category_id: Id, body: CategoryWrite, session: SessionDep):
    return category_service.update_category(session, category_id, body)


@router.delete("/{category_id}", status_code=204, responses=NOT_FOUND | CONFLICT)
def delete_category(category_id: Id, session: SessionDep):
    category_service.delete_category(session, category_id)
