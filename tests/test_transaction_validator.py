"""
Tests unitarios para Transaction Validator
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Tests para endpoints de salud"""
    
    def test_root_endpoint(self):
        """Test del endpoint raíz"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "PayFlow MX - Transaction Validator"
        assert "status" in data
        assert data["status"] == "operational"
    
    def test_health_check(self):
        """Test del health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert data["checks"]["api"] == "ok"
    
    def test_readiness_check(self):
        """Test del readiness check"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert "dependencies" in data


class TestTransactionValidation:
    """Tests para validación de transacciones"""
    
    def test_validate_valid_transaction(self):
        """Test de validación de transacción válida"""
        transaction = {
            "transaction_id": "TX-001",
            "amount": 1000.50,
            "currency": "MXN",
            "sender_account": "1234567890",
            "receiver_account": "0987654321",
            "timestamp": "2025-12-10T10:00:00Z",
            "description": "Pago de prueba"
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 200
        
        data = response.json()
        assert data["transaction_id"] == "TX-001"
        assert "is_valid" in data
        assert "validation_score" in data
        assert "risk_level" in data
        assert "checks_passed" in data
    
    def test_validate_high_amount_transaction(self):
        """Test de validación con monto alto"""
        transaction = {
            "transaction_id": "TX-002",
            "amount": 750000,
            "currency": "MXN",
            "sender_account": "1234567890",
            "receiver_account": "0987654321",
            "timestamp": "2025-12-10T10:00:00Z"
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 200
        
        data = response.json()
        assert "warnings" in data
        # Debe tener advertencia de alto valor
        assert len(data["warnings"]) > 0
    
    def test_validate_invalid_currency(self):
        """Test de validación con moneda inválida"""
        transaction = {
            "transaction_id": "TX-003",
            "amount": 1000,
            "currency": "JPY",  # Moneda no permitida
            "sender_account": "1234567890",
            "receiver_account": "0987654321",
            "timestamp": "2025-12-10T10:00:00Z"
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 422  # Validation error
    
    def test_validate_excessive_amount(self):
        """Test de validación con monto excesivo"""
        transaction = {
            "transaction_id": "TX-004",
            "amount": 2000000,  # Excede límite de 1M
            "currency": "MXN",
            "sender_account": "1234567890",
            "receiver_account": "0987654321",
            "timestamp": "2025-12-10T10:00:00Z"
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 422  # Validation error
    
    def test_validate_same_accounts(self):
        """Test de validación con cuentas iguales"""
        transaction = {
            "transaction_id": "TX-005",
            "amount": 1000,
            "currency": "MXN",
            "sender_account": "1234567890",
            "receiver_account": "1234567890",  # Misma cuenta
            "timestamp": "2025-12-10T10:00:00Z"
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 200
        
        data = response.json()
        # El check de cuentas diferentes debe fallar
        assert data["checks_passed"]["different_accounts"] is False
    
    def test_validate_missing_fields(self):
        """Test de validación con campos faltantes"""
        transaction = {
            "transaction_id": "TX-006",
            "amount": 1000
            # Faltan campos requeridos
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 422  # Validation error
    
    def test_validate_negative_amount(self):
        """Test de validación con monto negativo"""
        transaction = {
            "transaction_id": "TX-007",
            "amount": -1000,
            "currency": "MXN",
            "sender_account": "1234567890",
            "receiver_account": "0987654321",
            "timestamp": "2025-12-10T10:00:00Z"
        }
        
        response = client.post("/api/v1/validate", json=transaction)
        assert response.status_code == 422  # Validation error


class TestMetrics:
    """Tests para endpoint de métricas"""
    
    def test_metrics_endpoint(self):
        """Test del endpoint de métricas"""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        # Verificar que contiene métricas de Prometheus
        content = response.text
        assert "transaction_validator_requests_total" in content
        assert "transaction_validator_request_duration_seconds" in content
        assert "transaction_validations_total" in content


class TestStats:
    """Tests para endpoint de estadísticas"""
    
    def test_stats_endpoint(self):
        """Test del endpoint de stats"""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "transaction-validator"
        assert "version" in data


class TestErrorHandling:
    """Tests para manejo de errores"""
    
    def test_404_not_found(self):
        """Test de endpoint no encontrado"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_json(self):
        """Test de JSON inválido"""
        response = client.post(
            "/api/v1/validate",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestConcurrentRequests:
    """Tests de concurrencia"""
    
    async def test_multiple_validations(self):
        """Test de múltiples validaciones concurrentes"""
        transactions = [
            {
                "transaction_id": f"TX-{i:03d}",
                "amount": 1000 + i,
                "currency": "MXN",
                "sender_account": "1234567890",
                "receiver_account": "0987654321"
            }
            for i in range(10)
        ]
        
        responses = []
        for transaction in transactions:
            response = client.post("/api/v1/validate", json=transaction)
            responses.append(response)
        
        # Todas deben completarse exitosamente
        for response in responses:
            assert response.status_code == 200
