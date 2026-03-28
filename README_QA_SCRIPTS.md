# QA AUTOMATION SCRIPTS - Red Team SaaS Professional

Scripts modulares y automatizados para validación completa del entorno.

## 📁 ARCHIVOS

```
run_all_tests.sh          ← Script orquestador (ejecuta TODO)
test_health_check.sh      ← Health check rápido (30 segundos)
test_api.sh               ← Validación API Backend (2 min)
test_swagger.sh           ← Validación Swagger UI (1 min)
test_prometheus.sh        ← Validación Prometheus (1 min)
test_flower.sh            ← Validación Flower/Celery (1 min)
```

---

## 🚀 CÓMO USAR

### Opción 1: EJECUTAR TODO (Recomendado)

```bash
# Hacer ejecutable y ejecutar
chmod +x run_all_tests.sh
./run_all_tests.sh

# Tiempo estimado: 8-10 minutos
# Genera reporte consolidado en qa_results_TIMESTAMP/
```

### Opción 2: TESTS INDIVIDUALES

```bash
# Health check rápido (30 segundos)
chmod +x test_health_check.sh
./test_health_check.sh

# API Backend (2 minutos)
chmod +x test_api.sh
./test_api.sh

# Swagger UI (1 minuto)
chmod +x test_swagger.sh
./test_swagger.sh

# Prometheus (1 minuto)
chmod +x test_prometheus.sh
./test_prometheus.sh

# Flower (1 minuto)
chmod +x test_flower.sh
./test_flower.sh
```

### Opción 3: BATCH CON SCRIPT

```bash
# Crear script que ejecute todos
cat > quick_test.sh << 'EOF'
#!/bin/bash
./test_health_check.sh && \
./test_api.sh && \
./test_swagger.sh && \
./test_prometheus.sh && \
./test_flower.sh
echo "✓ All tests completed"
EOF

chmod +x quick_test.sh
./quick_test.sh
```

---

## 📊 CADA SCRIPT VALIDA

### test_health_check.sh
- ✓ API disponible
- ✓ Swagger UI disponible
- ✓ Prometheus disponible
- ✓ Grafana disponible
- ✓ Flower disponible
- ⏱ Tiempo: ~30 segundos

### test_api.sh
- ✓ Health endpoint
- ✓ Root endpoint
- ✓ POST /auth/register
- ✓ POST /auth/login
- ✓ GET /auth/me (protegido)
- ✓ GET /auth/me sin token (401)
- ✓ POST /auth/refresh
- ✓ Error handling
- ✓ Content-Type headers
- ✓ Performance/latencia
- ⏱ Tiempo: ~2 minutos

### test_swagger.sh
- ✓ Swagger UI accesible
- ✓ HTML válido
- ✓ OpenAPI JSON schema
- ✓ Endpoints documentados
- ✓ Schemas/modelos documentados
- ✓ ReDoc accesible
- ✓ Response headers
- ✓ Performance
- ⏱ Tiempo: ~1 minuto

### test_prometheus.sh
- ✓ Prometheus accesible
- ✓ API funciona
- ✓ Métricas disponibles
- ✓ Targets status
- ✓ HTTP requests metric
- ✓ Performance
- ⏱ Tiempo: ~1 minuto

### test_flower.sh
- ✓ Flower accesible
- ✓ API funciona
- ✓ Workers conectados
- ✓ Tasks API
- ✓ Estadísticas
- ✓ Performance
- ⏱ Tiempo: ~1 minuto

---

## 📝 REPORTES

Cada script genera:

1. **test_*_report.txt** - Reporte del test individual
2. **CONSOLIDATED_QA_REPORT.txt** - Reporte consolidado (solo run_all_tests.sh)
3. **QA_REPORT.html** - Reporte HTML visual (solo run_all_tests.sh)

### Ubicación

```
qa_results_TIMESTAMP/
├── test_api_report.txt
├── test_swagger_report.txt
├── test_prometheus_report.txt
├── test_flower_report.txt
├── CONSOLIDATED_QA_REPORT.txt
└── QA_REPORT.html
```

---

## ✅ EXPECTED OUTPUT

Si todos los tests pasan:

```
✓ API Backend - PASSED
✓ Swagger UI - PASSED
✓ Prometheus - PASSED
✓ Flower - PASSED

═══════════════════════════════════════════════════════════════
STATUS: ✓ ALL TESTS PASSED
READY FOR NEXT PHASE: YES
═══════════════════════════════════════════════════════════════
```

---

## ❌ TROUBLESHOOTING

### Error: "API no está disponible"
```bash
# Verificar que docker-compose está corriendo
docker-compose ps

# Si no está:
docker-compose up -d

# Esperar ~20 segundos y volver a ejecutar
```

### Error: "curl: command not found"
```bash
# Instalar curl
# Ubuntu/Debian:
sudo apt-get install curl

# macOS:
brew install curl

# Windows (PowerShell):
choco install curl
```

### Error: "Permission denied"
```bash
# Hacer scripts ejecutables
chmod +x test_*.sh run_all_tests.sh
```

### Tests lentos
- Aumentar timeout en scripts
- Verificar que Docker tiene suficientes recursos
- Verificar conexión de red

---

## 🎯 RECOMENDACIONES

1. **Primero**: Ejecutar `test_health_check.sh` para verificación rápida
2. **Luego**: Ejecutar `test_api.sh` para validar core functionality
3. **Finalmente**: Ejecutar `run_all_tests.sh` para suite completa

---

## 📋 INTEGRACIÓN CI/CD

Para integrar en pipeline:

```yaml
# GitHub Actions example
- name: Run QA Tests
  run: |
    chmod +x run_all_tests.sh
    ./run_all_tests.sh
    
- name: Upload Reports
  uses: actions/upload-artifact@v2
  with:
    name: qa-reports
    path: qa_results_*
```

---

## 🔧 PERSONALIZACIÓN

Para cambiar URLs (si no están en localhost):

```bash
# Editar variables en cada script
SWAGGER_URL="http://tu-servidor:8000/api/docs"
PROMETHEUS_URL="http://tu-servidor:9090"
# etc...
```

---

## 📊 EJEMPLO DE REPORTE

```
╔════════════════════════════════════════════════════════════╗
║         QA VALIDATION CONSOLIDATED REPORT                 ║
║         Red Team SaaS Professional                         ║
╚════════════════════════════════════════════════════════════╝

SUMMARY:
────────────────────────────────────────────────────────────
Total Test Suites:    6
Passed Suites:        6
Failed Suites:        0
Overall Success Rate: 100%

STATUS: ✓ ALL TESTS PASSED
READY FOR NEXT PHASE: YES
════════════════════════════════════════════════════════════
```

---

## 🚀 PRÓXIMOS PASOS

1. Descargar scripts
2. Hacer ejecutables: `chmod +x *.sh`
3. Ejecutar: `./run_all_tests.sh`
4. Revisar reportes en `qa_results_*/`
5. Si todo pasa: ¡Listo para siguiente fase!

---

## 📞 SOPORTE

Si un test falla:
1. Leer el error en el output
2. Revisar el reporte: `test_*_report.txt`
3. Verificar servicio correspondiente está corriendo
4. Ejecutar solo ese test para más detalles

---

**Creado para Red Team SaaS Professional - QA Automation**
