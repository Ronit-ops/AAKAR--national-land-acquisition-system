from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, rbac, users


api_router = APIRouter()

api_router.include_router(
    health.router,
)

api_router.include_router(
    auth.router,
)

api_router.include_router(
    rbac.router,
)

api_router.include_router(
    users.router,
)