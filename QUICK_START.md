# 🚀 QUICK START - QA AUTOMATION SCRIPTS

**Cancelaste el prompt largo. Ahora usaremos BASH SCRIPTS en lugar de prompts.**

---

## 📦 QUÉ RECIBISTE

6 scripts BASH modulares + 1 orquestador:

```
test_health_check.sh       ← Verificación rápida (30 segundos)
test_api.sh                ← Valida API (2 minutos)
test_swagger.sh            ← Valida Swagger UI (1 minuto)
test_prometheus.sh         ← Valida Prometheus (1 minuto)
test_flower.sh             ← Valida Flower (1 minuto)
run_all_tests.sh           ← Ejecuta TODO (8-10 minutos)
README_QA_SCRIPTS.md       ← Documentación completa
```

---

## ⚡ INICIO RÁPIDO (3 PASOS)

### Paso 1: Copiar scripts a tu proyecto

```bash
# Descarga los 6 scripts .sh desde /mnt/user-data/outputs/
# Cópialos a tu directorio raíz del proyecto
# (o donde prefieras, siempre en mismo directorio)

D:\Proyectos\read-team-saas\
├── docker-compose.yml
├── backend/
├── test_health_check.sh    ← Aquí
├── test_api.sh             ← Aquí
├── test_swagger.sh         ← Aquí
├── test_prometheus.sh      ← Aquí
├── test_flower.sh          ← Aquí
└── run_all_tests.sh        ← Aquí
```

### Paso 2: Hacer ejecutables

```bash
# Windows (PowerShell como Admin):
icacls test_*.sh /grant:r "%username%:F"
icacls run_all_tests.sh /grant:r "%username%:F"

# Linux/macOS:
chmod +x test_*.sh run_all_tests.sh
```

### Paso 3: Ejecutar

**OPCIÓN A: Verificación rápida (30 segundos)**
```bash
./test_health_check.sh
```

**OPCIÓN B: Suite completa (8-10 minutos)**
```bash
./run_all_tests.sh
```

**OPCIÓN C: Tests individuales**
```bash
./test_api.sh
./test_swagger.sh
./test_prometheus.sh
./test_flower.sh
```

---

## 📊 QUÉ VALIDAN

```
test_health_check.sh
├─ API está UP
├─ Swagger UI accesible
├─ Prometheus accesible
├─ Grafana accesible
└─ Flower accesible

test_api.sh
├─ GET /health
├─ POST /auth/register
├─ POST /auth/login
├─ GET /auth/me (protegido)
├─ POST /auth/refresh
├─ Error handling
├─ Headers correctos
└─ Performance < 100ms

test_swagger.sh
├─ Swagger UI cargable
├─ OpenAPI JSON válido
├─ Endpoints documentados
├─ Schemas documentados
├─ ReDoc accesible
└─ Performance < 2s

test_prometheus.sh
├─ Prometheus accesible
├─ API funciona
├─ Métricas disponibles
├─ Targets UP
└─ Performance < 1s

test_flower.sh
├─ Flower accesible
├─ API funciona
├─ Workers conectados
├─ Tasks API
└─ Performance < 2s
```

---

## ✅ EXPECTED OUTPUT

Si todo está bien:

```bash
$ ./test_health_check.sh

✓ API
✓ Swagger UI
✓ ReDoc
✓ Prometheus
✓ Grafana
✓ Flower

Servicios UP:   6
Servicios DOWN: 0

✓ TODOS LOS SERVICIOS ESTÁN FUNCIONANDO
```

---

## 📁 REPORTES GENERADOS

Cada script crea un `.txt` report:

```
test_api_report.txt
test_swagger_report.txt
test_prometheus_report.txt
test_flower_report.txt

# Plus, run_all_tests.sh genera:
qa_results_2025-03-28_14-30-45/
├── test_api_report.txt
├── test_swagger_report.txt
├── test_prometheus_report.txt
├── test_flower_report.txt
├── CONSOLIDATED_QA_REPORT.txt    ← Summary
└── QA_REPORT.html                ← Visual HTML
```

---

## 🎯 FLUJO RECOMENDADO

