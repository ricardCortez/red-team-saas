# SCRIPT POWERSHELL CORREGIDO - Fase 1 Setup
# Ejecutar en: D:\Proyectos\read-team-saas

Write-Host "=== RED TEAM SAAS - SETUP FINAL ===" -ForegroundColor Green
Write-Host "Estimado: 2-3 minutos" -ForegroundColor Cyan

# OPCIÓN 1: INSTALAR LOCALMENTE PRIMERO (MÁS SEGURO)
Write-Host "`n[PASO 1] Instalar dependencias localmente primero..." -ForegroundColor Yellow

$backendPath = Join-Path (Get-Location) "backend"
$venvPath = Join-Path $backendPath "venv"

# Crear venv
if (-not (Test-Path $venvPath)) {
    Write-Host "Creando virtual environment..." -ForegroundColor Cyan
    python -m venv $venvPath
}

# Activar venv
Write-Host "Activando venv..." -ForegroundColor Cyan
& "$venvPath\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip setuptools wheel

# Crear requirements.txt correcto
Write-Host "Creando requirements.txt..." -ForegroundColor Cyan
$requirementsContent = @"
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.7.0
pydantic-settings==2.2.1
sqlalchemy==2.0.27
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.6
PyJWT==2.8.1
python-multipart==0.0.6
bcrypt==4.1.2
cryptography==42.0.2
python-dotenv==1.0.0
email-validator==2.1.0
passlib==1.7.4
"@
$requirementsContent | Out-File -FilePath "$backendPath\requirements.txt" -Encoding UTF8

# Instalar localmente
Write-Host "Instalando dependencias localmente..." -ForegroundColor Cyan
pip install -r "$backendPath\requirements.txt"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencias instaladas correctamente localmente" -ForegroundColor Green
} else {
    Write-Host "❌ Error al instalar localmente" -ForegroundColor Red
    Write-Host "Verifica el error arriba e intenta manualmente:" -ForegroundColor Yellow
    Write-Host "pip install -r backend/requirements.txt -vvv" -ForegroundColor Gray
    exit 1
}

# Deactivate venv
Write-Host "Desactivando venv..." -ForegroundColor Cyan
deactivate

# OPCIÓN 2: AHORA DOCKER TIENE LOS PACKAGES CORRECTOS
Write-Host "`n[PASO 2] Setup de Docker..." -ForegroundColor Yellow

# Crear Dockerfile correcto
Write-Host "Creando Dockerfile..." -ForegroundColor Cyan
$dockerfileContent = @"
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@
$dockerfileContent | Out-File -FilePath "$backendPath\Dockerfile" -Encoding UTF8

# Actualizar docker-compose.yml
Write-Host "Actualizando docker-compose.yml..." -ForegroundColor Cyan
$dcContent = Get-Content "docker-compose.yml"
$dcContent = $dcContent -replace "^version: '3\.8'", "# Docker Compose v2"
$dcContent | Set-Content "docker-compose.yml"

# Docker cleanup
Write-Host "`n[PASO 3] Limpieza de Docker..." -ForegroundColor Yellow
docker-compose down 2>$null | Out-Null
Write-Host "Removiendo images viejas..." -ForegroundColor Cyan
docker rmi redteam-api redteam-celery -f 2>$null | Out-Null
docker system prune -f 2>$null | Out-Null

# Rebuild
Write-Host "`n[PASO 4] Rebuild de Docker..." -ForegroundColor Yellow
docker-compose build --no-cache

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error en Docker build" -ForegroundColor Red
    Write-Host "Intenta ver logs: docker-compose logs api" -ForegroundColor Yellow
    exit 1
}

# Levantar servicios
Write-Host "`n[PASO 5] Levantando servicios..." -ForegroundColor Yellow
docker-compose up -d

# Esperar
Write-Host "Esperando 30 segundos..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# Verificar estado
Write-Host "`n[PASO 6] Verificando estado..." -ForegroundColor Yellow
docker-compose ps

# Test (SINTAXIS CORRECTA POWERSHELL)
Write-Host "`n[PASO 7] Testeando health check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $content = $response.Content | ConvertFrom-Json
        Write-Host "✅ ¡ÉXITO! Servicios corriendo correctamente" -ForegroundColor Green
        Write-Host "Response: $($response.Content)" -ForegroundColor Green
        Write-Host "`n📊 Próximos pasos:" -ForegroundColor Cyan
        Write-Host "1. Abre: http://localhost:8000/docs (Swagger UI)" -ForegroundColor Cyan
        Write-Host "2. O ejecuta: curl http://localhost:8000/" -ForegroundColor Cyan
        Write-Host "3. Continúa con Fase 1 + PROMPT DELTA" -ForegroundColor Cyan
    }
} catch {
    Write-Host "⚠️  Health check falló" -ForegroundColor Yellow
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Intenta: docker-compose logs api" -ForegroundColor Yellow
}

Write-Host "`n=== SETUP COMPLETO ===" -ForegroundColor Green