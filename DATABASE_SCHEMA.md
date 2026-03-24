# Database Schema - Red Team SaaS

10 Modelos SQLAlchemy:
1. User - Autenticacion
2. Workspace - Aislamiento proyectos
3. Task - Ejecucion herramientas
4. Result - Salida (AES-256)
5. AuditLog - Pista inmutable
6. Template - Configuraciones
7. ThreatIntel - CVE database
8. RiskScore - Puntuacion riesgo
9. ComplianceMapping - Controles
10. Report - Reportes pentesting

Caracteristicas:
- Encriptacion AES-256
- 20+ indices
- Cascade delete
- Audit trail
- Connection pooling
