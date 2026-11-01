from fastapi import FastAPI

from app.routers.categories import router as categories_router
from app.routers.groups import router as groups_router
from app.routers.members import router as members_router

app = FastAPI()
app.include_router(groups_router)
app.include_router(members_router)
app.include_router(categories_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
