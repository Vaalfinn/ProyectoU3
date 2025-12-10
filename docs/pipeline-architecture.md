# Arquitectura del Pipeline CI/CD
## Transaction Validator - PayFlow MX

---

## 1. Descripción General

El pipeline CI/CD implementa un flujo completo de integración y despliegue continuo para el microservicio Transaction Validator, garantizando calidad, seguridad y despliegues sin downtime.

## 2. Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                            │
│                    (Source Code + Configuration)                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            │ Push/PR
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       GitHub Actions (CI/CD)                         │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Stage 1: BUILD & TEST                                        │   │
│  │ • Checkout code                                             │   │
│  │ • Setup Python 3.11                                         │   │
│  │ • Install dependencies                                      │   │
│  │ • Run unit tests (pytest)                                   │   │
│  │ • Generate coverage reports                                 │   │
│  │ • Upload to Codecov                                         │   │
│  └────────────┬────────────────────────────────────────────────┘   │
│               │ ✅ Tests Pass                                       │
│               ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Stage 2: SECURITY SCAN                                       │   │
│  │ • Run Trivy vulnerability scanner                           │   │
│  │ • Check dependencies (Snyk/Dependabot)                      │   │
│  │ • SAST analysis                                             │   │
│  │ • Upload results to GitHub Security                         │   │
│  └────────────┬────────────────────────────────────────────────┘   │
│               │ ✅ No Critical Vulnerabilities                      │
│               ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Stage 3: BUILD DOCKER IMAGE                                  │   │
│  │ • Setup Docker Buildx                                       │   │
│  │ • Login to Container Registry (GHCR)                        │   │
│  │ • Build Docker image                                        │   │
│  │ • Tag: latest, version, sha                                 │   │
│  │ • Push to registry                                          │   │
│  │ • Scan Docker image (Trivy)                                 │   │
│  └────────────┬────────────────────────────────────────────────┘   │
│               │ ✅ Image Built & Scanned                            │
│               ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Stage 4: DEPLOY (Blue/Green)                                 │   │
│  │ • Deploy to Green environment                               │   │
│  │ • Health checks (30 retries)                                │   │
│  │ • Smoke tests                                               │   │
│  │ • Integration tests                                         │   │
│  │ • Switch traffic (Blue → Green)                             │   │
│  │ • Monitor for 5 minutes                                     │   │
│  │ • Rollback on failure                                       │   │
│  └────────────┬────────────────────────────────────────────────┘   │
│               │ ✅ Deployment Successful                            │
│               ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Stage 5: POST-DEPLOYMENT VALIDATION                          │   │
│  │ • Run load tests (k6)                                       │   │
│  │ • Verify SLO compliance                                     │   │
│  │ • Check error budget                                        │   │
│  │ • Generate deployment report                                │   │
│  └────────────┬────────────────────────────────────────────────┘   │
│               │ ✅ Validation Complete                              │
│               ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Stage 6: CLEANUP                                             │   │
│  │ • Remove old container images                               │   │
│  │ • Clean build cache                                         │   │
│  │ • Archive logs and reports                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │ Metrics & Logs
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Monitoring & Observability                        │
│  • Prometheus (métricas)                                            │
│  • Grafana (dashboards)                                             │
│  • Jaeger (trazas)                                                  │
│  • ELK Stack (logs)                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes del Pipeline

### 3.1 Triggers

El pipeline se activa automáticamente en:

- **Push a main:** Despliegue completo a producción
- **Push a develop:** Despliegue a ambiente de staging
- **Pull Request:** Solo build, test y security scan

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

### 3.2 Jobs y Stages

#### Job 1: Build & Test
**Duración estimada:** 2-3 minutos

```yaml
Pasos:
1. Checkout código
2. Configurar Python 3.11
3. Instalar dependencias (con cache)
4. Ejecutar pytest con coverage
5. Generar reportes
6. Subir a Codecov
```

**Criterios de éxito:**
- ✅ Todos los tests pasan (100%)
- ✅ Coverage > 80%
- ✅ Sin errores de lint

**Salida:**
- Test report (JUnit XML)
- Coverage report (XML, HTML)
- Artifacts para análisis

#### Job 2: Security Scan
**Duración estimada:** 1-2 minutos

```yaml
Pasos:
1. Scan de filesystem con Trivy
2. Análisis de dependencias
3. SAST (Static Application Security Testing)
4. Upload a GitHub Security
```

**Criterios de éxito:**
- ✅ Sin vulnerabilidades críticas
- ✅ Sin vulnerabilidades altas sin mitigar
- ⚠️ Vulnerabilidades medias documentadas

**Salida:**
- SARIF report
- Security advisory

#### Job 3: Build Docker Image
**Duración estimada:** 3-5 minutos

```yaml
Pasos:
1. Setup Docker Buildx (multi-platform)
2. Login a GHCR
3. Extract metadata
4. Build con cache layers
5. Push a registry
6. Scan image con Trivy
```

**Estrategia de tags:**
```
ghcr.io/payflow/transaction-validator:latest
ghcr.io/payflow/transaction-validator:1.0.0
ghcr.io/payflow/transaction-validator:main-abc1234
ghcr.io/payflow/transaction-validator:pr-123
```

**Optimizaciones:**
- BuildKit cache
- Multi-stage builds
- Layer caching

#### Job 4: Deploy Blue/Green
**Duración estimada:** 10-15 minutos

