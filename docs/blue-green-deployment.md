# Guía de Despliegue Blue/Green
## Transaction Validator - PayFlow MX

---

## 1. Introducción

### 1.1 ¿Qué es Blue/Green Deployment?

Blue/Green Deployment es una estrategia de despliegue que reduce el downtime y el riesgo al ejecutar dos ambientes de producción idénticos:

- **BLUE:** Versión actualmente en producción
- **GREEN:** Nueva versión a desplegar

El tráfico se cambia atómicamente de Blue a Green una vez que la nueva versión está completamente validada.

### 1.2 Ventajas

✅ **Cero Downtime:** El cambio es instantáneo  
✅ **Rollback Rápido:** Solo cambiar tráfico de vuelta  
✅ **Testing en Producción:** Green se puede probar antes del switch  
✅ **Menor Riesgo:** Validación completa antes de afectar usuarios  

### 1.3 Desventajas

❌ **Doble Infraestructura:** Requiere recursos duplicados temporalmente  
❌ **Complejidad de Base de Datos:** Migraciones requieren ser backward-compatible  
❌ **Sincronización de Estado:** Sesiones y caché deben manejarse cuidadosamente  

---

## 2. Arquitectura

### 2.1 Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer (Nginx)                     │
│                                                                   │
│  Route: / ──────────► [ Active: Blue/Green ]                    │
│  Route: /blue ───────► [ Blue (Direct) ]                        │
│  Route: /green ──────► [ Green (Direct) ]                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
    ┌─────────────────────┐ ┌─────────────────────┐
    │   BLUE ENVIRONMENT  │ │  GREEN ENVIRONMENT  │
    │                     │ │                     │
    │ • Port: 8000        │ │ • Port: 8001        │
    │ • Version: 1.0.0    │ │ • Version: 1.1.0    │
    │ • Status: Active    │ │ • Status: Standby   │
    └─────────────────────┘ └─────────────────────┘
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │  Shared Infrastructure   │
              │                          │
              │  • Database              │
              │  • Redis Cache           │
              │  • Message Queue         │
              │  • Monitoring            │
              └──────────────────────────┘
```

### 2.2 Estados del Sistema

#### Estado 1: Blue Activo (Normal)
```
Traffic Flow: Users → Nginx → Blue:8000
Blue: Running (v1.0.0)
Green: Stopped
```

#### Estado 2: Preparando Green
```
Traffic Flow: Users → Nginx → Blue:8000
Blue: Running (v1.0.0)
Green: Starting (v1.1.0)
```

#### Estado 3: Validando Green
```
Traffic Flow: Users → Nginx → Blue:8000
              Tests → Green:8001
Blue: Running (v1.0.0)
Green: Testing (v1.1.0)
```

#### Estado 4: Switched to Green
```
Traffic Flow: Users → Nginx → Green:8001
Blue: Running (v1.0.0) - Standby
Green: Active (v1.1.0)
```

#### Estado 5: Green Activo (Nuevo Normal)
```
Traffic Flow: Users → Nginx → Green:8001
Blue: Stopped
Green: Active (v1.1.0)
```

---

## 3. Proceso de Despliegue

### 3.1 Pre-requisitos

**Checklist antes de despliegue:**

- [ ] Código revisado y aprobado
- [ ] Todos los tests pasan
- [ ] Security scan completado
- [ ] Database migrations probadas
- [ ] Rollback plan documentado
- [ ] Equipo notificado
- [ ] Monitoring dashboards abiertos
- [ ] On-call engineer disponible

### 3.2 Paso a Paso

#### PASO 1: Verificación Pre-Despliegue (2-3 min)

```powershell
# Verificar que Blue está saludable
Invoke-WebRequest -Uri http://localhost:8000/health

# Verificar métricas actuales
Invoke-WebRequest -Uri http://localhost:9090/api/v1/query?query=up{job="transaction-validator-blue"}

# Verificar error budget disponible
# Debe tener > 25% disponible para proceder
```

**Criterios de GO:**
- ✅ Blue responde healthy
- ✅ Error rate < 0.1%
- ✅ Latency normal
- ✅ Error budget > 25%

#### PASO 2: Deploy Green (3-5 min)

```powershell
# Construir nueva imagen
docker-compose build transaction-validator-green

