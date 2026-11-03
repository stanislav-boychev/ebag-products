import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import Conflict, InvalidInput, NotFound
from app.routers import categories, health, products

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Catalogue service")

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(health.router)


def plain_error(status_code: int):
    def handler(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    return handler


app.add_exception_handler(NotFound, plain_error(404))
app.add_exception_handler(Conflict, plain_error(409))


@app.exception_handler(InvalidInput)
def invalid_input(request: Request, error: InvalidInput) -> JSONResponse:
    """The same shape as FastAPI's own validation errors, so clients parse one format."""
    detail = [{"type": "invalid_input", "loc": ["body", error.field], "msg": str(error)}]
    return JSONResponse(status_code=422, content={"detail": detail})