```yaml
Pasos:
1. Deploy a Green
2. Health check (30 retries × 10s)
3. Smoke tests (3-5 tests críticos)
4. Switch traffic
5. Monitor (5 minutos)
6. Rollback si falla
```

**Validaciones:**
- Health endpoint returns 200
- API responds correctamente
- Métricas normales
- Sin errores en logs

#### Job 5: Post-Deployment
**Duración estimada:** 5-10 minutos

```yaml
Pasos:
1. Run k6 load tests
2. Verificar SLOs
3. Check error budget
4. Generate report
```

**Métricas verificadas:**
- Latencia P95 < 250ms
- Latencia P99 < 500ms
- Error rate < 0.1%
- Throughput adecuado

#### Job 6: Cleanup
**Duración estimada:** 1-2 minutos

```yaml
Pasos:
1. Delete old images (mantener últimas 10)
2. Clean workspace
3. Archive artifacts
```

---

## 4. Estrategia de Branching

```
main (production)
  └─ develop (staging)
       └─ feature/TX-123
       └─ bugfix/TX-456
       └─ hotfix/TX-789
```

### Reglas:

1. **main:** Protegida, requiere PR + reviews + checks
2. **develop:** Protegida, requiere PR + checks
3. **feature/*:** Libre para desarrollo
4. **hotfix/*:** Deploy directo a main después de approval

---

## 5. Rollback Strategy

### Rollback Automático

Se activa automáticamente si:
- Health check falla 3 veces consecutivas
- Smoke tests fallan
- Error rate > 5% en primeros 5 minutos
- Latencia P99 > 2s

### Rollback Manual

```bash
# PowerShell
.\scripts\deploy-blue-green.ps1 -Rollback

# Bash
./scripts/deploy-blue-green.sh rollback
```

### Proceso de Rollback

```
1. Detectar falla
2. Log del error
3. Notificar al equipo
4. Switch tráfico a Blue
5. Stop Green environment
6. Crear incident ticket
7. Postmortem
```

**Tiempo objetivo de rollback:** < 2 minutos

---

## 6. Environments

| Environment | Branch | URL | Propósito |
|-------------|--------|-----|-----------|
| **Development** | feature/* | localhost | Desarrollo local |
| **Staging** | develop | staging.payflow.mx | QA y testing |
| **Production Blue** | main | api.payflow.mx | Producción activa |
| **Production Green** | main | green.payflow.mx | Nuevo despliegue |

---

## 7. Secrets y Configuración

### GitHub Secrets Requeridos

```yaml
GITHUB_TOKEN          # Auto-generado
DOCKERHUB_TOKEN       # Para pull de imágenes base
CODECOV_TOKEN         # Para reportes de coverage
SLACK_WEBHOOK         # Notificaciones
PAGERDUTY_KEY         # Alertas críticas
```

### Variables de Entorno

```yaml
APP_VERSION           # Versión del app
ENVIRONMENT           # production/staging
DEPLOYMENT_COLOR      # blue/green
JAEGER_HOST          # Host de Jaeger
PROMETHEUS_URL       # URL de Prometheus
```

---

## 8. Monitoreo del Pipeline

### Métricas del Pipeline

- **Success Rate:** > 95%
- **Build Time:** < 10 minutos
- **Deployment Time:** < 15 minutos
- **Rollback Time:** < 2 minutos

### Dashboard

Grafana dashboard: "CI/CD Pipeline Metrics"

Métricas rastreadas:
- Pipeline execution time
- Success/failure rate
- Deployment frequency
- Mean time to recovery (MTTR)
- Change failure rate

---

## 9. Notificaciones

### Canales

1. **Slack:** `#deployments`
   - Inicio de deployment
   - Resultado (success/failure)
   - Métricas clave

2. **Email:** team@payflow.mx
   - Resumen diario de deployments
   - Reportes semanales

3. **PagerDuty:** On-call engineers
   - Solo para fallos críticos
   - Requiere acción inmediata

### Formato de Notificación

```
🚀 DEPLOYMENT STARTED
Service: transaction-validator
Version: 1.2.0
Branch: main
Commit: abc1234
Deployer: @john.doe

Status: 🟢 In Progress
Estimated time: 15 minutes
```

---

## 10. Mejores Prácticas

### ✅ DO

- Commits pequeños y frecuentes
- Tests antes de PR
- Descriptive commit messages
- Review de código
- Documentar cambios
- Monitorear post-deployment

### ❌ DON'T

- Push directo a main
- Skip tests
- Deploy sin smoke tests
- Ignorar alertas
- Deploy en viernes tarde
- Múltiples features en un PR

---

## 11. Troubleshooting

### Pipeline Falla en Tests

```bash
# Ver logs detallados
gh run view <run-id> --log

# Re-ejecutar solo job fallido
gh run rerun <run-id> --job <job-id>
```

### Build Docker Falla

```bash
# Build local para debugging
docker build -t transaction-validator:debug .

# Inspeccionar capas
docker history transaction-validator:debug
```

### Deployment Falla

```bash
# Ver logs del deployment
docker-compose logs transaction-validator-green

# Check health manualmente
curl http://localhost:8001/health
```

---

## 12. Métricas de DevOps (DORA)

| Métrica | Objetivo | Actual |
|---------|----------|--------|
| **Deployment Frequency** | > 1/día | - |
| **Lead Time for Changes** | < 1 hora | - |
| **Time to Restore Service** | < 1 hora | - |
| **Change Failure Rate** | < 15% | - |

---

## 13. Referencias

- **GitHub Actions Docs:** https://docs.github.com/actions