# Iniciar Green environment
docker-compose --profile green-deployment up -d transaction-validator-green

# Ver logs en tiempo real
docker-compose logs -f transaction-validator-green
```

**Monitorear:**
- Container status
- Memory usage
- CPU usage
- Startup time

#### PASO 3: Health Check Green (5-10 min)

```powershell
# Script automático de health check
.\scripts\deploy-blue-green.ps1

# O manual:
for ($i=1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri http://localhost:8001/health -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "Health check OK ($i/30)" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "Health check failed ($i/30)" -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 10
}
```

**Criterios de éxito:**
- ✅ Health check responde 200
- ✅ Readiness check OK
- ✅ Dependencies conectadas
- ✅ Sin errores en logs

#### PASO 4: Smoke Tests (5 min)

```powershell
# Test 1: API básica
$response = Invoke-WebRequest -Uri http://localhost:8001/ -Method Get
Write-Host "Root endpoint: $($response.StatusCode)"

# Test 2: Validación de transacción
$body = @{
    transaction_id = "smoke-test-001"
    amount = 1000
    currency = "MXN"
    sender_account = "1234567890"
    receiver_account = "0987654321"
} | ConvertTo-Json

$response = Invoke-WebRequest `
    -Uri http://localhost:8001/api/v1/validate `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

Write-Host "Validation endpoint: $($response.StatusCode)"

# Test 3: Métricas
$response = Invoke-WebRequest -Uri http://localhost:8001/metrics
Write-Host "Metrics endpoint: $($response.StatusCode)"

# Test 4: Trazas (verificar en Jaeger UI)
# http://localhost:16686
```

**Test Suite Completo:**
```
✓ Endpoint raíz responde
✓ Health check funciona
✓ Validación de transacciones funciona
✓ Métricas se exportan
✓ Logs se envían a ELK
✓ Trazas se envían a Jaeger
✓ Base de datos conectada
✓ Redis/Cache funciona
```

#### PASO 5: Integration Tests (5 min)

```powershell
# Ejecutar suite de integration tests
docker-compose exec transaction-validator-green pytest tests/integration/ -v

# O usando k6 para test ligero
k6 run k6/smoke-test.js --env BASE_URL=http://localhost:8001
```

#### PASO 6: Traffic Switch (1 min)

```powershell
# Actualizar Nginx para apuntar a Green
docker-compose exec -T nginx sh -c `
    "sed -i 's/transaction_validator_blue/transaction_validator_green/g' /etc/nginx/nginx.conf"

# Reload Nginx sin downtime
docker-compose exec -T nginx nginx -s reload

# Verificar que el cambio se aplicó
Invoke-WebRequest -Uri http://localhost/health
```

**Validación del switch:**
```powershell
# Debe responder desde Green (v1.1.0)
$response = Invoke-WebRequest -Uri http://localhost/ | ConvertFrom-Json
Write-Host "Active version: $($response.version)"
```

#### PASO 7: Monitoring Period (5-10 min)

```powershell
# Script de monitoreo automático
$duration = 300  # 5 minutos
$interval = 30   # Check cada 30 segundos
$checks = $duration / $interval

for ($i=1; $i -le $checks; $i++) {
    Write-Host "Monitoring check $i/$checks" -ForegroundColor Blue
    
    # Health check
    try {
        $health = Invoke-WebRequest -Uri http://localhost/health -TimeoutSec 5
        Write-Host "  Health: OK" -ForegroundColor Green
    }
    catch {
        Write-Host "  Health: FAIL - ROLLBACK!" -ForegroundColor Red
        # Ejecutar rollback
        exit 1
    }
    
    # Métricas desde Prometheus
    $query = "rate(transaction_validator_requests_total{status=~`"5..`"}[1m])"
    $prometheusUrl = "http://localhost:9090/api/v1/query?query=$query"
    $metrics = Invoke-RestMethod -Uri $prometheusUrl
    
    $errorRate = $metrics.data.result[0].value[1]
    Write-Host "  Error rate: $errorRate"
    
    if ($errorRate -gt 0.01) {  # > 1%
        Write-Host "  High error rate - ROLLBACK!" -ForegroundColor Red
        # Ejecutar rollback
        exit 1
    }
    
    Start-Sleep -Seconds $interval
}

