
import { useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

type Finding = Record<string, unknown>;

type Hypothesis = {
  cause: string;
  verification_status?: string;
  confidence?: number;
  evidence?: string[];
  supporting_evidence?: string[];
  missing_evidence?: string[];
  recommended_check?: string;
};

type TraceStep = {
  step?: number;
  tool: string;
  reason?: string;
  result?: unknown;
};

type EvidenceCollection = {
  findings?: Finding[];
  [key: string]: unknown;
};

type IncidentResult = {
  incident_title?: string;
  investigation_status?: string;
  status?: string;
  agent?: string;
  tool_calls_used?: number;
  analysis?: string;
  evidence?: {
    logs?: EvidenceCollection;
    metrics?: EvidenceCollection;
    deployment?: Record<string, unknown>;
    [key: string]: unknown;
  };
  hypotheses?: Hypothesis[];
  root_cause_decision?: {
    status?: string;
    root_cause?: string | null;
    reason?: string;
  };
  evidence_gaps?: {
    gaps?: Array<{ cause: string; missing_evidence: string[] }>;
    note?: string;
  };
  investigation_trace?: TraceStep[];
  limitations?: string[];
};

type Page = "investigation" | "evidence" | "status";
type Mode = "baseline" | "nemotron";
type ApiStatus = "unknown" | "checking" | "online" | "offline";

function App() {
  const [page, setPage] = useState<Page>("investigation");
  const [title, setTitle] = useState("Database Connection Timeout");
  const [description, setDescription] = useState(
    "Requests are failing while waiting for database connections."
  );
  const [logs, setLogs] = useState(
    "ERROR: Database connection timeout\nWARNING: Connection pool limit reached"
  );
  const [errorRate, setErrorRate] = useState("25");
  const [latency, setLatency] = useState("1000");
  const [recentDeployment, setRecentDeployment] = useState(false);
  const [mode, setMode] = useState<Mode>("baseline");
  const [result, setResult] = useState<IncidentResult | null>(null);
  const [resultMode, setResultMode] = useState<Mode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiStatus, setApiStatus] = useState<ApiStatus>("unknown");
  const [healthDetails, setHealthDetails] = useState("");

  async function checkApi() {
    setApiStatus("checking");
    setHealthDetails("");

    try {
      const response = await fetch(`${API_URL}/health`);

      if (!response.ok) {
        throw new Error(`Health check returned ${response.status}`);
      }

      setApiStatus("online");
      setHealthDetails("Health endpoint responded successfully.");
    } catch (err) {
      setApiStatus("offline");
      setHealthDetails(
        err instanceof Error ? err.message : "Unable to reach the API."
      );
    }
  }

  async function runInvestigation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setResult(null);
    setResultMode(null);

    try {
      const response = await fetch(
        `${API_URL}/incidents/investigate?mode=${mode}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            title,
            description,
            logs: logs
              .split("\n")
              .map((line) => line.trim())
              .filter(Boolean),
            error_rate: Number(errorRate),
            latency_ms: Number(latency),
            recent_deployment: recentDeployment
          })
        }
      );

      const body: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        const detail =
          typeof body === "object" &&
          body !== null &&
          "detail" in body
            ? (body as { detail?: unknown }).detail
            : undefined;

        const message =
          typeof detail === "string"
            ? detail
            : detail !== undefined
              ? JSON.stringify(detail)
              : `Investigation failed (${response.status})`;

        throw new Error(`HTTP ${response.status}: ${message}`);
      }

      if (
        typeof body !== "object" ||
        body === null ||
        Array.isArray(body)
      ) {
        throw new Error("The API returned an unexpected response format.");
      }

      setResult(body as IncidentResult);
      setResultMode(mode);
      setApiStatus("online");

    } catch (err) {
      setApiStatus("offline");

      setError(
        err instanceof Error
          ? `${err.message}. Check that FastAPI is running and CORS is configured.`
          : "Unable to contact the investigation API."
      );

    } finally {
      setLoading(false);
    }
  }

  const isNemotronResult = resultMode === "nemotron";

  const decision = result?.root_cause_decision;

  const findings =
    result?.evidence?.logs?.findings ?? [];

  const metricFindings =
    result?.evidence?.metrics?.findings ?? [];

  const hypotheses =
    result?.hypotheses ?? [];

  const trace =
    result?.investigation_trace ?? [];

  const gaps =
    result?.evidence_gaps?.gaps ?? [];

  const missingEvidenceCount = gaps.reduce(
    (total, gap) =>
      total + (gap.missing_evidence?.length ?? 0),
    0
  );

  function renderJson(value: unknown) {
    return JSON.stringify(value ?? null, null, 2);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">

        <div className="brand">
          <div className="brand-icon">B</div>

          <div>
            <strong>BLACK BOX AI</strong>
            <span>INCIDENT INTELLIGENCE</span>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <button
          type="button"
          className={`nav-item ${page === "investigation" ? "active" : ""}`}
          onClick={() => setPage("investigation")}
        >
          ◈ &nbsp; Investigation
        </button>

        <button
          type="button"
          className={`nav-item ${page === "evidence" ? "active" : ""}`}
          onClick={() => setPage("evidence")}
        >
          ⌁ &nbsp; Evidence explorer
        </button>

        <button
          type="button"
          className={`nav-item ${page === "status" ? "active" : ""}`}
          onClick={() => {
            setPage("status");
            void checkApi();
          }}
        >
          ◎ &nbsp; System status
        </button>

        <div className="sidebar-bottom">
          <span
            className={`status-dot ${apiStatus === "online" ? "online" : ""}`}
          />

          <div>
            <strong>Investigation engine</strong>

            <span>
              {apiStatus === "online"
                ? "API connection online"
                : apiStatus === "offline"
                  ? "API connection unavailable"
                  : apiStatus === "checking"
                    ? "Checking API connection"
                    : "API connection not checked"}
            </span>
          </div>
        </div>

      </aside>

      <section className="main-content">

        <header className="topbar">

          <div>
            <span className="eyebrow">
              OPERATIONS / INCIDENT RESPONSE
            </span>

            <h1>
              {page === "investigation"
                ? "Incident investigation"
                : page === "evidence"
                  ? "Evidence explorer"
                  : "System status"}
            </h1>

            <p>
              {page === "investigation"
                ? "Trace failures. Verify evidence. Avoid unsupported conclusions."
                : page === "evidence"
                  ? "Review the evidence collected during the latest investigation."
                  : "Check the connection to the incident investigation API."}
            </p>
          </div>

          <div className="engine-badge">
            <span
              className={`status-dot ${apiStatus === "online" ? "online" : ""}`}
            />
            {mode === "baseline"
              ? "RULE-BASED ENGINE"
              : "NEMOTRON ENGINE"}
          </div>

        </header>

        {page === "investigation" && (
          <>

            <section className="metric-grid">

              <article className="metric-card">
                <span>INVESTIGATION STATUS</span>
                <strong>
                  {loading
                    ? "Running"
                    : result
                      ? "Completed"
                      : "Ready"}
                </strong>
                <small>
                  {isNemotronResult
                    ? "AI agent response received"
                    : "Evidence-led analysis"}
                </small>
              </article>

              <article className="metric-card">
                <span>LOG FINDINGS</span>
                <strong>
                  {result
                    ? isNemotronResult
                      ? "N/A"
                      : findings.length
                    : "—"}
                </strong>
                <small>
                  {isNemotronResult
                    ? "Not supplied as structured findings"
                    : "Matched log signals"}
                </small>
              </article>

              <article className="metric-card">
                <span>CANDIDATE CAUSES</span>
                <strong>
                  {result
                    ? isNemotronResult
                      ? "N/A"
                      : hypotheses.length
                    : "—"}
                </strong>
                <small>
                  {isNemotronResult
                    ? "Review agent analysis"
                    : "Generated and verified"}
                </small>
              </article>

              <article className="metric-card">
                <span>EVIDENCE GAPS</span>
                <strong>
                  {result
                    ? isNemotronResult
                      ? "N/A"
                      : missingEvidenceCount
                    : "—"}
                </strong>
                <small>
                  {isNemotronResult
                    ? "Not returned as structured gaps"
                    : "Additional checks needed"}
                </small>
              </article>

            </section>

            <div className="workspace-grid">

              <section className="panel incident-panel">

                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">INPUT</span>
                    <h2>Incident details</h2>
                  </div>
                  <span className="step-number">01</span>
                </div>

                <form onSubmit={runInvestigation}>

                  <label>
                    Incident title
                    <input
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      required
                    />
                  </label>

                  <label>
                    Description
                    <textarea
                      value={description}
                      onChange={(event) =>
                        setDescription(event.target.value)
                      }
                      placeholder="What happened? Which service is affected?"
                      rows={3}
                    />
                  </label>

                  <label>
                    Application logs{" "}
                    <span className="label-hint">One log per line</span>

                    <textarea
                      value={logs}
                      onChange={(event) => setLogs(event.target.value)}
                      rows={6}
                    />
                  </label>

                  <div className="input-row">

                    <label>
                      Error rate (%)
                      <input
                        type="number"
                        min="0"
                        value={errorRate}
                        onChange={(event) =>
                          setErrorRate(event.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Latency (ms)
                      <input
                        type="number"
                        min="0"
                        value={latency}
                        onChange={(event) =>
                          setLatency(event.target.value)
                        }
                        required
                      />
                    </label>

                  </div>

                  <label>
                    Investigation engine

                    <select
                      value={mode}
                      onChange={(event) =>
                        setMode(event.target.value as Mode)
                      }
                    >
                      <option value="baseline">
                        Baseline — rule-based
                      </option>

                      <option value="nemotron">
                        Nemotron — AI agent
                      </option>
                    </select>
                  </label>

                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={recentDeployment}
                      onChange={(event) =>
                        setRecentDeployment(event.target.checked)
                      }
                    />
                    A recent deployment occurred
                  </label>

                  <button
                    className="primary-button"
                    disabled={loading}
                    type="submit"
                  >
                    {loading
                      ? "Investigating…"
                      : "◈ Run investigation"}
                  </button>

                </form>

                {error && (
                  <div className="error-message">
                    {error}
                  </div>
                )}

              </section>

              <div className="results-column">

                <section className="panel decision-panel">

                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">ANALYSIS</span>
                      <h2>Root-cause assessment</h2>
                    </div>
                    <span className="step-number">02</span>
                  </div>

                  {!result ? (

                    <div className="empty-state">
                      <div className="empty-icon">⌁</div>
                      <strong>Awaiting incident data</strong>
                      <p>
                        Submit an incident to see candidate causes and
                        verification results.
                      </p>
                    </div>

                  ) : isNemotronResult ? (

                    <>
                      <div className="decision-status">
                        <span className="eyebrow">AGENT STATUS</span>
                        <strong>
                          {result.status ?? "Response received"}
                        </strong>
                      </div>

                      <p className="muted">
                        Model: {result.agent ?? "Nemotron"}
                        {typeof result.tool_calls_used === "number"
                          ? ` · ${result.tool_calls_used} tool calls`
                          : ""}
                      </p>

                      <h3>AI investigation analysis</h3>

                      {result.analysis ? (
                        <div className="analysis-text">
                          {result.analysis}
                        </div>
                      ) : (
                        <p className="muted">
                          The API returned no analysis text.
                          Inspect the investigation trace below.
                        </p>
                      )}

                      <p className="disclaimer">
                        AI-generated analysis should be checked against
                        returned evidence before treating a cause as confirmed.
                      </p>
                    </>

                  ) : (

                    <>
                      <div className="decision-status">
                        <span className="eyebrow">DECISION STATUS</span>
                        <strong>
                          {decision?.status ?? "Not provided"}
                        </strong>
                      </div>

                      <h3>
                        {decision?.root_cause ?? "No root cause selected"}
                      </h3>

                      <p className="muted">
                        {decision?.reason ?? "No decision rationale was returned."}
                      </p>

                      <p className="disclaimer">
                        A supported candidate is not definitive proof of causation.
                      </p>
                    </>

                  )}

                </section>

                <section className="panel">

                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">VERIFICATION</span>
                      <h2>Candidate hypotheses</h2>
                    </div>
                    <span className="step-number">03</span>
                  </div>

                  {hypotheses.length === 0 ? (

                    <p className="muted">
                      {isNemotronResult
                        ? "This Nemotron response does not provide structured hypotheses. Review the AI analysis above."
                        : "Hypotheses will appear here after an investigation."}
                    </p>

                  ) : (

                    hypotheses.map((hypothesis, index) => (

                      <article
                        className="hypothesis-card"
                        key={`${hypothesis.cause}-${index}`}
                      >

                        <div className="hypothesis-top">
                          <strong>{hypothesis.cause}</strong>

                          <span
                            className={`tag ${(hypothesis.verification_status ?? "unknown").toLowerCase()}`}
                          >
                            {hypothesis.verification_status ?? "unknown"}
                          </span>
                        </div>

                        {(hypothesis.supporting_evidence ??
                          hypothesis.evidence ??
                          []).map((item, evidenceIndex) => (
                          <p className="evidence-line" key={evidenceIndex}>
                            + {item}
                          </p>
                        ))}

                        {(hypothesis.missing_evidence ?? []).map(
                          (item, evidenceIndex) => (
                            <p className="missing-line" key={evidenceIndex}>
                              △ Missing: {item}
                            </p>
                          )
                        )}

                        {hypothesis.recommended_check && (
                          <p className="next-check">
                            Next check: {hypothesis.recommended_check}
                          </p>
                        )}

                      </article>

                    ))

                  )}

                </section>

                <section className="panel">

                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">AUDITABILITY</span>
                      <h2>Investigation trace</h2>
                    </div>
                    <span className="step-number">04</span>
                  </div>

                  {trace.length === 0 ? (

                    <p className="muted">
                      The tool execution trace will appear here.
                    </p>

                  ) : (

                    trace.map((step, index) => (

                      <details
                        className="trace-step"
                        key={`${step.step ?? index + 1}-${step.tool}-${index}`}
                      >

                        <summary>
                          <span className="trace-index">
                            {String(step.step ?? index + 1).padStart(2, "0")}
                          </span>

                          <strong>{step.tool}</strong>

                          <span className="trace-arrow">↗</span>
                        </summary>

                        {step.reason && (
                          <p className="muted">{step.reason}</p>
                        )}

                        <pre className="evidence-json">
                          {renderJson(step.result)}
                        </pre>

                      </details>

                    ))

                  )}

                </section>

                {result?.limitations &&
                  result.limitations.length > 0 && (

                    <section className="panel">
                      <h2>Current limitations</h2>

                      {result.limitations.map((item, index) => (
                        <p className="muted" key={index}>
                          • {item}
                        </p>
                      ))}
                    </section>

                  )}

              </div>

            </div>

          </>
        )}

        {page === "evidence" && (

          <div className="results-column">

            {!result ? (

              <section className="panel">
                <h2>No investigation evidence yet</h2>

                <p className="muted">
                  Run an investigation first. Its collected evidence
                  will be displayed here.
                </p>

                <button
                  type="button"
                  className="primary-button"
                  onClick={() => setPage("investigation")}
                >
                  Go to investigation
                </button>
              </section>

            ) : isNemotronResult ? (

              <>

                <section className="panel">
                  <span className="eyebrow">AI ANALYSIS</span>
                  <h2>Nemotron response</h2>

                  <p className="muted">
                    Model: {result.agent ?? "Nemotron"} · Status:{" "}
                    {result.status ?? "unknown"}
                  </p>

                  <div className="analysis-text">
                    {result.analysis || "No analysis text was returned."}
                  </div>
                </section>

                <section className="panel">
                  <span className="eyebrow">TOOL TRACE</span>
                  <h2>Diagnostic tool results</h2>

                  {trace.length ? (

                    trace.map((step, index) => (

                      <details
                        className="trace-step"
                        key={`${step.tool}-${index}`}
                      >
                        <summary>
                          <span className="trace-index">
                            {String(step.step ?? index + 1).padStart(2, "0")}
                          </span>
                          <strong>{step.tool}</strong>
                        </summary>

                        <pre className="evidence-json">
                          {renderJson(step.result)}
                        </pre>
                      </details>

                    ))

                  ) : (
                    <p className="muted">
                      No tool trace was returned.
                    </p>
                  )}

                </section>

              </>

            ) : (

              <>

                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">LOGS</span>
                      <h2>Log findings</h2>
                    </div>
                    <span className="step-number">
                      {findings.length}
                    </span>
                  </div>

                  {findings.length ? (
                    findings.map((item, index) => (
                      <pre className="evidence-json" key={index}>
                        {renderJson(item)}
                      </pre>
                    ))
                  ) : (
                    <p className="muted">
                      No structured log findings returned.
                    </p>
                  )}
                </section>

                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">METRICS</span>
                      <h2>Metric findings</h2>
                    </div>
                    <span className="step-number">
                      {metricFindings.length}
                    </span>
                  </div>

                  {metricFindings.length ? (
                    metricFindings.map((item, index) => (
                      <pre className="evidence-json" key={index}>
                        {renderJson(item)}
                      </pre>
                    ))
                  ) : (
                    <p className="muted">
                      No metric findings returned.
                    </p>
                  )}
                </section>

                <section className="panel">
                  <span className="eyebrow">DEPLOYMENT</span>
                  <h2>Deployment evidence</h2>

                  <pre className="evidence-json">
                    {renderJson(
                      result.evidence?.deployment ?? "Not collected"
                    )}
                  </pre>
                </section>

                <section className="panel">
                  <span className="eyebrow">EVIDENCE GAPS</span>
                  <h2>Additional evidence requests</h2>

                  {gaps.length ? (

                    gaps.map((gap, index) => (

                      <article
                        className="gap-card"
                        key={`${gap.cause}-${index}`}
                      >
                        <strong>{gap.cause}</strong>

                        {gap.missing_evidence.map((item, itemIndex) => (
                          <p className="missing-line" key={itemIndex}>
                            △ {item}
                          </p>
                        ))}
                      </article>

                    ))

                  ) : (
                    <p className="muted">
                      No structured evidence gaps returned.
                    </p>
                  )}

                  {result.evidence_gaps?.note && (
                    <p className="muted">
                      {result.evidence_gaps.note}
                    </p>
                  )}
                </section>

              </>

            )}

          </div>

        )}

        {page === "status" && (

          <div className="results-column">

            <section className="panel">

              <div className="panel-heading">
                <div>
                  <span className="eyebrow">API CONNECTIVITY</span>
                  <h2>Backend health</h2>
                </div>

                <span className={`tag ${apiStatus}`}>
                  {apiStatus}
                </span>
              </div>

              <p className="muted">
                API base URL: {API_URL}
              </p>

              <p className="muted">
                {healthDetails ||
                  "Run a health check to inspect connectivity."}
              </p>

              <button
                type="button"
                className="primary-button"
                onClick={() => void checkApi()}
                disabled={apiStatus === "checking"}
              >
                {apiStatus === "checking"
                  ? "Checking…"
                  : "Refresh health check"}
              </button>

            </section>

            <section className="panel">
              <span className="eyebrow">LAST INVESTIGATION</span>
              <h2>Result availability</h2>

              <p className="muted">
                {result
                  ? `Latest result: ${result.incident_title ?? title} (${resultMode ?? "unknown"} mode).`
                  : "No investigation result has been stored in this session."}
              </p>

              {result && (
                <pre className="evidence-json">
                  {renderJson(result)}
                </pre>
              )}
            </section>

          </div>

        )}

      </section>
    </main>
  );
}

export default App;
