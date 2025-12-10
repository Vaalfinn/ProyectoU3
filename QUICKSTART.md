# Manual de Inicio Rápido
## Transaction Validator - PayFlow MX

---

## 🚀 Inicio Rápido (5 minutos)

### 1. Pre-requisitos

Asegúrate de tener instalado:

```powershell
# Verificar Docker
docker --version
# Debe mostrar: Docker version 20.10.x o superior

# Verificar Docker Compose
docker-compose --version
# Debe mostrar: docker-compose version 2.x o superior

# Verificar Git
git --version
```

### 2. Clonar y Configurar

```powershell
# Clonar repositorio
git clone https://github.com/AlanGaBer11/ProyectoUnidad3
cd payflow-transaction-validator

# Crear archivo de variables de entorno (opcional)
Copy-Item .env.example .env
# Editar .env si es necesario
```

### 3. Iniciar Todos los Servicios

```powershell
# Construir e iniciar todos los servicios
docker-compose up -d

# Ver logs (opcional)
docker-compose logs -f
```

**Espera ~2 minutos** para que todos los servicios inicien.

### 4. Verificar que Todo Funciona

```powershell
# Verificar servicios activos
docker-compose ps

# Debe mostrar todos en estado "Up"
```

**Acceder a las interfaces:**

- 🌐 **API:** http://localhost:8000
- 📊 **Grafana:** http://localhost:3000 (admin/admin)
- 📈 **Prometheus:** http://localhost:9090
- 🔍 **Jaeger:** http://localhost:16686
- 📋 **Kibana:** http://localhost:5601
- 📖 **API Docs:** http://localhost:8000/docs
- 🔀 **Load Balancer:** http://localhost:9080

### 5. Probar la API

```powershell
# Test rápido
Invoke-WebRequest -Uri http://localhost:8000/health

# Validar una transacción
$body = @{
    transaction_id = "TEST-001"
    amount = 1000
    currency = "MXN"
    sender_account = "1234567890"
    receiver_account = "0987654321"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/api/v1/validate `
    -Method Post -Body $body -ContentType "application/json"
```

---

## 📚 Siguientes Pasos

1. **Explorar Dashboards:** Abre Grafana y explora los dashboards
2. **Ver Logs:** Revisa Kibana para ver logs estructurados
3. **Probar Despliegue:** Ejecuta `.\scripts\deploy-blue-green.ps1`
4. **Ejecutar Tests:** `docker-compose exec transaction-validator-blue pytest tests/`
5. **Pruebas de Carga:** `k6 run k6/load-test.js` (requiere k6 instalado)

---

## 🛑 Detener Todo

```powershell
# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (¡cuidado, borra datos!)
docker-compose down -v
```

---

## 🔧 Troubleshooting Rápido

### Puertos en uso

```powershell
# Ver qué está usando el puerto 8000
netstat -ano | findstr :8000

# Matar proceso
Stop-Process -Id <PID> -Force
```

### Servicios no inician

```powershell
# Ver logs de error
docker-compose logs <nombre-servicio>

# Reiniciar servicio específico
docker-compose restart <nombre-servicio>
```

### Limpiar y reiniciar

```powershell
# Detener todo
docker-compose down -v

# Limpiar imágenes
docker system prune -af

# Reconstruir
docker-compose build --no-cache
docker-compose up -d
```

