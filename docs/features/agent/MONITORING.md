# LLM Monitoring and Cost Tracking

The chatbot includes lightweight monitoring for LLM performance and cost tracking.

## Features

- **Performance Monitoring**: Track latency for each LLM call
- **Token Usage**: Monitor prompt, completion, and total tokens
- **Cost Estimation**: Rough cost estimates based on token usage
- **Error Tracking**: Count and log LLM call failures
- **Statistics**: Aggregate statistics across all calls

## How It Works

The monitoring is automatically enabled when you use the LangGraph agent. A callback handler (`LLMMonitoringCallback`) is attached to all LLM instances and tracks:

- Call start/end times
- Token usage from response metadata
- Errors and exceptions
- Aggregated statistics

## Usage

### Automatic Monitoring

Monitoring is enabled by default. No configuration needed!

```python
from src.agent import ChatbotAgent

# Create agent - monitoring is automatically enabled
agent = ChatbotAgent(
    provider_name="openai",
    enable_tools=True
)

# Use the agent normally
response = agent.invoke("Hello, how are you?")
```

### Accessing Statistics

Get monitoring statistics programmatically:

```python
# Get current statistics
stats = agent.get_monitoring_stats()

print(f"Total calls: {stats['total_calls']}")
print(f"Total tokens: {stats['total_tokens']:,}")
print(f"Average duration: {stats['average_duration_seconds']:.2f}s")
print(f"Estimated cost: ${stats['estimated_cost_usd']:.4f}")
```

### Logging Summary

Log a formatted summary of all monitoring data:

```python
# Log summary to console
agent.log_monitoring_summary()
```

Example output:
```
======================================================================
LLM Monitoring Summary
======================================================================
Total Calls: 15
Successful: 14 | Errors: 1
Success Rate: 93.3%
Total Tokens: 12,450
  - Prompt: 8,200
  - Completion: 4,250
Total Duration: 45.32s
Average Duration: 3.02s
Estimated Cost: $0.0234
======================================================================
```

## What Gets Logged

### Per-Call Logging

Each LLM call logs:
- **INFO level**: Completion time, token usage
- **DEBUG level**: Start time, prompt details, response length
- **ERROR level**: Failures with full exception details

Example log entry:
```
INFO: LLM call #5 completed: 2.34s | Tokens: 450 (prompt: 300, completion: 150)
```

### Statistics Available

The `get_statistics()` method returns:

```python
{
    'total_calls': 15,
    'successful_calls': 14,
    'error_count': 1,
    'success_rate': '93.3%',
    'total_tokens': 12450,
    'total_prompt_tokens': 8200,
    'total_completion_tokens': 4250,
    'total_duration_seconds': 45.32,
    'average_duration_seconds': 3.02,
    'estimated_cost_usd': 0.0234
}
```

## Cost Estimation

The cost estimation uses approximate pricing (as of 2024):
- **GPT-3.5-turbo baseline**: $0.0015/1K prompt tokens, $0.002/1K completion tokens
- **Note**: Actual costs vary by model. Adjust pricing in `callbacks.py` if needed.

To customize pricing for your model:

```python
# In src/agent/callbacks.py, modify _estimate_cost() method
def _estimate_cost(self) -> float:
    # Your custom pricing logic
    prompt_cost_per_1k = 0.03  # e.g., GPT-4 pricing
    completion_cost_per_1k = 0.06
    # ...
```

## Integration with Flask App

You can expose monitoring stats via API:

```python
# In app.py
@app.route('/api/monitoring/stats')
@token_required
def get_monitoring_stats():
    if app.chatbot and app.chatbot.agent:
        stats = app.chatbot.agent.get_monitoring_stats()
        return jsonify(stats)
    return jsonify({'error': 'Agent not initialized'}), 503
```

## Best Practices

1. **Regular Monitoring**: Check statistics periodically to track usage
2. **Cost Alerts**: Set up alerts if estimated costs exceed thresholds
3. **Performance Optimization**: Use average duration to identify slow operations
4. **Error Analysis**: Monitor error rates to catch issues early

## Limitations

- **Cost estimates are approximate**: Actual costs depend on your specific model and provider
- **Token counting**: Relies on LLM provider's response metadata
- **Single instance**: Statistics are per-agent instance (not global)

## Future Enhancements

Potential improvements:
- Export statistics to external monitoring systems
- Per-model cost tracking
- Real-time cost alerts
- Historical trend analysis
- Integration with observability platforms (e.g., Prometheus, Datadog)

