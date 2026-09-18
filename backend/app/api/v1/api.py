from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    authorities,
    departments,
    health,
    rbac,
    users,
)


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(rbac.router)
api_router.include_router(users.router)
api_router.include_router(departments.router)
api_router.include_router(authorities.router)
