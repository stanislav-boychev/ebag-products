import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.session import SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ops"])


@router.get("/health", responses={503: {"description": "The database can't be reached"}})
def health(session: SessionDep) -> JSONResponse:
    """The service is up and can reach the database. A 503 tells a load balancer to stop sending traffic here."""
    try:
        session.execute(text("SELECT 1"))
    except OperationalError:
        logger.exception("Health check can't reach the database")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})