### Día a día:
```bash
# Antes de trabajar
./test_health_check.sh  # ~30 segundos

# Si todo está bien, trabajar
# Si algo falla, revisar qué pasó
```

### Pre-deployment:
```bash
# Validación completa
./run_all_tests.sh      # ~10 minutos

# Revisar reportes
cat qa_results_*/CONSOLIDATED_QA_REPORT.txt
```

### En CI/CD:
```bash
# Integrar en tu pipeline
# (GitHub Actions, GitLab CI, Jenkins, etc)
./run_all_tests.sh || exit 1
```

---

## ❌ TROUBLESHOOTING

### "API no está disponible"
```bash
# Verificar docker-compose
docker-compose ps

# Si no está corriendo:
docker-compose up -d

# Esperar ~20 segundos
./test_health_check.sh
```

### "command not found: curl"
```bash
# Windows: ya debe estar instalado en PowerShell
# Linux: sudo apt-get install curl
# macOS: brew install curl
```

### "Permission denied"
```bash
# Windows (PowerShell Admin):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Linux/macOS:
chmod +x *.sh
```

### Scripts lentos
- Docker necesita más recursos
- WiFi está lenta
- Ejecutar durante horas de no-pico

---

## 🔧 PERSONALIZACIÓN

Si tus URLs no están en localhost:

Editar cada script y cambiar:

```bash
# test_api.sh
API_URL="http://localhost:8000"  # Cambiar aquí

# test_swagger.sh
SWAGGER_URL="http://localhost:8000/api/docs"  # Cambiar aquí

# test_prometheus.sh
PROMETHEUS_URL="http://localhost:9090"  # Cambiar aquí

# Etc...
```

---

## 📝 EJEMPLO DE USO COMPLETO

```bash
# 1. Descargar scripts
# (ya los tienes en /mnt/user-data/outputs/)

# 2. Copiar a proyecto
cp test_*.sh run_all_tests.sh ~/proyectos/redteam-saas/

# 3. Hacer ejecutables
cd ~/proyectos/redteam-saas/
chmod +x *.sh

# 4. Verificación rápida
./test_health_check.sh
# Output: ✓ TODOS LOS SERVICIOS ESTÁN FUNCIONANDO

# 5. Suite completa
./run_all_tests.sh
# Output: Genera qa_results_2025-03-28_14-30-45/

# 6. Revisar reporte
cat qa_results_*/CONSOLIDATED_QA_REPORT.txt

# 7. Si TODO PASSED:
# ✓ READY FOR NEXT PHASE
```

---

## 📊 TIEMPOS

```
test_health_check.sh    ~30 segundos
test_api.sh             ~2 minutos
test_swagger.sh         ~1 minuto
test_prometheus.sh      ~1 minuto
test_flower.sh          ~1 minuto
────────────────────────────────────
run_all_tests.sh        ~8-10 minutos
```

---

## ✨ VENTAJAS vs PROMPT

| Aspecto | Prompt QA Gigante | Scripts BASH |
|---------|-------------------|--------------|
| Velocidad | Lento (VSCode) | ⚡ Rápido |
| Modularidad | Monolítico | Modular ✓ |
| Reutilizable | No | Sí ✓ |
| CI/CD compatible | No | Sí ✓ |
| Automatizable | Parcialmente | Completamente ✓ |
| Reportes | Texto | Texto + HTML ✓ |

---

## 🚀 PRÓXIMOS PASOS

1. **Descarga** los 6 scripts (.sh) desde `/mnt/user-data/outputs/`
2. **Copia** a tu proyecto
3. **Ejecuta** `./test_health_check.sh` para verificar
4. **Ejecuta** `./run_all_tests.sh` para validación completa
5. **Revisa** reportes
6. **¡Listo!** para siguiente fase

---

## 📞 PREGUNTAS

Si algo no funciona:
1. Revisar el output del script
2. Leer el reporte `.txt` generado
3. Revisar que los servicios están corriendo
4. Ejecutar nuevamente

---

**¿Listo?** 🚀

Descarga los scripts y comienza: `/mnt/user-data/outputs/`
