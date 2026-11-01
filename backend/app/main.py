from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.adapters.orm import start_mappers
from app.api_errors import error_response
from app.routers.categories import router as categories_router
from app.routers.expenses import router as expenses_router
from app.routers.groups import router as groups_router
from app.routers.members import router as members_router

start_mappers()
app = FastAPI()
app.include_router(groups_router)
app.include_router(members_router)
app.include_router(categories_router)
app.include_router(expenses_router)


@app.exception_handler(RequestValidationError)
def request_validation_error(
    _request: Request, _error: RequestValidationError
) -> JSONResponse:
    return error_response(422, "INVALID_REQUEST", "Invalid request.")


@app.exception_handler(404)
def not_found(_request: Request, _error: HTTPException) -> JSONResponse:
    return error_response(404, "NOT_FOUND", "Resource not found.")


@app.exception_handler(405)
def method_not_allowed(_request: Request, e: HTTPException) -> JSONResponse:
    return error_response(
        405, "METHOD_NOT_ALLOWED", "Method not allowed.", headers=e.headers
    )


@app.exception_handler(Exception)
def internal_error(_request: Request, _error: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", "Internal server error.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
