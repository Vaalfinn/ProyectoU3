#!/bin/bash

# Script de Despliegue Blue/Green para Transaction Validator
# Este script implementa una estrategia de despliegue sin downtime

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
CURRENT_ENV="blue"
NEW_ENV="green"
HEALTH_CHECK_URL_BLUE="http://localhost:8000/health"
HEALTH_CHECK_URL_GREEN="http://localhost:8001/health"
MAX_HEALTH_RETRIES=30
HEALTH_CHECK_INTERVAL=10
MONITORING_PERIOD=300  # 5 minutos de monitoreo

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   PayFlow MX - Blue/Green Deployment${NC}"
echo -e "${BLUE}   Transaction Validator Microservice${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Función para imprimir con color
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para verificar health check
check_health() {
    local url=$1
    local retries=$2
    local interval=$3
    
    print_info "Verificando health check: $url"
    
    for ((i=1; i<=retries; i++)); do
        if curl -sf "$url" > /dev/null; then
            print_success "Health check exitoso (intento $i/$retries)"
            return 0
        else
            print_warning "Health check falló (intento $i/$retries)"
            if [ $i -lt $retries ]; then
                sleep $interval
            fi
        fi
    done
    
    print_error "Health check falló después de $retries intentos"
    return 1
}

# Función para obtener métricas
get_metrics() {
    local url=$1
    curl -s "$url" || echo "Error obteniendo métricas"
}

# Función de rollback
rollback() {
    print_error "Iniciando rollback a $CURRENT_ENV..."
    
    # Detener ambiente Green
    docker-compose stop transaction-validator-green
    
    # Asegurar que Blue está corriendo
    docker-compose up -d transaction-validator-blue
    
    # Actualizar Nginx
    docker-compose exec nginx sed -i 's/transaction_validator_green/transaction_validator_blue/g' /etc/nginx/nginx.conf
    docker-compose exec nginx nginx -s reload
    
    print_success "Rollback completado. Tráfico redirigido a $CURRENT_ENV"
    exit 1
}

# PASO 1: Pre-deployment checks
print_info "Paso 1/7: Verificaciones pre-despliegue"
echo ""

# Verificar que Blue está corriendo
print_info "Verificando ambiente BLUE (actual)..."
if ! check_health "$HEALTH_CHECK_URL_BLUE" 3 5; then
    print_error "El ambiente BLUE actual no está saludable. Abortando despliegue."
    exit 1
fi
print_success "Ambiente BLUE está saludable"
echo ""

# PASO 2: Deploy Green
print_info "Paso 2/7: Desplegando ambiente GREEN"
echo ""

print_info "Construyendo nueva imagen..."
docker-compose build transaction-validator-green

print_info "Iniciando contenedor GREEN..."
docker-compose --profile green-deployment up -d transaction-validator-green

sleep 10
print_success "Contenedor GREEN iniciado"
echo ""

# PASO 3: Health Check Green
print_info "Paso 3/7: Verificando salud del ambiente GREEN"
echo ""

if ! check_health "$HEALTH_CHECK_URL_GREEN" $MAX_HEALTH_RETRIES $HEALTH_CHECK_INTERVAL; then
    print_error "El ambiente GREEN no pasó el health check"
    rollback
fi
print_success "Ambiente GREEN está saludable"
echo ""

# PASO 4: Smoke Tests
print_info "Paso 4/7: Ejecutando smoke tests en GREEN"
echo ""

# Test básico de API
print_info "Test 1: Endpoint raíz"
if curl -sf http://localhost:8001/ > /dev/null; then
    print_success "✓ Endpoint raíz responde correctamente"
else
    print_error "✗ Endpoint raíz falló"
    rollback
fi

print_info "Test 2: Endpoint de validación"
RESPONSE=$(curl -sf -X POST http://localhost:8001/api/v1/validate \
    -H "Content-Type: application/json" \
    -d '{
        "transaction_id": "test-123",
        "amount": 1000,
        "currency": "MXN",
        "sender_account": "1234567890",
        "receiver_account": "0987654321"
    }')

