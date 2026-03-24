"""API v1 main router"""
from fastapi import APIRouter
from app.api.v1.endpoints import projects, scans, results, reports, tools as tool_endpoints

api_router = APIRouter()

api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(scans.router, prefix="/scans", tags=["Scans"])
api_router.include_router(results.router, prefix="/results", tags=["Results"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(tool_endpoints.router, prefix="/tools", tags=["Tool Configs"])
