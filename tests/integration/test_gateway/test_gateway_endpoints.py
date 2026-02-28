"""
Integration tests for gateway endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.gateway.gateway_service import create_gateway_app


@pytest.fixture
def gateway_client():
    """Create test client for gateway."""
    app = create_gateway_app()
    return TestClient(app)


class TestGatewayEndpoints:
    """Tests for gateway API endpoints."""
    
    def test_health_endpoint(self, gateway_client):
        """Test health check endpoint."""
        response = gateway_client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "providers" in data
        assert "features" in data
    
    def test_providers_endpoint(self, gateway_client):
        """Test providers list endpoint."""
        response = gateway_client.get("/v1/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)
    
    def test_metrics_endpoint(self, gateway_client):
        """Test metrics endpoint."""
        response = gateway_client.get("/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "total_errors" in data
        assert "cache_hit_rate" in data
        assert "provider_metrics" in data
    
    def test_chat_completion_endpoint_validation(self, gateway_client):
        """Test chat completion endpoint validation."""
        # Missing messages should fail
        response = gateway_client.post("/v1/chat/completions", json={})
        assert response.status_code == 422  # Validation error
        
        # Invalid messages should fail
        response = gateway_client.post(
            "/v1/chat/completions",
            json={"messages": []}
        )
        assert response.status_code == 422
    
    def test_chat_completion_endpoint_structure(self, gateway_client):
        """Test chat completion endpoint response structure."""
        # Note: This test may fail if no providers are configured
        # It's mainly testing the endpoint structure, not actual LLM calls
        response = gateway_client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        )
        
        # Should either succeed (200) or fail with proper error (503 if no providers)
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert "content" in data["choices"][0]["message"]

