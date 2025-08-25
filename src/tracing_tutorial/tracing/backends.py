"""
Tracing backends factory for OpenTelemetry SDK.

Uses OTLP (OpenTelemetry Protocol) as the standard export mechanism for all providers.
Provider selection via TRACING_BACKEND environment variable:
- langfuse: LangFuse OTLP endpoint (cloud or local)
- langsmith: LangSmith OTLP endpoint  
- phoenix: Arize Phoenix OTLP endpoint (local or cloud)
- otlp: Generic OTLP endpoint (Jaeger, custom collectors, etc.)
- console: Console output for debugging

All providers except console use OTLP protocol with provider-specific configuration.
"""
from __future__ import annotations

import base64
import os
from typing import Optional, Dict

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

# Load environment variables
load_dotenv()

DEFAULT_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "tracing-tutorial")


def _ensure_provider(service_name: str) -> TracerProvider:
    """Initialize and set the global TracerProvider with resource attributes."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("OTEL_SERVICE_VERSION", "0.1.0"),
        "deployment.environment": os.getenv("OTEL_ENVIRONMENT", "dev"),
    })
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    return provider


def _get_otlp_exporter(endpoint: str, headers: Optional[Dict[str, str]] = None):
    """Create OTLP exporter with appropriate protocol based on endpoint."""
    # Determine if we should use HTTP or gRPC based on endpoint
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        # Use HTTP exporter for HTTP(S) endpoints
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        
        # Ensure endpoint has /v1/traces for HTTP protocol
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"
        
        return OTLPSpanExporter(endpoint=endpoint, headers=headers)
    else:
        # Use gRPC exporter for non-HTTP endpoints
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        
        return OTLPSpanExporter(endpoint=endpoint, headers=headers)


def _setup_langfuse_otlp(provider: TracerProvider) -> None:
    """Configure OTLP export to LangFuse."""
    # LangFuse endpoints
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    
    # Determine endpoint based on host
    if "cloud.langfuse.com" in host:
        # Cloud endpoints
        if "us.cloud" in host:
            endpoint = "https://us.cloud.langfuse.com/api/public/otel"
        else:
            endpoint = "https://cloud.langfuse.com/api/public/otel"
    else:
        # Local or custom deployment
        endpoint = f"{host}/api/public/otel"
    
    # LangFuse requires Basic Auth with public and secret keys
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    headers = {}
    if public_key and secret_key:
        # Create Basic Auth header
        credentials = f"{public_key}:{secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    
    exporter = _get_otlp_exporter(endpoint, headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))


def _setup_langsmith_otlp(provider: TracerProvider) -> None:
    """Configure OTLP export to LangSmith."""
    # LangSmith endpoints
    api_url = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    
    # Determine OTLP endpoint
    if "eu.api" in api_url:
        endpoint = "https://eu.api.smith.langchain.com/otel"
    else:
        endpoint = f"{api_url}/otel" if not api_url.endswith("/otel") else api_url
    
    # LangSmith requires API key in headers
    api_key = os.getenv("LANGSMITH_API_KEY")
    headers = {}
    
    if api_key:
        headers["x-api-key"] = api_key
    
    # Optional project name
    project = os.getenv("LANGSMITH_PROJECT")
    if project:
        headers["Langsmith-Project"] = project
    
    exporter = _get_otlp_exporter(endpoint, headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))


def _setup_phoenix_otlp(provider: TracerProvider) -> None:
    """Configure OTLP export to Arize Phoenix."""
    # Phoenix can run locally or in cloud
    endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    
    # Phoenix Cloud requires API key
    api_key = os.getenv("PHOENIX_API_KEY")
    headers = {}
    
    if api_key:
        headers["authorization"] = api_key
    
    exporter = _get_otlp_exporter(endpoint, headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))


def _setup_generic_otlp(provider: TracerProvider) -> None:
    """Configure generic OTLP export for custom collectors."""
    # Support both environment variable formats
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or \
               os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    
    # Support custom headers for authentication
    headers_str = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers = {}
    
    if headers_str:
        # Parse headers in format: "key1=value1,key2=value2"
        for header in headers_str.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
    
    exporter = _get_otlp_exporter(endpoint, headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))


def _setup_console(provider: TracerProvider) -> None:
    """Configure console export for debugging."""
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))


def configure_tracing(service_name: Optional[str] = None) -> trace.Tracer:
    """
    Configure OpenTelemetry tracing with the specified backend.
    
    All backends except 'console' use OTLP protocol with provider-specific configuration.
    
    Args:
        service_name: Optional service name override
        
    Returns:
        Configured OpenTelemetry tracer
    """
    backend = os.getenv("TRACING_BACKEND", "console").lower()
    service = service_name or DEFAULT_SERVICE_NAME
    
    provider = _ensure_provider(service)
    
    # Configure the appropriate backend
    if backend == "langfuse":
        _setup_langfuse_otlp(provider)
    elif backend == "langsmith":
        _setup_langsmith_otlp(provider)
    elif backend == "phoenix":
        _setup_phoenix_otlp(provider)
    elif backend == "console":
        _setup_console(provider)
    else:
        # Default to generic OTLP
        _setup_generic_otlp(provider)
    
    # Instrument LangChain for automatic tracing
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        # Pass skip_dep_check=True to avoid dependency check issues
        LangChainInstrumentor().instrument(
            tracer_provider=provider,
            skip_dep_check=True
        )
    except ImportError as e:
        print(f"Warning: LangChain instrumentation not available: {e}")
    except Exception as e:
        print(f"Warning: Failed to instrument LangChain: {e}")
    
    return trace.get_tracer(service)