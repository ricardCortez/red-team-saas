"""API v1 main router"""
from fastapi import APIRouter
from app.api.v1.endpoints import projects, scans, results, reports, tools as tool_endpoints
from app.api.v1.endpoints import executions
from app.api.v1.endpoints import findings, exec_results
from app.api.v1.endpoints import dashboard
from app.api.v1.endpoints import alert_rules, notifications
from app.api.v1.endpoints import targets
from app.api.v1.endpoints import wordlists
from app.api.v1.endpoints import threat_intel
from app.api.v1.endpoints import compliance
from app.api.v1.endpoints import integrations
from app.api.v1.endpoints import security

api_router = APIRouter()

api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
# Phase 9: targets (routes already include /projects/{id}/targets prefix)
api_router.include_router(targets.router, prefix="", tags=["Targets"])
api_router.include_router(scans.router, prefix="/scans", tags=["Scans"])
api_router.include_router(results.router, prefix="/results", tags=["Results"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(tool_endpoints.router, prefix="/tools", tags=["Tool Configs"])
api_router.include_router(executions.router, prefix="/executions", tags=["Executions"])
# Phase 5
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(exec_results.router, prefix="/exec-results", tags=["Exec Results"])
# Phase 7
api_router.include_router(dashboard.router, prefix="", tags=["Dashboard"])
# Phase 8
api_router.include_router(alert_rules.router, prefix="", tags=["Alert Rules"])
api_router.include_router(notifications.router, prefix="", tags=["Notifications"])
# Phase 10
api_router.include_router(wordlists.router, prefix="", tags=["Wordlists"])
# Phase 12
api_router.include_router(threat_intel.router, prefix="", tags=["Threat Intel"])
# Phase 13
api_router.include_router(compliance.router, prefix="", tags=["Compliance"])
# Phase 16
api_router.include_router(integrations.router, prefix="", tags=["Integrations"])
# Phase 17
api_router.include_router(security.router, prefix="", tags=["Security"])