Write-Host "Monitoring period completed successfully!" -ForegroundColor Green
```

**Métricas monitoreadas:**
- HTTP error rate
- Latency P95/P99
- Throughput
- Active connections
- Memory/CPU usage
- Database connections
- Cache hit rate

#### PASO 8: Finalización (1-2 min)

```powershell
# Detener Blue (ya no necesario)
docker-compose stop transaction-validator-blue

# Opcional: Eliminar para liberar recursos
# docker-compose rm -f transaction-validator-blue

# Guardar estado del deployment
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logEntry = "$timestamp - Deployed v1.1.0 to GREEN successfully"
Add-Content -Path deployment-history.log -Value $logEntry

# Notificar al equipo
# Send-SlackNotification -Message "✅ Deployment to GREEN completed successfully"
```

---

## 4. Rollback

### 4.1 Rollback Automático

El script detecta automáticamente y hace rollback si:

```powershell
# Condiciones de rollback automático
if (
    $healthCheckFails -ge 3 -or
    $smokeTestsFail -or
    $errorRate -gt 0.05 -or
    $latencyP99 -gt 2000
) {
    Invoke-Rollback
}
```

### 4.2 Rollback Manual

```powershell
# Switch rápido de vuelta a Blue
docker-compose exec -T nginx sh -c `
    "sed -i 's/transaction_validator_green/transaction_validator_blue/g' /etc/nginx/nginx.conf"

docker-compose exec -T nginx nginx -s reload

# Verificar
Invoke-WebRequest -Uri http://localhost/

# Detener Green
docker-compose stop transaction-validator-green

# Analizar qué salió mal
docker-compose logs transaction-validator-green > rollback-logs.txt
```

### 4.3 Tiempo de Rollback

**Objetivo:** < 2 minutos

```
Detección de problema: 30 segundos
Switch de tráfico: 10 segundos
Verificación: 30 segundos
Notificación: 10 segundos
──────────────────────────────
Total: ~1.5 minutos
```

---

## 5. Casos Especiales

### 5.1 Database Migrations

**Regla de oro:** Migrations deben ser backward-compatible

```python
# ✅ CORRECTO: Agregar columna con default
ALTER TABLE transactions ADD COLUMN risk_score FLOAT DEFAULT 0.0;

# ❌ INCORRECTO: Eliminar columna
ALTER TABLE transactions DROP COLUMN old_field;

# ✅ CORRECTO (en dos deployments):
# Deploy 1: Dejar de usar la columna
# Deploy 2: Eliminar la columna
```

**Estrategia:**
1. Deploy 1: Agregar nuevas columnas/tablas
2. Ambos Blue y Green funcionan
3. Deploy 2: Eliminar código viejo
4. Deploy 3: Eliminar columnas/tablas viejas

### 5.2 Cache Warming

```powershell
# Calentar cache de Green antes del switch
for ($i=1; $i -le 100; $i++) {
    Invoke-WebRequest -Uri "http://localhost:8001/api/v1/validate" -Method Post ...
}
```

### 5.3 Session Management

**Opciones:**

1. **Sticky Sessions:** Nginx mantiene usuarios en mismo backend
2. **Shared Session Store:** Redis para sesiones compartidas
3. **Stateless:** Sin sesiones (recomendado para microservicios)

Para Transaction Validator usamos **stateless** (sin sesiones).

---

## 6. Monitoreo Durante Despliegue

### 6.1 Dashboards Críticos

**Abrir antes de despliegue:**

1. **Service Overview**
   - http://localhost:3000/d/payflow-tx-validator
   - Métricas de disponibilidad, latencia, errores

2. **Infrastructure**
   - CPU, memoria, disco, red
   - Por ambiente (Blue vs Green)

3. **Business Metrics**
   - Transacciones procesadas
   - Tasa de aprobación/rechazo

### 6.2 Queries Útiles de Prometheus

