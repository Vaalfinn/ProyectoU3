# PayFlow MX - Transaction Validator Microservice

## 🎯 Descripción del Proyecto

Microservicio crítico de validación de transacciones para la plataforma fintech PayFlow MX. Este proyecto implementa un pipeline completo de CI/CD con despliegue Blue/Green, sistema de observabilidad de tres pilares (métricas, logs y trazas) y monitoreo basado en SLO/SLI.

## 🏗️ Arquitectura

```
Transaction-Validator/
├── src/                    # Código fuente del microservicio
├── tests/                  # Pruebas automatizadas
├── .github/workflows/      # Pipelines CI/CD
├── docker/                 # Configuraciones Docker
├── monitoring/             # Configuración de monitoreo
│   ├── prometheus/         # Métricas
│   ├── grafana/           # Dashboards
│   ├── jaeger/            # Trazas distribuidas
│   └── elk/               # Logs centralizados
├── k6/                    # Scripts de pruebas de carga
├── docs/                  # Documentación técnica
└── infrastructure/        # Scripts de infraestructura
```

## 🚀 Características Principales

- ✅ **Pipeline CI/CD automatizado** con GitHub Actions
- ✅ **Despliegue Blue/Green** con cero downtime
- ✅ **Rollback automático** en caso de fallas
- ✅ **Monitoreo completo**: Prometheus + Grafana + Jaeger + ELK
- ✅ **Pruebas de carga** con k6
- ✅ **SLA/SLO/SLI** definidos y medibles
- ✅ **Trazas distribuidas** con OpenTelemetry

## 📊 Indicadores de Servicio

### SLA (Service Level Agreement)
- **Disponibilidad**: 99.5% mensual
- **Soporte**: 24/7
- **Tiempo de respuesta a incidentes críticos**: < 15 minutos

### SLO (Service Level Objective)
- **Disponibilidad**: 99.7% mensual
- **Latencia P95**: < 250ms
- **Latencia P99**: < 500ms
- **Tasa de errores**: < 0.1%

### SLI (Service Level Indicator)
- Disponibilidad = (requests exitosos / total requests) × 100
- Latencia = tiempo de respuesta medido en percentiles
- Error rate = (requests con error / total requests) × 100

### Presupuesto de Errores
- **Mensual**: 43.2 minutos de downtime permitido
- **Diario**: 1.44 minutos de downtime permitido
- **Por cada 1000 requests**: 1 error permitido

## 🛠️ Tecnologías Utilizadas

- **Backend**: Python 3.11 + FastAPI
- **Contenedorización**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Métricas**: Prometheus + Grafana
- **Logs**: Elasticsearch + Logstash + Kibana
- **Trazas**: Jaeger + OpenTelemetry
- **Pruebas de carga**: k6
- **Orquestación**: Docker Swarm (simulación Blue/Green)

## 📦 Inicio Rápido

### Prerrequisitos
```bash
- Docker Desktop 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Git
```

### Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/AlanGaBer11/ProyectoUnidad3
cd payflow-transaction-validator
```

2. Construir e iniciar todos los servicios:
```bash
docker-compose up -d
```

3. Verificar que todos los servicios estén corriendo:
```bash
docker-compose ps
```

### Acceso a Servicios

- **API Transaction-Validator**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger UI**: http://localhost:16686
- **Kibana**: http://localhost:5601
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Load Balancer (Nginx)**: http://localhost:9080

## 🧪 Pruebas

### Ejecutar pruebas unitarias:
```bash
docker-compose exec transaction-validator pytest tests/ -v
```

### Ejecutar pruebas de carga:
```bash
k6 run k6/load-test.js
```

### Ejecutar pruebas de estrés:
```bash
k6 run k6/stress-test.js
```

## 🔄 Pipeline CI/CD

El pipeline se ejecuta automáticamente en cada push a `main` o `develop`:

1. **Build**: Construcción del artefacto
2. **Test**: Ejecución de pruebas automatizadas
3. **Security**: Análisis de vulnerabilidades
4. **Package**: Creación de imagen Docker
5. **Deploy Blue/Green**: Despliegue sin downtime
6. **Validation**: Pruebas post-despliegue
7. **Rollback**: Automático si falla la validación

## 📈 Monitoreo y Alertas

### Dashboards Principales

1. **Service Overview**: Métricas generales del servicio
2. **Performance**: Latencia, throughput, errores
3. **Infrastructure**: CPU, memoria, I/O, red
4. **Business Metrics**: Transacciones procesadas, validaciones

### Alertas Configuradas

- Disponibilidad < 99.7%
- Latencia P95 > 250ms
- Tasa de errores > 0.1%
- CPU > 80% por más de 5 minutos
- Memoria > 85%

## 🔧 Troubleshooting

### Ver logs en tiempo real:
```bash
docker-compose logs -f transaction-validator
```

### Reiniciar un servicio específico:
```bash
docker-compose restart transaction-validator
```

### Verificar salud del servicio:
```bash
curl http://localhost:8000/health
```

## 📚 Documentación Adicional

- [Arquitectura del Pipeline](docs/pipeline-architecture.md)
- [Guía de Despliegue Blue/Green](docs/blue-green-deployment.md)
- [Manual de Monitoreo](docs/monitoring-guide.md)
- [Plan de Mejora](docs/improvement-plan.md)
- [SLA/SLO/SLI Detallado](docs/sla-slo-sli.md)

