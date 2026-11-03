from typing import Annotated

from fastapi import APIRouter, Query

from app.db.session import SessionDep
from app.schemas import ErrorRead, Id, Page, PageParams, ProductRead, ProductWrite, SearchParams
from app.services import products as product_service
from app.services import search as search_service

router = APIRouter(prefix="/products", tags=["products"])

NOT_FOUND = {404: {"model": ErrorRead}}
DUPLICATE_SKU = {409: {"model": ErrorRead}}


@router.get("", response_model=Page[ProductRead])
def list_products(session: SessionDep, params: Annotated[PageParams, Query()]):
    return product_service.list_products(session, params)


# Must be defined before "/{product_id}", or FastAPI would read "search" as a product id.
@router.get("/search", response_model=Page[ProductRead])
def search_products(session: SessionDep, params: Annotated[SearchParams, Query()]):
    return search_service.search_products(session, params)


@router.get("/{product_id}", response_model=ProductRead, responses=NOT_FOUND)
def get_product(product_id: Id, session: SessionDep):
    return product_service.get_product(session, product_id)


@router.post("", response_model=ProductRead, status_code=201, responses=DUPLICATE_SKU)
def create_product(body: ProductWrite, session: SessionDep):
    return product_service.create_product(session, body)


@router.put("/{product_id}", response_model=ProductRead, responses=NOT_FOUND | DUPLICATE_SKU)
def update_product(product_id: Id, body: ProductWrite, session: SessionDep):
    return product_service.update_product(session, product_id, body)


@router.delete("/{product_id}", status_code=204, responses=NOT_FOUND)
def delete_product(product_id: Id, session: SessionDep):
    product_service.delete_product(session, product_id)
