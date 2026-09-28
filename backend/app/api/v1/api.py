from fastapi import APIRouter

from app.api.v1.endpoints import (
    acquisition_cases,
    audit,
    auth,
    authorities,
    departments,
    health,
    land_requirements,
    parcels,
    permissions,
    projects,
    rbac,
    surveys,
    users,
)


api_router = APIRouter()


api_router.include_router(health.router)

api_router.include_router(auth.router)

api_router.include_router(rbac.router)

api_router.include_router(users.router)

api_router.include_router(departments.router)

api_router.include_router(authorities.router)

api_router.include_router(permissions.router)

api_router.include_router(audit.router)

api_router.include_router(projects.router)

api_router.include_router(land_requirements.router)

api_router.include_router(acquisition_cases.router)

api_router.include_router(parcels.router)

api_router.include_router(surveys.router)