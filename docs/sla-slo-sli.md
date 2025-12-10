# SLA, SLO, SLI y Presupuesto de Errores
## Transaction Validator - PayFlow MX

**Documento Técnico v1.0**  
**Fecha:** Diciembre 2025  
**Servicio:** Transaction Validator Microservice

---

## 1. Resumen Ejecutivo

Este documento define los acuerdos de nivel de servicio (SLA), objetivos de nivel de servicio (SLO), indicadores de nivel de servicio (SLI) y el presupuesto de errores para el microservicio Transaction Validator de PayFlow MX.

El microservicio es **crítico** para las operaciones de la plataforma, procesando validaciones de transacciones electrónicas en tiempo real.

---

## 2. Service Level Agreement (SLA)

### 2.1 Definición

El SLA es el compromiso contractual con los clientes sobre el nivel de servicio que se proporcionará.

### 2.2 SLA Definido

| Métrica | Objetivo | Período | Consecuencia si se incumple |
|---------|----------|---------|----------------------------|
| **Disponibilidad** | 99.5% | Mensual | Crédito del 10% en facturación |
| **Latencia P95** | < 500ms | Mensual | Crédito del 5% en facturación |
| **Soporte Crítico** | Respuesta < 15min | Incidente | Escalamiento automático |
| **Tiempo de Recuperación** | < 1 hora | Incidente | Revisión de procesos |

### 2.3 Exclusiones del SLA

- Mantenimientos programados (notificados con 72h de anticipación)
- Fallas causadas por terceros (proveedores de nube, ISP)
- Ataques DDoS o eventos de fuerza mayor
- Uso inadecuado del servicio por parte del cliente

### 2.4 Cálculo de Disponibilidad SLA

```
Disponibilidad = (Tiempo Total - Downtime No Programado) / Tiempo Total × 100

SLA 99.5% = 3.65 horas de downtime permitido al mes
           = 43.8 minutos de downtime permitido al mes
```

---

## 3. Service Level Objectives (SLO)

### 3.1 Definición

Los SLO son objetivos internos más estrictos que el SLA, utilizados para guiar las operaciones y garantizar que siempre superamos el SLA.

### 3.2 SLOs Definidos

#### SLO 1: Disponibilidad
- **Objetivo:** 99.7% mensual
- **Medición:** Cada 1 minuto
- **Downtime permitido:** 2.16 horas/mes (129.6 minutos/mes)
- **Justificación:** Proporciona margen de 1.3 horas sobre el SLA

```
99.7% disponibilidad = 21.6 minutos de downtime al mes
                     = 43.2 segundos de downtime al día
```

#### SLO 2: Latencia P95
- **Objetivo:** < 250ms
- **Medición:** Ventana móvil de 5 minutos
- **Justificación:** Garantiza experiencia de usuario fluida
- **Límite de alerta:** 200ms (alerta temprana)

#### SLO 3: Latencia P99
- **Objetivo:** < 500ms
- **Medición:** Ventana móvil de 5 minutos
- **Justificación:** Proteger contra casos extremos
- **Límite de alerta:** 400ms (alerta temprana)

#### SLO 4: Tasa de Errores
- **Objetivo:** < 0.1% (1 error por cada 1,000 requests)
- **Medición:** Ventana móvil de 5 minutos
- **Justificación:** Calidad de servicio excepcional
- **Límite de alerta:** 0.05% (alerta temprana)

#### SLO 5: Throughput
- **Objetivo:** Soportar 500 requests/segundo
- **Pico máximo:** 1,000 requests/segundo
- **Medición:** Ventana de 1 minuto
- **Justificación:** Basado en tráfico histórico con margen del 200%

#### SLO 6: Tiempo de Recuperación (MTTR)
- **Objetivo:** < 30 minutos
- **Medición:** Por incidente
- **Justificación:** Minimizar impacto de incidentes

---

## 4. Service Level Indicators (SLI)

### 4.1 Definición

Los SLI son las métricas reales que medimos para determinar si estamos cumpliendo los SLO.

### 4.2 SLIs Implementados

#### SLI 1: Disponibilidad
```
Disponibilidad = (Requests Exitosos / Total Requests) × 100

Requests Exitosos = HTTP Status 200-299
Requests Fallidos = HTTP Status 500-599
Total Requests = Todos los requests recibidos

Implementación en Prometheus:
(sum(rate(transaction_validator_requests_total{status=~"2.."}[5m])) / 
 sum(rate(transaction_validator_requests_total[5m]))) * 100
```

