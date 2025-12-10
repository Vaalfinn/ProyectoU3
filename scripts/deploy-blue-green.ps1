# Script de Despliegue Blue/Green para Transaction Validator (PowerShell)
# Este script implementa una estrategia de despliegue sin downtime para Windows

param(
    [string]$CurrentEnv = "blue",
    [string]$NewEnv = "green",
    [int]$HealthCheckRetries = 30,
    [int]$HealthCheckInterval = 10,
    [int]$MonitoringPeriod = 300
)

# Configuración
$HEALTH_CHECK_URL_BLUE = "http://localhost:8000/health"
$HEALTH_CHECK_URL_GREEN = "http://localhost:8001/health"

# Función para imprimir con color
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Función para verificar health check
function Test-HealthCheck {
    param(
        [string]$Url,
        [int]$Retries,
        [int]$Interval
    )
    
    Write-Info "Verificando health check: $Url"
    
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Success "Health check exitoso (intento $i/$Retries)"
                return $true
            }
        }
        catch {
            Write-Warning "Health check falló (intento $i/$Retries)"
            if ($i -lt $Retries) {
                Start-Sleep -Seconds $Interval
            }
        }
    }
    
    Write-Error "Health check falló después de $Retries intentos"
    return $false
}

# Función de rollback
function Invoke-Rollback {
    Write-Error "Iniciando rollback a $CurrentEnv..."
    
    # Detener ambiente Green
    docker-compose stop transaction-validator-green
    
    # Asegurar que Blue está corriendo
    docker-compose up -d transaction-validator-blue
    
    # Actualizar Nginx
    docker-compose exec -T nginx sed -i 's/transaction_validator_green/transaction_validator_blue/g' /etc/nginx/nginx.conf
    docker-compose exec -T nginx nginx -s reload
    
    Write-Success "Rollback completado. Tráfico redirigido a $CurrentEnv"
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Blue
Write-Host "   PayFlow MX - Blue/Green Deployment" -ForegroundColor Blue
Write-Host "   Transaction Validator Microservice" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# PASO 1: Pre-deployment checks
Write-Info "Paso 1/7: Verificaciones pre-despliegue"
Write-Host ""

Write-Info "Verificando ambiente BLUE (actual)..."
if (-not (Test-HealthCheck -Url $HEALTH_CHECK_URL_BLUE -Retries 3 -Interval 5)) {
    Write-Error "El ambiente BLUE actual no está saludable. Abortando despliegue."
    exit 1
}
Write-Success "Ambiente BLUE está saludable"
Write-Host ""

# PASO 2: Deploy Green
Write-Info "Paso 2/7: Desplegando ambiente GREEN"
Write-Host ""

Write-Info "Construyendo nueva imagen..."
docker-compose build transaction-validator-green

Write-Info "Iniciando contenedor GREEN..."
docker-compose --profile green-deployment up -d transaction-validator-green

Start-Sleep -Seconds 10
Write-Success "Contenedor GREEN iniciado"
Write-Host ""

# PASO 3: Health Check Green
Write-Info "Paso 3/7: Verificando salud del ambiente GREEN"
Write-Host ""

if (-not (Test-HealthCheck -Url $HEALTH_CHECK_URL_GREEN -Retries $HealthCheckRetries -Interval $HealthCheckInterval)) {
    Write-Error "El ambiente GREEN no pasó el health check"
    Invoke-Rollback
}
Write-Success "Ambiente GREEN está saludable"
Write-Host ""

# PASO 4: Smoke Tests
Write-Info "Paso 4/7: Ejecutando smoke tests en GREEN"
Write-Host ""

Write-Info "Test 1: Endpoint raíz"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/" -Method Get -UseBasicParsing
    Write-Success "✓ Endpoint raíz responde correctamente"
}
catch {
    Write-Error "✗ Endpoint raíz falló"
    Invoke-Rollback
}

Write-Info "Test 2: Endpoint de validación"
$body = @{
    transaction_id   = "test-123"
    amount           = 1000
    currency         = "MXN"
    sender_account   = "1234567890"
    receiver_account = "0987654321"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/validate" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    Write-Success "✓ Endpoint de validación responde correctamente"
}
catch {
    Write-Error "✗ Endpoint de validación falló"
    Invoke-Rollback
}

Write-Info "Test 3: Métricas"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/metrics" -Method Get -UseBasicParsing
    Write-Success "✓ Endpoint de métricas responde correctamente"
}
catch {
    Write-Error "✗ Endpoint de métricas falló"
    Invoke-Rollback
}

Write-Success "Todos los smoke tests pasaron"
Write-Host ""

# PASO 5: Switch Traffic
Write-Info "Paso 5/7: Cambiando tráfico de BLUE a GREEN"
Write-Host ""

Write-Warning "Preparando para cambiar tráfico..."
Start-Sleep -Seconds 3

Write-Info "Actualizando configuración de Nginx..."
docker-compose exec -T nginx sh -c "sed -i 's/transaction_validator_blue/transaction_validator_green/g' /etc/nginx/nginx.conf"
docker-compose exec -T nginx nginx -s reload

Write-Success "Tráfico cambiado a GREEN"
Write-Host ""

# PASO 6: Monitoring Period
Write-Info "Paso 6/7: Período de monitoreo ($MonitoringPeriod segundos)"
Write-Host ""

$MonitoringInterval = 30
$Checks = [math]::Floor($MonitoringPeriod / $MonitoringInterval)

Write-Info "Monitoreando GREEN por $([math]::Floor($MonitoringPeriod/60)) minutos..."

for ($i = 1; $i -le $Checks; $i++) {
    Write-Info "Check $i/$Checks"
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:80/health" -Method Get -TimeoutSec 5 -UseBasicParsing
        Write-Info "Health check OK"
    }
    catch {
        Write-Error "Health check falló durante monitoreo"
        Invoke-Rollback
    }
    
    Start-Sleep -Seconds $MonitoringInterval
}

Write-Success "Período de monitoreo completado exitosamente"
Write-Host ""

# PASO 7: Finalization
Write-Info "Paso 7/7: Finalización del despliegue"
Write-Host ""

Write-Info "Deteniendo ambiente BLUE (antiguo)..."
docker-compose stop transaction-validator-blue

Write-Success "Ambiente BLUE detenido"
Write-Success "GREEN es ahora el ambiente de producción"
Write-Host ""

# Resumen
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "   DESPLIEGUE COMPLETADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Ambiente anterior: " -NoNewline; Write-Host "BLUE" -ForegroundColor Yellow
Write-Host "Ambiente nuevo:    " -NoNewline; Write-Host "GREEN" -ForegroundColor Green
Write-Host "URL producción:    " -NoNewline; Write-Host "http://localhost" -ForegroundColor Blue
Write-Host "URL Green directa: " -NoNewline; Write-Host "http://localhost:8001" -ForegroundColor Blue
Write-Host ""
Write-Host "Próximos pasos:"
Write-Host "  1. Monitorear dashboards en Grafana: http://localhost:3000"
Write-Host "  2. Verificar logs en Kibana: http://localhost:5601"
Write-Host "  3. Revisar trazas en Jaeger: http://localhost:16686"
Write-Host ""

# Guardar estado del despliegue
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "deployment-history.log" -Value "$timestamp - Deployed to GREEN successfully"

exit 0
