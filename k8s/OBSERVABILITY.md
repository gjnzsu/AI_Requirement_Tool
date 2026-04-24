# Observability Stack

The observability stack (Prometheus, Grafana, dashboards) has been moved to the centralized repository:

**Repository:** https://github.com/gjnzsu/ai-sre-observability

## Quick Links

- **Prometheus:** http://136.113.33.154:9090
- **Grafana:** http://136.114.77.0 (admin / newpassword123)
- **Deployment Guide:** See `k8s/README.md` in ai-sre-observability repo

## Dashboards

1. **Service Overview** - Health, HTTP metrics, error rates
2. **LLM Cost & Usage** - Cost tracking by provider/model, token usage
3. **Request Tracing** - Latency heatmaps, trace search, success rates

## Instrumentation

This service is monitored by the AI SRE Observability platform. Metrics are exposed at `/metrics` endpoint and scraped by Prometheus every 15 seconds.

For SDK usage and instrumentation details, see the ai-sre-observability repository.
