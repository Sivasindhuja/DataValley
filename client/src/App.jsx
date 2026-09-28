import { useState, useRef, useEffect } from 'react'

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '') || 'http://localhost:8000'
const api = (path) => `${API_BASE}${path}`

function getToken(){ try{ return localStorage.getItem('token') }catch{ return null } }
function getStoredCustomer(){ try{ return localStorage.getItem('customer_id') || 'C102' }catch{ return 'C102' } }

function authHeaders(){
  const t = getToken()
  return t ? { 'Authorization': `Bearer ${t}` } : {}
}

export default function App(){
  const [messages,setMessages]=useState([{role:'agent', text:'Hi, I’m your Guardrailed Support Agent.\nI can help with orders, refunds, products, and tickets. How can I assist today?'}])
  const [input,setInput]=useState('')
  const [trace,setTrace]=useState(null)
  const [loading,setLoading]=useState(false)
  const [auth,setAuth]=useState(()=> ({ token: getToken(), customerId: getStoredCustomer() }))
  const [authMode,setAuthMode]=useState('login') // login | register
  const [authForm,setAuthForm]=useState({ customer_id:'C102', name:'Alex Johnson', email:'alex@example.com', password:'password123' })
  const [authError,setAuthError]=useState('')
  const [pendingConfirm,setPendingConfirm]=useState(false)
  const listRef = useRef(null)

  const isAuthed = !!auth.token

  useEffect(()=>{
    if(listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  },[messages, loading])

  // fetch traces/dashboard with auth after load if authed
  useEffect(()=>{ if(isAuthed) refreshTrace() },[isAuthed])

  async function refreshTrace(){
    try{
      const r=await fetch(api('/traces'), { headers: { ...authHeaders() } })
      if(!r.ok) return
      const traces=await r.json()
      if(Array.isArray(traces) && traces.length) setTrace(traces.at(-1))
    }catch{}
  }

  function logout(){
    try{ localStorage.removeItem('token'); localStorage.removeItem('customer_id') }catch{}
    setAuth({ token:null, customerId:'C102'})
    setMessages(m=>[...m, {role:'agent', text:'Logged out. Please login again.'}])
  }

  async function handleAuth(e){
    e?.preventDefault()
    setAuthError('')
    const url = authMode==='register' ? api('/auth/register') : api('/auth/login')
    // login can use customer_id OR email - prefer customer_id if provided
    const body = authMode==='register'
      ? { customer_id: authForm.customer_id.trim(), name: authForm.name.trim(), email: authForm.email.trim(), password: authForm.password }
      : { customer_id: authForm.customer_id.trim() || undefined, email: authForm.email.trim() || undefined, password: authForm.password }
    if(!body.password || body.password.length < 6){ setAuthError('Password must be at least 6 characters'); return }
    if(authMode==='register' && (!body.customer_id || !body.name || !body.email)){ setAuthError('All fields required for registration'); return }
    if(!body.customer_id && !body.email){ setAuthError('Provide customer_id or email'); return }
    try{
      const r=await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})
      const j=await r.json().catch(()=>({}))
      if(!r.ok){ setAuthError(j.detail || `Auth failed (${r.status})`); return }
      const token=j.access_token
      const cid=j.customer_id || body.customer_id
      try{ localStorage.setItem('token', token); localStorage.setItem('customer_id', cid) }catch{}
      setAuth({ token, customerId: cid })
      setMessages(m=>[...m, {role:'agent', text:`Authenticated as ${cid}. How can I help?`}])
    }catch(err){
      setAuthError('Backend not reachable. Run: python -m app.api.main')
    }
  }

  async function send(confirmOverride){
    const text = input.trim()
    if((!text && confirmOverride===undefined) || loading) return
    if(!isAuthed){ setAuthError('Please login first'); return }
    const outgoing = text || (confirmOverride ? 'yes, cancel' : '')
    // simple length guard
    if(outgoing.length > 4000){ setMessages(m=>[...m,{role:'agent', text:'Message too long (max 4000 chars)'}]); return }
    const confirm = typeof confirmOverride === 'boolean' ? confirmOverride : pendingConfirm
    const userMsg={role:'user', text: confirm ? `${outgoing} (confirm)` : outgoing}
    setMessages(m=>[...m, userMsg])
    setLoading(true)
    setInput('')
    const controller = new AbortController()
    const t = setTimeout(()=> controller.abort(), 30000)
    try{
      const r=await fetch(api('/chat'),{
        method:'POST',
        headers:{'Content-Type':'application/json', ...authHeaders()},
        body:JSON.stringify({message: outgoing, confirm}),
        signal: controller.signal
      })
      const data=await r.json().catch(()=>null)
      if(!r.ok){
        if(r.status===401){ logout(); setMessages(m=>[...m, {role:'agent', text:'Session expired. Please login again.'}]); }
        else if(r.status===429){ setMessages(m=>[...m, {role:'agent', text:'Rate limited (60/min). Please wait a moment.'}]) }
        else { setMessages(m=>[...m, {role:'agent', text: data?.detail || `Error ${r.status}: ${data?.response || 'request failed'}`}]) }
        return
      }
      setMessages(m=>[...m, {role:'agent', text:data.response, tools:data.tools_used, docs:data.docs}])
      // detect confirmation ask
      if(data.response && data.response.includes('explicit confirmation')) setPendingConfirm(true)
      else if(confirm) setPendingConfirm(false)
      else if(data.response && !data.response.includes('confirmation')) setPendingConfirm(false)
      await refreshTrace()
    }catch(e){
      if(e.name==='AbortError') setMessages(m=>[...m, {role:'agent', text:'Request timed out. Backend may be busy (Gemini latency). Try again.'}])
      else setMessages(m=>[...m, {role:'agent', text:'Backend not reachable. Run: python -m app.api.main'}])
    }finally{ clearTimeout(t); setLoading(false) }
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
            <span className="status-dot"><i/> {isAuthed ? `Authed · ${auth.customerId}` : 'Not authenticated'}</span>
            {isAuthed ? (
              <button className="btn btn-ghost" onClick={logout}>Logout</button>
            ) : (
              <span className="pill-select" style={{padding:'6px 10px'}}>Guest</span>
            )}
          </div>
        </div>
      </header>

      <div className="page">
        {!isAuthed && (
          <div className="card" style={{marginBottom:16, padding:16}}>
            <h2 style={{margin:'0 0 8px'}}><span className="icon-bubble">🔒</span> Authentication required</h2>
            <p className="card-sub" style={{margin:'0 0 12px'}}>Login with your customer account or register. JWT is required for all chat/traces calls (Bearer token).</p>
            <div style={{display:'flex', gap:8, marginBottom:12}}>
              <button className={`btn ${authMode==='login'?'btn-primary':'btn-ghost'}`} onClick={()=>setAuthMode('login')}>Login</button>
              <button className={`btn ${authMode==='register'?'btn-primary':'btn-ghost'}`} onClick={()=>setAuthMode('register')}>Register</button>
              <span style={{fontSize:12, color:'#666', alignSelf:'center'}}>Demo: C102/C103 password123 · C104 is LOCKED</span>
            </div>
            <form onSubmit={handleAuth} style={{display:'grid', gap:8, maxWidth:480}}>
              <input placeholder="Customer ID (e.g. C102)" value={authForm.customer_id} onChange={e=>setAuthForm(s=>({...s, customer_id:e.target.value}))} style={{padding:'8px 10px', border:'1px solid #ddd', borderRadius:8}}/>
              {authMode==='register' && (
                <>
                  <input placeholder="Full name" value={authForm.name} onChange={e=>setAuthForm(s=>({...s, name:e.target.value}))} style={{padding:'8px 10px', border:'1px solid #ddd', borderRadius:8}}/>
                </>
              )}
              <input placeholder="Email" value={authForm.email} onChange={e=>setAuthForm(s=>({...s, email:e.target.value}))} style={{padding:'8px 10px', border:'1px solid #ddd', borderRadius:8}}/>
              <input type="password" placeholder="Password (min 6)" value={authForm.password} onChange={e=>setAuthForm(s=>({...s, password:e.target.value}))} style={{padding:'8px 10px', border:'1px solid #ddd', borderRadius:8}}/>
              <button type="submit" className="btn btn-primary"> {authMode==='register' ? 'Create account & login' : 'Login'}</button>
              {authError && <div style={{color:'#DC2626', fontSize:13}}>{authError}</div>}
            </form>
          </div>
        )}

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
                <span style={{width:6,height:6,borderRadius:99,background: isAuthed ? '#16A34A' : '#DC2626', display:'inline-block'}}/> {isAuthed ? auth.customerId : 'guest'}
                {pendingConfirm && <span className="meta-pill" style={{background:'#FEF3C7'}}>Awaiting confirmation</span>}
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
                  placeholder={isAuthed ? "Ask about an order, refund, or product…" : "Login first to chat"}
                  disabled={!isAuthed}
                  maxLength={4000}
                />
                <button className="send-btn" onClick={()=>send()} disabled={!input.trim() || loading || !isAuthed} aria-label="Send">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M5 12L19 5l-3 7 3 7-14-7Z" fill="white" stroke="white" strokeWidth="1.4" strokeLinejoin="round"/></svg>
                </button>
              </div>
              {pendingConfirm && (
                <div style={{display:'flex', gap:8, marginTop:8}}>
                  <button className="btn btn-primary" onClick={()=>send(true)} disabled={loading}>Yes, confirm cancel</button>
                  <button className="btn btn-ghost" onClick={()=>{ setPendingConfirm(false); setInput('') }}>Cancel</button>
                </div>
              )}
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
                <button key={s} onClick={()=>setInput(s)} className="chip" disabled={!isAuthed}>{s}</button>
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
                      <span className="kv"><b>{trace.trace_id?.slice(0,8)}</b> · {trace.timestamp ? new Date(trace.timestamp).toLocaleTimeString() : ''}</span>
                      <span className="kv"><b>{trace.latency_ms ?? '-'}</b> ms</span>
                      <span className="kv"><b>${trace.cost_usd != null ? Number(trace.cost_usd).toFixed(4) : '0.0000'}</b></span>
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

            <Metrics isAuthed={isAuthed} />
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

function Metrics({isAuthed}){
  const [m,setM]=useState(null)
  const [busy,setBusy]=useState(false)
  const [err,setErr]=useState('')
  async function load(){
    if(!isAuthed){ setErr('Login to view metrics'); return }
    setBusy(true); setErr('')
    try{
      const r=await fetch(api('/dashboard'), { headers: { ...authHeaders() } })
      const j=await r.json().catch(()=>null)
      if(!r.ok){ setErr(j?.detail || `Failed ${r.status}`); }
      else setM(j)
    }catch{ setErr('Backend not reachable') }
    setBusy(false)
  }
  async function runEvals(){
    if(!isAuthed){ setErr('Login first'); return }
    setBusy(true); setErr('')
    try{
      const r=await fetch(api('/evals/run'), { headers: { ...authHeaders() } })
      const j=await r.json().catch(()=>null)
      if(!r.ok){ setErr(j?.detail || `Failed ${r.status}`); }
      else setM(prev=> prev ? {...prev, evals:j} : {evals:j, task_success:0, tool_accuracy:0, rag_accuracy:0, policy_compliance:0, guardrail_accuracy:0, escalation_accuracy:0})
    }catch{ setErr('Backend not reachable') }
    setBusy(false)
  }
  useEffect(()=>{ if(isAuthed) load() },[isAuthed])
  return (
    <div className="card">
      <div className="card-header">
        <h2><span className="icon-bubble">▦</span> Agent Performance <span>§20</span></h2>
        <div className="metrics-head">
          <button onClick={load} className="btn btn-ghost" disabled={busy}>{busy ? '…' : '↻ Refresh'}</button>
          <button onClick={runEvals} className="btn btn-primary" disabled={busy}>▶ Run evals</button>
        </div>
      </div>
      {err && <div style={{padding:'8px 16px', color:'#DC2626', fontSize:13}}>{err}</div>}
      {!m ? (
        <div className="empty" style={{padding:'22px 16px'}}>
          <p style={{fontSize:13}}>Metrics not loaded</p>
          <span>Task Success, Tool Accuracy, RAG, Policy Compliance, Guardrail & Escalation — per spec §20 {isAuthed ? '' : '(login required)'}</span>
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
