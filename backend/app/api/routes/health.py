from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/health")
@app.head("/api/health")
async def health():
    return JSONResponse(
        content={"status": "healthy"},
        status_code=200
    )