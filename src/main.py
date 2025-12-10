"""
PayFlow MX - Transaction Validator Microservice
Microservicio crítico para validación de transacciones electrónicas
"""
import logging
import time
import random
from typing import Dict, Optional
from datetime import datetime
import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s]'
)
logger = logging.getLogger(__name__)

# Configuración de OpenTelemetry para trazas
resource = Resource(attributes={
    "service.name": "transaction-validator",
    "service.version": os.getenv("APP_VERSION", "1.0.0"),
    "deployment.environment": os.getenv("ENVIRONMENT", "production")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configurar exportador Jaeger
jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_HOST", "jaeger"),
    agent_port=int(os.getenv("JAEGER_PORT", "6831")),
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Métricas de Prometheus
REQUEST_COUNT = Counter(
    'transaction_validator_requests_total',
    'Total de requests recibidos',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'transaction_validator_request_duration_seconds',
    'Latencia de requests en segundos',
    ['method', 'endpoint']
)

TRANSACTION_VALIDATION = Counter(
    'transaction_validations_total',
    'Total de validaciones de transacciones',
    ['status', 'validation_type']
)

ACTIVE_TRANSACTIONS = Gauge(
    'transaction_validator_active_transactions',
    'Número de transacciones activas siendo procesadas'
)

ERROR_COUNT = Counter(
    'transaction_validator_errors_total',
    'Total de errores por tipo',
    ['error_type']
)

# Crear aplicación FastAPI
app = FastAPI(
    title="PayFlow MX - Transaction Validator",
    description="Microservicio de validación de transacciones electrónicas",
    version=os.getenv("APP_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc"
)

# Instrumentar FastAPI con OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para métricas y logging
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Incrementar transacciones activas
    ACTIVE_TRANSACTIONS.inc()
    
    try:
        response = await call_next(request)
        
        # Calcular latencia
        duration = time.time() - start_time
        
        # Registrar métricas
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Log estructurado
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
                "otelTraceID": trace.format_trace_id(trace.get_current_span().get_span_context().trace_id),
                "otelSpanID": trace.format_span_id(trace.get_current_span().get_span_context().span_id)
            }
        )
        
        return response
    
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Error procesando request: {str(e)}", exc_info=True)
        raise
    
    finally:
        ACTIVE_TRANSACTIONS.dec()


# Modelos de datos
class Transaction(BaseModel):
    """Modelo de transacción para validación"""
    transaction_id: str = Field(..., description="ID único de la transacción")
    amount: float = Field(..., gt=0, description="Monto de la transacción")
    currency: str = Field(default="MXN", description="Moneda de la transacción")
    sender_account: str = Field(..., description="Cuenta origen")
    receiver_account: str = Field(..., description="Cuenta destino")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('currency')
    def validate_currency(cls, v):
        allowed_currencies = ['MXN', 'USD', 'EUR']
        if v not in allowed_currencies:
            raise ValueError(f'Moneda debe ser una de: {allowed_currencies}')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v > 1000000:  # Límite de $1M
            raise ValueError('Monto excede el límite permitido')
        return v


class ValidationResult(BaseModel):
    """Resultado de validación de transacción"""
    transaction_id: str
    is_valid: bool
    validation_score: float
    risk_level: str
    checks_passed: Dict[str, bool]
    warnings: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Endpoints
@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": "PayFlow MX - Transaction Validator",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "operational",
        "environment": os.getenv("ENVIRONMENT", "production")
    }


@app.get("/health")
async def health_check():
    """Health check endpoint para validación de despliegue"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "checks": {
            "api": "ok",
            "database": "ok",  # Simulado
            "cache": "ok"      # Simulado
        }
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check para Kubernetes/Docker"""
    # Simular chequeo de dependencias
    return {
        "ready": True,
        "dependencies": {
            "database": "connected",
            "cache": "connected",
            "message_queue": "connected"
        }
    }


