import React, { useState } from 'react';
import { ChatMessageEvent, RFPProjectSummary } from './types';

export default function App() {
  const defaultHost = `${window.location.protocol}//${window.location.hostname}:8000`;
  const [backendUrl, setBackendUrl] = useState<string>(defaultHost);
  const [activeRfpId, setActiveRfpId] = useState<string | null>(null);
  const [events, setEvents] = useState<ChatMessageEvent[]>([
    {
      sender: 'System Orchestrator',
      phase: 1,
      message_english: 'Welcome to the Autonomous BFS Pre-Sales RFP Engine (LAN Host). Select an entry point to initialize:',
      hitl_buttons: [
        { action_id: 'NEW_RFP', label: 'New RFP', variant: 'primary' },
        { action_id: 'EXISTING_RFP', label: 'Existing RFP', variant: 'secondary' }
      ]
    }
  ]);
  const [showNewForm, setShowNewForm] = useState<boolean>(false);
  const [existingRfps, setExistingRfps] = useState<RFPProjectSummary[] | null>(null);
  const [clientName, setClientName] = useState<string>('');
  const [language, setLanguage] = useState<string>('en');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [samplePpt, setSamplePpt] = useState<File | null>(null);
  const [sampleExcel, setSampleExcel] = useState<File | null>(null);
  const [inspectedEvent, setInspectedEvent] = useState<ChatMessageEvent | null>(null);

  const handleGatewayOrHitl = async (actionId: string, rfpId?: string) => {
    if (actionId === 'NEW_RFP') {
      setShowNewForm(true);
      setExistingRfps(null);
      return;
    }
    if (actionId === 'EXISTING_RFP') {
      setShowNewForm(false);
      setLoading(true);
      try {
        const res = await fetch(`${backendUrl}/api/rfps`);
        const data = await res.json();
        setExistingRfps(data.rfps || []);
      } catch (err) {
        alert(`Failed to reach LAN backend at ${backendUrl}`);
      } finally {
        setLoading(false);
      }
      return;
    }

    const targetRfp = rfpId || activeRfpId;
    if (!targetRfp) return;
    setLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/rfps/${targetRfp}/hitl`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId })
      });
      const data = await res.json();
      if (data.state?.chat_events) {
        setEvents(data.state.chat_events);
        const latestArtifact = [...data.state.chat_events].reverse().find((e: ChatMessageEvent) => e.artifact_payload);
        if (latestArtifact) setInspectedEvent(latestArtifact);
      } else if (data.message) {
        setEvents(prev => [...prev, {
          rfp_id: targetRfp,
          sender: 'Executive Sign-Off Gate',
          phase: 5,
          message_english: data.message,
          hitl_buttons: []
        }]);
      }
    } catch (err) {
      alert('Error submitting HITL decision to LAN host.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRfp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientName || !selectedFile) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('client_name', clientName);
    formData.append('detected_language', language);
    formData.append('file', selectedFile);
    if (samplePpt) formData.append('sample_deal_brief_ppt', samplePpt);
    if (sampleExcel) formData.append('sample_questionnaire_excel', sampleExcel);
 
    try {
      const res = await fetch(`${backendUrl}/api/rfps/new`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setActiveRfpId(data.rfp_id);
      setShowNewForm(false);
      if (data.state?.chat_events) {
        setEvents(data.state.chat_events);
        const latestArtifact = [...data.state.chat_events].reverse().find((ev: ChatMessageEvent) => ev.artifact_payload);
        if (latestArtifact) setInspectedEvent(latestArtifact);
      }
    } catch (err) {
      alert(`Upload failed. Verify FastAPI is running at ${backendUrl}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>Autonomous BFS Pre-Sales RFP Engine</h1>
        <div className="lan-box">
          <span>LAN Backend:</span>
          <input value={backendUrl} onChange={e => setBackendUrl(e.target.value)} />
        </div>
      </header>

      <div className="workspace">
        <main className="chat-pane">
          <div className="chat-stream">
            {events.map((ev, idx) => (
              <div key={idx} className="msg-card">
                <div className="msg-header">
                  <strong>{ev.sender}</strong>
                  <span className="badge">Phase {ev.phase} {ev.rfp_id ? `• ${ev.rfp_id}` : ''}</span>
                </div>
                <p>{ev.message_english}</p>

                <div className="btn-row">
                  {ev.artifact_payload && (
                    <button className="btn btn-secondary" onClick={() => setInspectedEvent(ev)}>
                      Inspect Dual-Language Artifact ({ev.artifact_type})
                  {ev.artifact_type === 'EFFORT_MATRIX' && (ev.rfp_id || activeRfpId) && (
                    <>
                      <a
                        className="btn btn-secondary"
                        href={`${backendUrl}/api/rfps/${ev.rfp_id || activeRfpId}/download/deal_brief_pptx`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download Deal Brief (.pptx)
                      </a>
                      <a
                        className="btn btn-secondary"
                        href={`${backendUrl}/api/rfps/${ev.rfp_id || activeRfpId}/download/questionnaire_xlsx`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download Questionnaire (.xlsx)
                      </a>
                    </>
                  )}
                  {ev.artifact_type === 'FINAL_PACKAGE' && (ev.rfp_id || activeRfpId) && (
                    <>
                      <a className="btn btn-secondary" href={`${backendUrl}/api/rfps/${ev.rfp_id || activeRfpId}/download/native_pdf`} target="_blank" rel="noreferrer">Native PDF</a>
                      <a className="btn btn-secondary" href={`${backendUrl}/api/rfps/${ev.rfp_id || activeRfpId}/download/english_mirror_pdf`} target="_blank" rel="noreferrer">English Mirror PDF</a>
                      <a className="btn btn-secondary" href={`${backendUrl}/api/rfps/${ev.rfp_id || activeRfpId}/download/commercial_xlsx`} target="_blank" rel="noreferrer">Commercial TCO (.xlsx)</a>
                      <a className="btn btn-secondary" href={`${backendUrl}/api/rfps/${ev.rfp_id || activeRfpId}/download/c_suite_pptx`} target="_blank" rel="noreferrer">C-Suite Pitch (.pptx)</a>
                    </>
                  )}

                    </button>
                  )}
                  {ev.hitl_buttons?.map(btn => (
                    <button
                      key={btn.action_id}
                      disabled={loading}
                      className={`btn btn-${btn.variant === 'danger' ? 'danger' : btn.variant === 'secondary' ? 'secondary' : 'primary'}`}
                      onClick={() => handleGatewayOrHitl(btn.action_id, ev.rfp_id)}
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            {existingRfps && (
              <div className="msg-card">
                <div className="msg-header"><strong>Historical RFP State Matrix</strong></div>
                {existingRfps.length === 0 ? <p>No existing RFPs found in local SQLite registry.</p> : (
                  <table className="rfp-table">
                    <thead>
                      <tr><th>RFP ID</th><th>Client</th><th>Lang</th><th>Phase</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                      {existingRfps.map(r => (
                        <tr key={r.rfp_id}>
                          <td>{r.rfp_id}</td>
                          <td>{r.client_name_redacted}</td>
                          <td>{r.detected_language}</td>
                          <td>{r.current_phase}</td>
                          <td>{r.workflow_status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>

          {showNewForm && (
            <form className="upload-bar" onSubmit={handleCreateRfp}>
              <input
                type="text"
                placeholder="Client Bank Name"
                value={clientName}
                onChange={e => setClientName(e.target.value)}
                required
              />
              <select value={language} onChange={e => setLanguage(e.target.value)}>
                <option value="en">English (en)</option>
                <option value="pt">Portuguese (pt)</option>
                <option value="es">Spanish (es)</option>
                <option value="de">German (de)</option>
                <option value="fr">French (fr)</option>
              </select>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                required
              />
              <label title="Optional Sample Deal Brief (.pptx)">
                Sample PPT:
                <input
                  type="file"
                  accept=".pptx"
                  onChange={e => setSamplePpt(e.target.files?.[0] || null)}
                />
              </label>
              <label title="Optional Sample Questionnaire (.xlsx)">
                Sample Excel:
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={e => setSampleExcel(e.target.files?.[0] || null)}
                />
              </label>

              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Ingesting & Running Triage...' : 'Launch Phase 1 Triage'}
              </button>
            </form>
          )}
        </main>

        {inspectedEvent && inspectedEvent.artifact_payload && (
          <aside className="artifact-drawer">
            <div className="drawer-header">
              <strong>{inspectedEvent.artifact_type} (Rule 2 Side-by-Side)</strong>
              <button className="btn btn-secondary" onClick={() => setInspectedEvent(null)}>Close</button>
            </div>
            <div className="dual-grid">
              <div className="dual-col">
                <h4>English Core (System Truth)</h4>
                <pre>{JSON.stringify(inspectedEvent.artifact_payload.english || inspectedEvent.artifact_payload, null, 2)}</pre>
              </div>
              <div className="dual-col">
                <h4>Native RFP Mirror ({language.toUpperCase()})</h4>
                <pre>{JSON.stringify(inspectedEvent.artifact_payload.native || inspectedEvent.artifact_payload, null, 2)}</pre>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
