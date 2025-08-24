# Tracing your agentic trajectories

## Objective

In this project we demonstrate how to plugin a flexible observability and tracing framework in our agentic solutions. These solutions are often quite complex, involving multiple hops: LLM → planner → tool call → sub-agent → response; with guardrails and reflections. Without tracing and visualization of agent trajectories with detailed information when something fails, it becomes very difficult to reason about the cause of the failure and fix it.

Observability is key to:

1. Deep debugging & root cause analysis
2. Performance and cost optimization
3. Trust, monitoring, and continuous improvement

## AI Solution

We use [LangChain's supervisor pattern](https://github.com/langchain-ai/langgraph-supervisor-py) to build a multi-agentic solution. [Our implementation](src/tracing_tutorial/supervisor_demo.py) is a LangGraph supervisor that coordinates 2 agents: research_expert (a ReAct agent using a web_search tool) and joke_agent (a functional task that produces a short coding joke). Per instructions, the supervisor routes each turn to the appropriate agent, appends the agent's reply to the message state, and executes the compiled workflow end-to-end.

## Step-by-Step Implementation Plan

### Step 1: Environment Setup

#### Requirements

- Python 3.10+
- `uv` for dependency management (https://github.com/astral-sh/uv)
- An OpenAI API key for the example model

#### Installation

```bash
# Install dependencies
uv sync --all-extras

# Set required API key
export OPENAI_API_KEY=...
```

### Step 2: Build the Multi-Agent System

Implementation: [`src/tracing_tutorial/supervisor_demo.py`](src/tracing_tutorial/supervisor_demo.py)

1. **Create the Supervisor Agent**: Implement a LangGraph supervisor that coordinates multiple specialized agents
2. **Implement Specialized Agents**:
   - **Joke Agent**: A functional API agent that generates coding jokes
   - **Research Agent**: A Graph API agent with web search capabilities
3. **Define Agent Routing Logic**: Supervisor decides which agent to use based on the task

### Step 3: Instrument with OpenTelemetry

Implementation: [`src/tracing_tutorial/tracing/backends.py`](src/tracing_tutorial/tracing/backends.py)

1. **Add OpenTelemetry Dependencies**: Include necessary packages in [`pyproject.toml`](pyproject.toml)
2. **Create Tracer Provider**: Configure a global TracerProvider with selected exporter
3. **Automatic Instrumentation**: Use `LangChainInstrumentor` from OpenInference to automatically instrument all LangChain components
   - This provides bulk instrumentation that automatically traces agent invocations, tool calls, LLM interactions, and message flows
   - No manual span creation needed - the instrumentation library handles it automatically

Note: While we are using the `LangChainInstrumentor` here, [OpenInference](https://github.com/Arize-ai/openinference) which is a complementary to [OpenTelemetry](https://opentelemetry.io/) provides instrumentation libraries (for python as well as javascript) for many of the other popular AI frameworks as well. So a similar generic instrumentation approach will likely work for you if you are using any of the OpenInference supported frameworks.

### Step 4: Configure Multiple Tracing Backends

Implementation: [`src/tracing_tutorial/tracing/backends.py`](src/tracing_tutorial/tracing/backends.py)

The system supports switching between multiple tracing backends via the `TRACING_BACKEND` environment variable.

**Important Note**: All backends except `console` actually use the OTLP protocol under the hood. LangFuse, LangSmith, and Phoenix are OTLP-compatible platforms that expose OTLP endpoints with their own authentication mechanisms. This means they all benefit from the standardized OpenTelemetry data format while providing specialized UI/UX for AI and LLM observability.

#### Available Backends

- **OTLP (default)**: Generic OTLP endpoint for any OpenTelemetry-compatible backend

  ```bash
  export TRACING_BACKEND=otlp
  export OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317  # gRPC endpoint (no http://)
  # Or for HTTP: export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
  ```
  
  Use this for general-purpose observability platforms like:
  - **Jaeger**: Open-source distributed tracing platform
  - **Grafana Tempo**: High-volume distributed tracing backend
  - **OpenTelemetry Collector**: Can forward to multiple backends
  - **Commercial platforms**: Datadog, New Relic, Honeycomb, Dynatrace, etc.

- **Console**: Prints spans to stdout for development (does not use OTLP)

  ```bash
  export TRACING_BACKEND=console
  ```

- **LangSmith**: LangChain's native tracing platform (uses OTLP at `/otel` endpoint)

  ```bash
  export TRACING_BACKEND=langsmith
  export LANGSMITH_API_KEY=...
  export LANGSMITH_ENDPOINT=...  # Defaults to https://api.smith.langchain.com
  ```

- **LangFuse**: Open-source LLM observability (uses OTLP at `/api/public/otel` endpoint)

  ```bash
  export TRACING_BACKEND=langfuse
  export LANGFUSE_HOST=...  # e.g., http://localhost:3000 or https://cloud.langfuse.com
  export LANGFUSE_PUBLIC_KEY=...
  export LANGFUSE_SECRET_KEY=...
  ```

- **Phoenix**: Arize Phoenix for ML observability (uses OTLP gRPC on port 4317 by default)

  ```bash
  export TRACING_BACKEND=phoenix
  export PHOENIX_ENDPOINT=localhost:4317  # gRPC endpoint (no http://)
  # For cloud: export PHOENIX_API_KEY=...
  ```

### Step 5: Set Up Local LangFuse (Optional Demo)

For this tutorial, we'll demonstrate using LangFuse as our observability backend. LangFuse is an open-source LLM engineering platform that provides excellent visualization for agent traces.

#### Prerequisites

- Docker Desktop or Rancher Desktop running locally

#### Quick Setup with Docker Compose

1. **Clone and Start LangFuse**:

   ```bash
   git clone https://github.com/langfuse/langfuse
   cd langfuse
   docker compose up -d
   ```

2. **Wait for services to be ready** (this may take a minute or two for the initial setup)

3. **Access LangFuse UI**:

   - Open (http://localhost:3000) in your browser
   - Sign up for a new account (first user becomes admin)
   - Create a new project

4. **Get API Credentials**:

   - Go to Settings → API Keys
   - Create a new API key pair
   - Copy the Public Key and Secret Key

5. **Configure Environment Variables**:

   ```bash
   export TRACING_BACKEND=langfuse
   export LANGFUSE_HOST=http://localhost:3000
   export LANGFUSE_PUBLIC_KEY=<your-public-key>
   export LANGFUSE_SECRET_KEY=<your-secret-key>
   ```

### Step 6: Run and Observe

Implementation: [`src/tracing_tutorial/scripts/run_demo.py`](src/tracing_tutorial/scripts/run_demo.py)

With LangFuse running and configured, execute the demo:

```bash
# Run with LangFuse backend (if you followed Step 5)
uv run run-demo

# Or run with console output to see traces immediately
export TRACING_BACKEND=console
uv run run-demo
```

### Step 7: Analyze Traces in LangFuse

After running the demo with LangFuse backend:

1. **Open LangFuse UI**: Navigate to (http://localhost:3000)
2. **View Traces**: Go to the "Traces" tab in your project
3. **Explore the Trace**:
   - Click on a trace to see the full execution flow
   - View the hierarchy: supervisor → agent selection → tool calls → responses
   - Examine token usage, latencies, and costs for each step
   - Review the actual prompts and completions at each stage

You should be able to see a trace like this:
![[Trace of our demo]](trace.png)

What you'll see in LangFuse:

- **Trace Timeline**: Visual representation of the execution flow
- **Span Details**: Input/output for each LangChain component
- **Performance Metrics**: Duration, token counts, and costs
- **Error Tracking**: Any failures with full stack traces
