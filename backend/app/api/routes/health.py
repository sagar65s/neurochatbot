from fastapi import APIRouter

router = APIRouter()

@router.get("/api/health")
@router.head("/api/health")
async def health_check():
    return {"status": "healthy"}