```promql
# Error rate por ambiente
rate(transaction_validator_requests_total{status=~"5..",deployment_color="green"}[1m])

# Latencia P95 comparativa
histogram_quantile(0.95,
  sum by (le, deployment_color) (
    rate(transaction_validator_request_duration_seconds_bucket[5m])
  )
)

# Throughput por ambiente
sum by (deployment_color) (
  rate(transaction_validator_requests_total[1m])
)
```

### 6.3 Logs en Kibana

```
Filtro durante despliegue:
- service: transaction-validator
- deployment_color: green
- level: error OR warning
- @timestamp: last 15 minutes
```

### 6.4 Trazas en Jaeger

```
Service: transaction-validator
Tags: deployment.color=green
Lookback: 10 minutes
Min Duration: 500ms (para encontrar requests lentos)
```

---

## 7. Troubleshooting

### 7.1 Green no inicia

```powershell
# Ver logs detallados
docker-compose logs --tail=100 transaction-validator-green

# Verificar puertos
netstat -ano | findstr 8001

# Verificar recursos
docker stats transaction-validator-green

# Entrar al container
docker-compose exec transaction-validator-green sh
```

### 7.2 Health check falla

```powershell
# Verificar endpoint directamente
Invoke-WebRequest -Uri http://localhost:8001/health -Verbose

# Ver logs de la aplicación
docker-compose logs -f transaction-validator-green | Select-String "error"

# Verificar dependencias
docker-compose exec transaction-validator-green ping elasticsearch
docker-compose exec transaction-validator-green ping prometheus
```

### 7.3 Smoke tests fallan

```powershell
# Test manual paso a paso
# 1. Root endpoint
Invoke-WebRequest -Uri http://localhost:8001/

# 2. Health
Invoke-WebRequest -Uri http://localhost:8001/health

# 3. Validation con verbose
Invoke-WebRequest -Uri http://localhost:8001/api/v1/validate `
    -Method Post -Body $testBody -ContentType "application/json" -Verbose
```

### 7.4 Alto error rate post-switch

```powershell
# Rollback inmediato
.\scripts\rollback.ps1

# Capturar evidencia
docker-compose logs transaction-validator-green > incident-logs.txt

# Consultar métricas de Prometheus
$query = "rate(transaction_validator_requests_total{status=~`"5..`"}[5m])"
Invoke-RestMethod -Uri "http://localhost:9090/api/v1/query?query=$query"

# Revisar trazas en Jaeger
# Buscar requests con errores
```

---

## 8. Checklist de Despliegue

### Pre-Deployment

- [ ] PR aprobado y mergeado
- [ ] CI/CD pipeline pasó
- [ ] Security scan limpio
- [ ] Database migrations probadas
- [ ] Documentación actualizada
- [ ] Equipo notificado (#deployments)
- [ ] Dashboards de monitoreo abiertos
- [ ] On-call engineer disponible
- [ ] Error budget > 25%

### During Deployment

- [ ] Blue verificado healthy
- [ ] Green construido y iniciado
- [ ] Health checks pasando
- [ ] Smoke tests completados
- [ ] Integration tests OK
- [ ] Métricas normales
- [ ] Tráfico switched
- [ ] Monitoring period (5 min) OK

### Post-Deployment

- [ ] Green es ahora producción
- [ ] Blue detenido
- [ ] Logs revisados
- [ ] Métricas estables
- [ ] SLOs cumplidos
- [ ] Error budget actualizado
- [ ] Deployment log actualizado
- [ ] Equipo notificado del éxito

---

## 9. Métricas de Deployment

### KPIs del Proceso

| Métrica | Objetivo | Tracking |
|---------|----------|----------|
| Deployment Frequency | > 1/día | GitHub Actions |
| Lead Time | < 1 hora | GitHub → Production |
| Deployment Duration | < 15 min | Script timing |
| Rollback Rate | < 5% | Incident log |
| Rollback Time | < 2 min | Script timing |

---

## 10. Referencias

- **Docker Compose:** `docker-compose.yml`
- **Deployment Script:** `scripts/deploy-blue-green.ps1`
- **Nginx Config:** `monitoring/nginx/nginx.conf`