if [ $? -eq 0 ]; then
    print_success "✓ Endpoint de validación responde correctamente"
else
    print_error "✗ Endpoint de validación falló"
    rollback
fi

print_info "Test 3: Métricas"
if curl -sf http://localhost:8001/metrics > /dev/null; then
    print_success "✓ Endpoint de métricas responde correctamente"
else
    print_error "✗ Endpoint de métricas falló"
    rollback
fi

print_success "Todos los smoke tests pasaron"
echo ""

# PASO 5: Switch Traffic
print_info "Paso 5/7: Cambiando tráfico de BLUE a GREEN"
echo ""

print_warning "Preparando para cambiar tráfico..."
sleep 3

# Actualizar configuración de Nginx
print_info "Actualizando configuración de Nginx..."
docker-compose exec -T nginx sh -c "sed -i 's/transaction_validator_blue/transaction_validator_green/g' /etc/nginx/nginx.conf"
docker-compose exec -T nginx nginx -s reload

print_success "Tráfico cambiado a GREEN"
echo ""

# PASO 6: Monitoring Period
print_info "Paso 6/7: Período de monitoreo ($MONITORING_PERIOD segundos)"
echo ""

print_info "Monitoreando GREEN por $((MONITORING_PERIOD/60)) minutos..."
MONITORING_INTERVAL=30
CHECKS=$((MONITORING_PERIOD/MONITORING_INTERVAL))

for ((i=1; i<=CHECKS; i++)); do
    print_info "Check $i/$CHECKS"
    
    # Verificar health
    if ! curl -sf http://localhost:80/health > /dev/null; then
        print_error "Health check falló durante monitoreo"
        rollback
    fi
    
    # Verificar métricas
    METRICS=$(get_metrics "http://localhost:80/metrics")
    ERROR_COUNT=$(echo "$METRICS" | grep "transaction_validator_errors_total" | awk '{print $2}' | head -1)
    
    print_info "Errores detectados: ${ERROR_COUNT:-0}"
    
    # Verificar que no haya demasiados errores
    if [ ! -z "$ERROR_COUNT" ] && [ "$ERROR_COUNT" -gt 100 ]; then
        print_error "Demasiados errores detectados en GREEN"
        rollback
    fi
    
    sleep $MONITORING_INTERVAL
done

print_success "Período de monitoreo completado exitosamente"
echo ""

# PASO 7: Finalization
print_info "Paso 7/7: Finalización del despliegue"
echo ""

print_info "Deteniendo ambiente BLUE (antiguo)..."
docker-compose stop transaction-validator-blue

print_success "Ambiente BLUE detenido"
print_success "GREEN es ahora el ambiente de producción"
echo ""

# Resumen
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   DESPLIEGUE COMPLETADO EXITOSAMENTE${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "Ambiente anterior: ${YELLOW}BLUE${NC}"
echo -e "Ambiente nuevo:    ${GREEN}GREEN${NC}"
echo -e "URL producción:    ${BLUE}http://localhost${NC}"
echo -e "URL Green directa: ${BLUE}http://localhost:8001${NC}"
echo ""
echo -e "Próximos pasos:"
echo -e "  1. Monitorear dashboards en Grafana: http://localhost:3000"
echo -e "  2. Verificar logs en Kibana: http://localhost:5601"
echo -e "  3. Revisar trazas en Jaeger: http://localhost:16686"
echo ""
echo -e "${YELLOW}Nota:${NC} Para el próximo despliegue, BLUE será el nuevo ambiente"
echo -e "      y GREEN el actual. Intercambiar las variables en este script."
echo ""

# Guardar estado del despliegue
echo "$(date +"%Y-%m-%d %H:%M:%S") - Deployed to GREEN successfully" >> deployment-history.log

exit 0