**Umbrales:**
- Verde (OK): ≥ 99.7%
- Amarillo (Warning): 99.5% - 99.7%
- Rojo (Critical): < 99.5%

#### SLI 2: Latencia
```
Latencia P95 = Percentil 95 del tiempo de respuesta
Latencia P99 = Percentil 99 del tiempo de respuesta

Implementación en Prometheus:
histogram_quantile(0.95, 
  sum(rate(transaction_validator_request_duration_seconds_bucket[5m])) by (le))
```

**Umbrales P95:**
- Verde: < 200ms
- Amarillo: 200ms - 250ms
- Rojo: > 250ms

**Umbrales P99:**
- Verde: < 400ms
- Amarillo: 400ms - 500ms
- Rojo: > 500ms

#### SLI 3: Tasa de Errores
```
Error Rate = (Requests con Error / Total Requests) × 100

Requests con Error = HTTP Status 500-599

Implementación en Prometheus:
(sum(rate(transaction_validator_requests_total{status=~"5.."}[5m])) / 
 sum(rate(transaction_validator_requests_total[5m]))) * 100
```

**Umbrales:**
- Verde: < 0.05%
- Amarillo: 0.05% - 0.1%
- Rojo: > 0.1%

#### SLI 4: Validaciones Exitosas
```
Validation Success Rate = (Validaciones Aprobadas / Total Validaciones) × 100

No confundir con errores técnicos. Esta métrica mide validaciones
de negocio (transacciones aprobadas vs rechazadas).

Implementación en Prometheus:
(sum(rate(transaction_validations_total{status="approved"}[5m])) / 
 sum(rate(transaction_validations_total[5m]))) * 100
```

**Baseline esperado:** 70-80% de validaciones aprobadas

#### SLI 5: Saturación
```
Saturación = Transacciones Activas / Capacidad Máxima × 100

Implementación en Prometheus:
(transaction_validator_active_transactions / 1000) * 100
```

**Umbrales:**
- Verde: < 50%
- Amarillo: 50% - 80%
- Rojo: > 80%

---

## 5. Presupuesto de Errores

### 5.1 Concepto

El presupuesto de errores es la diferencia entre el objetivo de disponibilidad (100%) y el SLO. Representa cuánto downtime o cuántos errores podemos permitirnos antes de violar el SLO.

### 5.2 Cálculo del Presupuesto

**SLO de Disponibilidad: 99.7%**

```
Error Budget = 100% - 99.7% = 0.3%

Mensual (30 días):
= 30 días × 24 horas × 60 minutos × 0.003
= 43,200 minutos × 0.003
= 129.6 minutos
= 2.16 horas

Semanal:
= 10,080 minutos × 0.003
= 30.24 minutos

Diario:
= 1,440 minutos × 0.003
= 4.32 minutos
= 259.2 segundos
```

### 5.3 Distribución del Presupuesto

| Período | Tiempo Total | Error Budget (0.3%) | En Minutos |
|---------|--------------|---------------------|------------|
| Mensual | 43,200 min | 0.3% | 129.6 min |
| Semanal | 10,080 min | 0.3% | 30.24 min |
| Diario | 1,440 min | 0.3% | 4.32 min |
| Por Hora | 60 min | 0.3% | 10.8 seg |

### 5.4 Presupuesto de Errores por Requests

**Asumiendo 10,000 requests/hora promedio:**

```
Mensual: 
- Total requests: 7,200,000
- Errores permitidos: 21,600 (0.3%)

Diario:
- Total requests: 240,000
- Errores permitidos: 720 (0.3%)

Por cada 1,000 requests:
- Errores permitidos: 3
```

### 5.5 Uso del Presupuesto

El presupuesto de errores se puede "gastar" en:

1. **Despliegues y experimentos** (50% del presupuesto)
   - Nuevas features
   - Refactorizaciones
   - Experimentos A/B
   - Migraciones

2. **Incidentes y fallas** (30% del presupuesto)
   - Downtime no planificado
   - Degradación del servicio
   - Errores de producción

3. **Mantenimiento** (20% del presupuesto)
   - Updates de seguridad
   - Parches de infraestructura
   - Optimizaciones

### 5.6 Políticas de Presupuesto

