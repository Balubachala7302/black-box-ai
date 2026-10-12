# BLACK BOX AI
### An AI-Powered Software Incident Investigator

BLACK BOX AI is an AI-powered incident investigation system designed to help developers investigate software failures, identify anomalies, and evaluate possible root causes using evidence from application logs, metrics, and deployment events.

## Problem

When a production application fails, developers often need to investigate logs, metrics, and deployment changes manually. This can make identifying the root cause slow and difficult.

## Proposed Solution

BLACK BOX AI aims to streamline incident investigation by combining machine learning-based anomaly detection with an AI investigation agent.

The system is being developed to:

- Analyze application logs and operational metrics.
- Detect unusual behavior using machine learning.
- Generate and compare possible root-cause hypotheses.
- Recommend diagnostic steps based on available evidence.
- Evaluate investigation results against controlled test scenarios.

## Technology Stack

- Python
- FastAPI
- NVIDIA Nemotron
- Nebius Token Factory
- scikit-learn
- Pandas
- React and TypeScript (planned)

## Project Status

Early development. The Nebius API connection has been tested successfully.

The investigation workflow, anomaly detection pipeline, API endpoints, and dashboard are still being developed.

## Getting Started

### 1. Clone the repository

Replace the placeholder below with your actual GitHub repository URL.

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd black-box-ai
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate it on Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure your API key

Create a `.env` file in the project root and add:

```env
NEBIUS_API_KEY=your_nebius_api_key
```

Replace the placeholder with your own API key.

**Never commit your `.env` file or publish your API key.**

## Roadmap

- [x] Set up the Python development environment.
- [x] Test the Nebius Token Factory API connection.
- [ ] Build the FastAPI backend.
- [ ] Implement anomaly detection.
- [ ] Build the evidence-based investigation workflow.
- [ ] Create synthetic incident scenarios and evaluation tests.
- [ ] Develop the frontend dashboard.
- [ ] Deploy a public demo.

## License

This project is intended to use the MIT License.