@app.get("/metrics")
async def metrics():
    """Endpoint de métricas de Prometheus"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/api/v1/validate", response_model=ValidationResult)
async def validate_transaction(transaction: Transaction):
    """
    Valida una transacción electrónica
    
    Realiza múltiples validaciones:
    - Límites de monto
    - Validación de cuentas
    - Detección de fraude
    - Compliance regulatorio
    """
    with tracer.start_as_current_span("validate_transaction") as span:
        span.set_attribute("transaction.id", transaction.transaction_id)
        span.set_attribute("transaction.amount", transaction.amount)
        span.set_attribute("transaction.currency", transaction.currency)
        
        try:
            # Simular proceso de validación con latencia variable
            # En horarios pico (simulado con probabilidad), aumentar latencia
            is_peak_hour = random.random() < 0.3
            base_latency = random.uniform(0.05, 0.15)
            
            if is_peak_hour:
                latency = base_latency + random.uniform(0.1, 0.3)
                span.set_attribute("peak_hour", True)
            else:
                latency = base_latency
                span.set_attribute("peak_hour", False)
            
            time.sleep(latency)
            
            # Realizar validaciones
            checks = {}
            warnings = []
            
            # 1. Validación de límites
            with tracer.start_as_current_span("check_amount_limits"):
                checks['amount_within_limits'] = transaction.amount <= 1000000
                if transaction.amount > 500000:
                    warnings.append("Transacción de alto valor - requiere aprobación adicional")
            
            # 2. Validación de cuentas
            with tracer.start_as_current_span("check_accounts"):
                checks['valid_sender'] = len(transaction.sender_account) >= 10
                checks['valid_receiver'] = len(transaction.receiver_account) >= 10
                checks['different_accounts'] = transaction.sender_account != transaction.receiver_account
            
            # 3. Detección de fraude (simulada)
            with tracer.start_as_current_span("fraud_detection"):
                # Simular análisis de patrones
                time.sleep(random.uniform(0.01, 0.05))
                fraud_score = random.uniform(0, 1)
                checks['fraud_check'] = fraud_score < 0.15
                
                if fraud_score >= 0.1:
                    warnings.append("Patrones inusuales detectados")
            
            # 4. Compliance
            with tracer.start_as_current_span("compliance_check"):
                checks['compliance'] = transaction.currency in ['MXN', 'USD', 'EUR']
            
            # Calcular resultado
            passed_checks = sum(checks.values())
            total_checks = len(checks)
            validation_score = (passed_checks / total_checks) * 100
            
            is_valid = passed_checks == total_checks
            
            # Determinar nivel de riesgo
            if validation_score >= 90:
                risk_level = "low"
            elif validation_score >= 70:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            # Simular errores ocasionales (0.8% según el escenario)
            if random.random() < 0.008:
                ERROR_COUNT.labels(error_type="ValidationError").inc()
                TRANSACTION_VALIDATION.labels(
                    status="error",
                    validation_type="automatic"
                ).inc()
                raise HTTPException(
                    status_code=500,
                    detail="Error interno en el sistema de validación"
                )
            
            # Registrar métrica de validación
            TRANSACTION_VALIDATION.labels(
                status="approved" if is_valid else "rejected",
                validation_type="automatic"
            ).inc()
            
            result = ValidationResult(
                transaction_id=transaction.transaction_id,
                is_valid=is_valid,
                validation_score=validation_score,
                risk_level=risk_level,
                checks_passed=checks,
                warnings=warnings
            )
            
            logger.info(
                f"Transacción {transaction.transaction_id} validada - Score: {validation_score:.2f}",
                extra={
                    "transaction_id": transaction.transaction_id,
                    "validation_score": validation_score,
                    "risk_level": risk_level,
                    "is_valid": is_valid,
                    "otelTraceID": trace.format_trace_id(span.get_span_context().trace_id),
                    "otelSpanID": trace.format_span_id(span.get_span_context().span_id)
                }
            )
            
            return result
        
        except HTTPException:
            raise
        except Exception as e:
            ERROR_COUNT.labels(error_type=type(e).__name__).inc()
            logger.error(
                f"Error validando transacción {transaction.transaction_id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.get("/api/v1/stats")
async def get_stats():
    """Obtiene estadísticas del servicio"""
    return {
        "service": "transaction-validator",
        "uptime": "operational",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "metrics_endpoint": "/metrics",
        "health_endpoint": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
