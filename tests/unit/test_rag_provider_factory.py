from src.adapters.rag import EmbeddedRagAdapter, ExternalRagAdapter
from src.runtime.rag_provider import build_rag_ports


class ExternalConfig:
    RAG_PROVIDER = "external"
    AI_RAG_SERVICE_URL = "http://rag-service"
    AI_RAG_SERVICE_TIMEOUT_SECONDS = 4.0


class EmbeddedConfig:
    RAG_PROVIDER = "embedded"
    AI_RAG_SERVICE_URL = ""
    AI_RAG_SERVICE_TIMEOUT_SECONDS = 4.0


class DefaultConfig:
    AI_RAG_SERVICE_URL = ""
    AI_RAG_SERVICE_TIMEOUT_SECONDS = 4.0


def test_build_rag_ports_returns_external_adapter_when_configured():
    ports = build_rag_ports(config=ExternalConfig, embedded_rag_service=None)

    assert isinstance(ports.query_port, ExternalRagAdapter)
    assert ports.ingestion_port is ports.query_port
    assert ports.provider == "external"


def test_build_rag_ports_defaults_to_external_provider_when_unset():
    ports = build_rag_ports(config=DefaultConfig, embedded_rag_service=object())

    assert ports.query_port is None
    assert ports.ingestion_port is None
    assert ports.provider == "external"


def test_build_rag_ports_wraps_embedded_service_when_configured():
    service = object()

    ports = build_rag_ports(config=EmbeddedConfig, embedded_rag_service=service)

    assert isinstance(ports.query_port, EmbeddedRagAdapter)
    assert ports.ingestion_port is ports.query_port
    assert ports.provider == "embedded"
