from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def home() -> dict[str, str]:
    return {"status": "ok"}
