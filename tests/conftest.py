"""
Configuración de pytest
"""
import pytest
import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def test_app():
    """Fixture para la aplicación de prueba"""
    from src.main import app
    return app


@pytest.fixture
def sample_transaction():
    """Fixture para transacción de ejemplo"""
    return {
        "transaction_id": "TEST-001",
        "amount": 1000.00,
        "currency": "MXN",
        "sender_account": "1234567890",
        "receiver_account": "0987654321",
        "description": "Test transaction"
    }