#### Si el presupuesto > 50% disponible:
- ✅ Proceder con despliegues normales
- ✅ Experimentar con nuevas features
- ✅ Realizar refactorizaciones
- ✅ Optimizaciones de rendimiento

#### Si el presupuesto entre 25-50% disponible:
- ⚠️ Despliegues con aprobación de tech lead
- ⚠️ Incrementar monitoreo
- ⚠️ Pausar experimentos no críticos
- ✅ Solo hotfixes críticos

#### Si el presupuesto < 25% disponible:
- 🚫 CONGELAR despliegues no críticos
- 🚫 NO experimentar
- ✅ Solo hotfixes de seguridad críticos
- 🔍 Análisis de causa raíz obligatorio
- 📊 Plan de recuperación de presupuesto

#### Si el presupuesto AGOTADO:
- 🚨 **FREEZE TOTAL** de despliegues
- 🚨 Postmortem obligatorio
- 🚨 Plan de acción correctiva
- 🚨 Revisión de SLOs
- 📈 Solo se permiten rollbacks

### 5.7 Monitoreo del Presupuesto

**Dashboard en Grafana:**
- Gráfica de consumo de presupuesto en tiempo real
- Proyección del consumo mensual
- Alertas automáticas en umbrales

**Alerta Configurada:**
```yaml
- alert: ErrorBudgetLow
  expr: error_budget_remaining < 0.25
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Presupuesto de errores bajo (< 25%)"
```

### 5.8 Reporte de Presupuesto

**Revisión semanal:**
- Presupuesto consumido vs. disponible
- Principales causas de consumo
- Tendencias y proyecciones

**Ejemplo de reporte:**

```
Semana del 4-10 Diciembre 2025
================================
Presupuesto semanal: 30.24 minutos
Consumido: 8.5 minutos (28.1%)
Disponible: 21.74 minutos (71.9%)

Desglose de consumo:
- Despliegue v1.2.0: 3.2 min
- Incidente DB: 4.8 min
- Experimento A/B: 0.5 min

Estado: 🟢 SALUDABLE
Acción: Continuar operaciones normales
```

---

## 6. Métricas de Negocio

### 6.1 Transacciones Procesadas
- **Objetivo:** 50,000 validaciones/día
- **Pico:** 5,000 validaciones/hora

### 6.2 Valor Procesado
- **Objetivo:** $10M MXN/día en transacciones validadas
- **Tasa de aprobación esperada:** 75-80%

### 6.3 Impacto de Downtime

**Por cada minuto de downtime:**
- Transacciones no procesadas: ~35
- Valor en riesgo: ~$7,000 MXN
- Clientes afectados: ~30

**Costo del 1% de downtime mensual:**
- Tiempo: 432 minutos/mes
- Transacciones perdidas: ~15,000
- Valor: ~$3M MXN
- Penalización SLA: ~$100K MXN

---

## 7. Alertas y Notificaciones

### 7.1 Niveles de Severidad

| Severidad | Descripción | Tiempo de Respuesta | Notificación |
|-----------|-------------|---------------------|--------------|
| **Critical** | SLO violado, servicio degradado | 5 minutos | PagerDuty + SMS + Email |
| **Warning** | Acercándose a violar SLO | 15 minutos | Slack + Email |
| **Info** | Métricas anormales | 1 hora | Slack |

### 7.2 Alertas Configuradas

1. **Disponibilidad < 99.7%** → Critical
2. **Latencia P95 > 250ms** → Warning
3. **Latencia P99 > 500ms** → Critical
4. **Error rate > 0.1%** → Warning
5. **Error rate > 1%** → Critical
6. **Presupuesto < 25%** → Warning
7. **Presupuesto agotado** → Critical
8. **Servicio caído** → Critical

---

## 8. Revisión y Ajuste

### 8.1 Frecuencia de Revisión
- **Semanal:** Reporte de presupuesto
- **Mensual:** Análisis de SLO compliance
- **Trimestral:** Revisión de SLO/SLA

### 8.2 Criterios para Ajustar SLOs

Considerar ajuste si:
- SLO se cumple consistentemente con > 99.5% del tiempo
- SLO se viola > 20% del tiempo
- Cambios en requisitos de negocio
- Cambios en infraestructura

---

## 9. Referencias

- Documentación de Prometheus: `/monitoring/prometheus/`
- Dashboards de Grafana: `http://localhost:3000`

