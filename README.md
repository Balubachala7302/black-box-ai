
# BLACK BOX AI
### An AI-Powered, Evidence-Driven Software Incident Investigator

BLACK BOX AI is an AI-powered incident investigation system designed to help developers investigate software failures, detect anomalies, and identify potential root causes using evidence from application logs, operational metrics, deployment signals, and OpenTelemetry traces.

Powered by **NVIDIA Nemotron** through **Nebius Token Factory**, BLACK BOX AI combines deterministic diagnostic tools with agentic AI reasoning to produce structured incident investigations and actionable recommendations.

## Problem

When production applications fail, developers often need to manually correlate logs, metrics, traces, and deployment changes. This process can be time-consuming and makes identifying the underlying cause of an incident difficult.

## Solution

BLACK BOX AI streamlines incident investigation through an evidence-driven diagnostic workflow.

The system can:

- Analyze application logs to identify potential failure patterns.
- Inspect operational metrics, including error rates and response latency.
- Investigate recent deployment signals.
- Analyze OpenTelemetry traces, including failed spans, slow operations, and parent-child relationships.
- Detect anomalous behavior using diagnostic thresholds and evidence analysis.
- Generate and evaluate potential root-cause hypotheses.
- Recommend actionable diagnostic steps.
- Evaluate investigation behavior using controlled synthetic incident scenarios.

## Key Features

### 1. Evidence-Based Investigation
Collects diagnostic evidence from multiple sources before generating an investigation report.

### 2. Agentic AI Investigation
Uses NVIDIA Nemotron to reason over diagnostic results and perform targeted follow-up investigations.

### 3. Multi-Source Evidence Analysis
Supports application logs, operational metrics, deployment signals, and normalized OpenTelemetry trace and log payloads.

### 4. Diagnostic Tool Orchestration
Uses deterministic preflight diagnostics, result caching, duplicate-call prevention, and a shared four-call investigation budget.

### 5. Controlled Evaluation
Includes automated tests for diagnostic tools, trace analysis, agent orchestration, and investigation workflows.

## Architecture

```text
              Incident Input
                    |
                    v
              FastAPI Backend
                    |
                    v
          Evidence Normalization
                    |
          +---------+---------+
          |         |         |
          v         v         v
         Logs    Metrics    OTEL Traces
          |         |         |
          +---------+---------+
                    |
                    v
          Diagnostic Tool Layer
                    |
                    v
          Evidence Preflight
                    |
                    v
          NVIDIA Nemotron Agent
             (Nebius API)
                    |
                    v
          Root Cause Investigation
                    |
                    v
          Structured Incident Report
```

## Technology Stack

| Category | Technologies |
|---|---|
| Language | Python |
| Backend | FastAPI |
| AI Model | NVIDIA Nemotron 3 Super |
| AI Inference | Nebius Token Factory |
| Data Processing | Pandas |
| Machine Learning | scikit-learn |
| Observability | Prometheus payloads, OpenTelemetry |
| Testing | pytest |
| Frontend | React, TypeScript |

## Project Status

**Working backend prototype with automated test coverage.**

- FastAPI investigation endpoints implemented.
- Nebius Token Factory integration implemented.
- NVIDIA Nemotron agentic investigation workflow implemented.
- Diagnostic tools for logs, metrics, deployments, and traces implemented.
- Prometheus and OpenTelemetry payload normalization implemented.
- Deterministic evidence preflight and diagnostic result caching implemented.
- Controlled synthetic incident evaluation and automated tests implemented.
- Frontend and public demo status should be verified before submission.

**Test status:** 53 automated tests passing.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Balubachala7302/black-box-ai.git
cd black-box-ai
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
NEBIUS_API_KEY=your_nebius_api_key
```

Never commit your `.env` file or expose your API key.

### 6. Start the backend

```powershell
python -m uvicorn app.main:app --reload
```

### 7. Open API documentation

Visit:

http://127.0.0.1:8000/docs

## Running Tests

Run the automated test suite:

```powershell
python -m pytest app/tests -q
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Health check |
| POST | `/evidence/normalize` | Normalize supplied evidence payloads |
| POST | `/incidents/investigate` | Investigate incidents using baseline or Nemotron mode |

### Investigation Modes

- `baseline` — deterministic diagnostic investigation.
- `nemotron` — AI-assisted investigation using NVIDIA Nemotron.

## Current Limitations

- Prometheus and OpenTelemetry support currently analyzes supplied payloads; it does not establish live connections to monitoring infrastructure.
- Deployment investigation relies on the deployment information supplied with the incident.
- Anomaly thresholds and diagnostic findings are heuristic and should not be interpreted as production-validated detection accuracy.
- Nemotron-generated root-cause hypotheses require human verification before production remediation.

## Future Improvements

- Live Prometheus and Grafana integrations.
- OpenTelemetry Collector integration.
- Advanced anomaly detection using historical operational data.
- More comprehensive incident benchmarks.
- Improved root-cause hypothesis verification.
- Production deployment and a polished investigation dashboard.

## License

MIT License.
