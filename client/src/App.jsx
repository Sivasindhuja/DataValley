import { useState, useRef, useEffect } from 'react'

export default function App(){
  const [messages,setMessages]=useState([{role:'agent', text:'Hi, I’m your Guardrailed Support Agent.\nI can help with orders, refunds, products, and tickets. How can I assist today?'}])
  const [input,setInput]=useState('')
  const [customer,setCustomer]=useState('C102')
  const [trace,setTrace]=useState(null)
  const [loading,setLoading]=useState(false)
  const listRef = useRef(null)

  useEffect(()=>{
    if(listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  },[messages, loading])

  async function send(){
    if(!input.trim() || loading) return
    const userMsg={role:'user', text:input}
    setMessages(m=>[...m, userMsg])
    setLoading(true)
    const outgoing = input
    setInput('')
    try{
      const r=await fetch('http://localhost:8000/chat',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:outgoing, customer_id:customer})})
      const data=await r.json()
      setMessages(m=>[...m, {role:'agent', text:data.response, tools:data.tools_used, docs:data.docs}])
      const t=await fetch('http://localhost:8000/traces')
      const traces=await t.json()
      setTrace(traces.at(-1))
    }catch(e){
      setMessages(m=>[...m, {role:'agent', text:'Backend not reachable. Run: python -m app.api.main'}])
    }
    setLoading(false)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark">◈</div>
            <div>
              <div className="brand-title">Datavalley Support</div>
              <div className="brand-sub">Guardrailed · Minimal · Premium</div>
            </div>
          </div>
          <div className="topbar-right">
            <span className="status-dot"><i/> System operational</span>
            <select className="pill-select" value={customer} onChange={e=>setCustomer(e.target.value)} aria-label="Customer">
              <option value="C102">C102 — Alex Johnson · #123 SHIPPED / #124 PENDING</option>
              <option value="C103">C103 — Priya Singh · #125 DELIVERED</option>
              <option value="C104">C104 — Locked account</option>
            </select>
          </div>
        </div>
      </header>

      <div className="page">
        <div className="hero">
          <div>
            <div className="mini-label">Customer Support — LLM + Deterministic Policy</div>
            <h1><em>Guardrailed</em> AI that respects policy.</h1>
            <p>The LLM decides what it <i>wants</i> to do — a deterministic policy engine decides what is <i>allowed</i>. Every step is traced and auditable.</p>
          </div>
        </div>

        <div className="layout">
          {/* Chat column */}
          <div className="card">
            <div className="card-header">
              <h2><span className="icon-bubble">✦</span> Conversation <span>{messages.length} messages</span></h2>
              <div className="card-sub" style={{display:'flex', alignItems:'center', gap:8}}>
                <span style={{width:6,height:6,borderRadius:99,background:'#16A34A', display:'inline-block'}}/> {customer}
              </div>
            </div>

            <div className="chat-viewport" ref={listRef}>
              {messages.map((m,i)=>(
                <div key={i} className={`msg-row ${m.role}`}>
                  {m.role==='agent' && <div className="avatar agent">◈</div>}
                  <div style={{maxWidth:'74%'}}>
                    <div className={`bubble ${m.role}`}>{m.text}</div>
                    {m.tools && (
                      <div className="meta-line">
                        {m.tools.length>0 && <span className="meta-pill">Tools · {m.tools.join(', ')}</span>}
                        {m.docs?.length>0 && <span className="meta-pill">Docs · {m.docs.join(', ')}</span>}
                      </div>
                    )}
                  </div>
                  {m.role==='user' && <div className="avatar user">You</div>}
                </div>
              ))}
              {loading && (
                <div className="msg-row agent">
                  <div className="avatar agent">◈</div>
                  <div className="thinking">Thinking <span className="dots"><i/><i/><i/></span></div>
                </div>
              )}
            </div>

            <div className="composer">
              <div className="composer-input">
                <input
                  value={input}
                  onChange={e=>setInput(e.target.value)}
                  onKeyDown={e=>e.key==='Enter'&&send()}
                  placeholder="Ask about an order, refund, or product…"
                />
                <button className="send-btn" onClick={send} disabled={!input.trim() || loading} aria-label="Send">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M5 12L19 5l-3 7 3 7-14-7Z" fill="white" stroke="white" strokeWidth="1.4" strokeLinejoin="round"/></svg>
                </button>
              </div>
            </div>

            <div className="suggestions">
              {[
                "My order #123 hasn't arrived. Can you check?",
                "Can you cancel order #123?",
                "Update delivery address for order #124 to 99 New Ave",
                "Why hasn't my refund R421 arrived?",
                "What's the warranty for product-a?",
                "I want to speak to a human",
              ].map(s=>(
                <button key={s} onClick={()=>setInput(s)} className="chip">{s}</button>
              ))}
            </div>
          </div>

          {/* Right column */}
          <div className="side-stack">
            <div className="card">
              <div className="card-header">
                <h2><span className="icon-bubble">◐</span> Observability & Trace</h2>
                <span className="mini-label">{trace ? trace.trace_id?.slice(0,8) : 'idle'}</span>
              </div>
              <div className="trace-viewport">
                {!trace ? (
                  <div className="empty">
                    <div className="empty-icon">◎</div>
                    <p>No trace yet</p>
                    <span>Send a message to generate a trace timeline</span>
                  </div>
                ) : (
                  <div>
                    <div className="trace-head">
                      <span className="kv"><b>{trace.trace_id?.slice(0,8)}</b> · {new Date(trace.timestamp).toLocaleTimeString()}</span>
                      <span className="kv"><b>{trace.latency_ms}</b> ms</span>
                      <span className="kv"><b>${Number(trace.cost_usd).toFixed(4)}</b></span>
                      <span className="kv"><b>{trace.customer_id}</b></span>
                    </div>
                    <div className="divider"/>
                    {trace.steps?.map((s,i)=>(
                      <div key={i} className={`step ${s.safe ? 'safe' : 'blocked'}`}>
                        <div className="step-head">
                          <span className="step-name">{s.safe ? '●' : '○'} {s.name}</span>
                          <span className={`badge ${s.safe ? 'ok' : 'fail'}`}>{s.safe ? 'allow' : 'blocked'}</span>
                        </div>
                        <pre>{JSON.stringify(s.data,null,2).slice(0,700)}</pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <Metrics />
          </div>
        </div>
      </div>

      <div className="footer">
        <span>© 2026 Datavalley · Premium Support Experience — built for trust & auditability.</span>
        <span style={{display:'flex', gap:12}}><span>Latency-aware</span><span>·</span><span>PII-guarded</span><span>·</span><span>Policy-enforced</span></span>
      </div>
    </div>
  )
}

function Bar({label, value, color}){
  return (
    <div className="bar-row">
      <div className="bar-label"><span>{label}</span><span>{value}%</span></div>
      <div className="track"><div className="fill" style={{width:`${value}%`, background: color}} /></div>
    </div>
  )
}

function Metrics(){
  const [m,setM]=useState(null)
  const [busy,setBusy]=useState(false)
  async function load(){
    setBusy(true)
    try{ const r=await fetch('http://localhost:8000/dashboard'); setM(await r.json()) }catch{}
    setBusy(false)
  }
  async function runEvals(){
    setBusy(true)
    try{
      const r=await fetch('http://localhost:8000/evals/run');
      const j=await r.json();
      setM(prev=> prev ? {...prev, evals:j} : {evals:j, task_success:0, tool_accuracy:0, rag_accuracy:0, policy_compliance:0, guardrail_accuracy:0, escalation_accuracy:0})
    }catch{}
    setBusy(false)
  }
  useEffect(()=>{ load() },[])
  return (
    <div className="card">
      <div className="card-header">
        <h2><span className="icon-bubble">▦</span> Agent Performance <span>§20</span></h2>
        <div className="metrics-head">
          <button onClick={load} className="btn btn-ghost" disabled={busy}>{busy ? '…' : '↻ Refresh'}</button>
          <button onClick={runEvals} className="btn btn-primary" disabled={busy}>▶ Run evals</button>
        </div>
      </div>
      {!m ? (
        <div className="empty" style={{padding:'22px 16px'}}>
          <p style={{fontSize:13}}>Metrics not loaded</p>
          <span>Task Success, Tool Accuracy, RAG, Policy Compliance, Guardrail & Escalation — per spec §20</span>
        </div>
      ) : (
        <div className="metrics-grid">
          <Bar label="Task Success" value={m.task_success ?? 0} color="#0F0F0F"/>
          <Bar label="Tool Accuracy" value={m.tool_accuracy ?? 0} color="#16A34A"/>
          <Bar label="RAG Accuracy" value={m.rag_accuracy ?? 0} color="#D97706"/>
          <Bar label="Policy Compliance" value={m.policy_compliance ?? 0} color="#6D28D9"/>
          <Bar label="Guardrail Accuracy" value={m.guardrail_accuracy ?? 0} color="#EA580C"/>
          <Bar label="Escalation Accuracy" value={m.escalation_accuracy ?? 0} color="#DC2626"/>

          <div className="stats-box">
            <div><b>Operational</b> · avg latency {(m.avg_latency ?? 0)}ms · traces {m.trace_count ?? 0} · blocked {m.blocked ?? 0} · escalations {m.escalations ?? 0}</div>
            <div><b>Safety</b> · PII detections {m.metrics?.pii_detections ?? 0} · output blocked {m.metrics?.output_blocked ?? 0}</div>
            <div><b>Tokens / Cost</b> · {m.metrics?.responses ?? 0} responses · cost ~${(m.trace_count ? (m.trace_count*0.0001).toFixed(4) : '0.0000')}</div>
          </div>

          <details className="raw-toggle"><summary>Raw JSON ▾</summary><pre>{JSON.stringify(m,null,2).slice(0,3000)}</pre></details>
        </div>
      )}
    </div>
  )
}
