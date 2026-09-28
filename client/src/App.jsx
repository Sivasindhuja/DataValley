import { useState, useRef, useEffect } from 'react'

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '') || 'http://localhost:8000'
const api = (path) => `${API_BASE}${path}`
function getToken(){ try{ return localStorage.getItem('token') }catch{ return null } }
function getStoredCustomer(){ try{ return localStorage.getItem('customer_id') || 'C102' }catch{ return 'C102' } }
function authHeaders(){ const t=getToken(); return t? { 'Authorization': `Bearer ${t}` } : {} }

function Topbar({ view, setView, isAuthed, auth, onLoginClick, onLogout }){
  return (
    <header className="g-topbar">
      <div className="g-topbar-inner">
        <div className="g-brand" onClick={()=>setView('home')}>
          <div className="g-logo">◈</div>
          <div>
            <div className="g-brand-title">Support</div>
            <div className="g-brand-sub">Guardrailed · Minimal · Premium</div>
          </div>
        </div>
        <nav className="g-nav" aria-label="Primary">
          <a className={view==='home'?'active':''} onClick={()=>setView('home')} href="#home">Home</a>
          <a className={view==='docs'?'active':''} onClick={()=>setView('docs')} href="#docs">Documentation</a>
          <a className={view==='chat'?'active':''} onClick={()=> isAuthed ? setView('chat') : onLoginClick()} href="#chat">Chat</a>
        </nav>
        <div className="g-topbar-right">
          {isAuthed ? (
            <>
              <span className="g-chip"><span className="g-dot"/>{auth.customerId}</span>
              <div className="g-avatar" title={auth.customerId}>{auth.customerId.slice(0,2)}</div>
              <button className="g-btn g-btn-ghost" onClick={onLogout}>Sign out</button>
            </>
          ) : (
            <>
              <button className="g-btn g-btn-ghost" onClick={()=>setView('docs')}>Docs</button>
              <button className="g-btn g-btn-primary" onClick={onLoginClick}>Sign in</button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

function Home({ isAuthed, onCTAClick, setView }){
  return (
    <div className="g-page">
      <section className="g-hero">
        <div>
          <div className="g-kicker">Guardrailed Customer Support</div>
          <h1>
            <em>Guardrailed</em> AI that<br/>respects policy.
          </h1>
          <p>The LLM decides what it <em>wants</em> to do — deterministic policy decides what is <em>allowed</em>. Memory, RAG and human escalation, wrapped in a quiet, premium experience.</p>
          <div className="g-hero-actions">
            <button className="g-btn g-btn-primary" style={{height:44, padding:'0 26px'}} onClick={onCTAClick}>{isAuthed ? 'Open chat' : 'Sign in to start'}</button>
            <button className="g-btn g-btn-secondary" style={{height:44}} onClick={()=>setView('docs')}>Documentation</button>
          </div>
          <div style={{marginTop:24, display:'flex', gap:8, flexWrap:'wrap'}}>
            <span className="g-chip">PII guarded</span>
            <span className="g-chip">Injection blocked</span>
            <span className="g-chip">Policy enforced</span>
            <span className="g-chip">Auditable</span>
          </div>
          <div className="g-searchbar" onClick={onCTAClick} role="button" tabIndex={0} style={{cursor:'pointer'}}>
            <span style={{color:'#9A9A9E', fontSize:14}}>⌕</span>
            <input placeholder={isAuthed ? 'Ask about order #123, refund, warranty…' : 'Sign in to chat with the agent…'} readOnly style={{cursor:'pointer'}} />
            <button className="g-search-btn" aria-label="Search">→</button>
          </div>
          <div style={{marginTop:10, fontSize:12, color:varMuted2}}>Try “My order #123 hasn’t arrived” · “Cancel order #123” · “Refund R421”</div>
        </div>

        <div className="g-hero-card">
          <div style={{display:'flex', alignItems:'center', gap:10, marginBottom:16}}>
            <span style={{width:6,height:6,borderRadius:'50%', background:'#0F0F0F', display:'inline-block'}}/>
            <span style={{fontSize:13, fontWeight:600, letterSpacing:'-.01em'}}>How it works</span>
            <span style={{marginLeft:'auto', fontSize:11, color:'#9A9A9E', background:'#F6F6F3', border:'1px solid #E8E8E3', padding:'4px 8px', borderRadius:999}}>Live trace</span>
          </div>
          <div style={{display:'grid', gap:10}}>
            {[
              ['Input guard', 'Jailbreak & PII check'],
              ['Memory · RAG', 'Chroma + BM25 + reranker'],
              ['Tools', 'Order · Customer · Support'],
              ['Policy engine', 'Allow / block decision'],
              ['Output guard', 'Grounded, no hallucination'],
            ].map(([k,d])=>(
              <div key={k} style={{display:'flex', alignItems:'center', gap:12, border:'1px solid #E8E8E3', borderRadius:12, padding:'11px 12px', background:'#fff'}}>
                <span style={{width:28,height:28, borderRadius:8, background:'#F6F6F3', border:'1px solid #E8E8E3', display:'grid', placeItems:'center', fontSize:11}}>—</span>
                <div style={{flex:1}}>
                  <div style={{fontSize:13, fontWeight:600}}>{k}</div>
                  <div style={{fontSize:11, color:'#6E6E73'}}>{d}</div>
                </div>
                <span style={{fontSize:11, fontWeight:600, color:'#6E6E73', background:'#F6F6F3', padding:'4px 8px', borderRadius:999, border:'1px solid #E8E8E3'}}>•</span>
              </div>
            ))}
          </div>
          <div style={{marginTop:14, fontSize:11, color:'#9A9A9E', textAlign:'center'}}>Every turn is traced and auditable</div>
        </div>
      </section>

      <section className="g-section">
        <div className="g-kicker">Features</div>
        <h2 className="g-h2">Everything for <em>trusted</em> support.</h2>
        <p className="g-sub">Premium by restraint. No color noise — just type, space, and clear decisions.</p>
        <div className="g-grid3">
          {[
            {icon:'—', t:'Deterministic Policy Engine', d:'LLM proposes; policy disposes. Cancellations, refunds and address changes validated against order state.'},
            {icon:'—', t:'RAG — Hybrid + Reranker', d:'Chroma + BM25 hybrid with version and recency-weighted reranker. Every answer grounded in docs.'},
            {icon:'—', t:'MCP Tools', d:'Customer, Order, Support and Knowledge servers via direct or MCP stdio with timeout and health checks.'},
            {icon:'—', t:'Memory', d:'Postgres + Redis cache — SQLite fallback for dev. Remembers orders, tickets and preferences.'},
            {icon:'—', t:'Guardrails', d:'Input: 25+ injection patterns. Output: PII redaction and grounded citations. Action: allow / block.'},
            {icon:'—', t:'Observability & Evals', d:'OTel-ready traces, latency & cost, dashboard and 52 eval cases for continuous trust.'},
          ].map(c=>(
            <div key={c.t} className="g-card">
              <div className="g-card-icon">{c.icon}</div>
              <h3>{c.t}</h3>
              <p>{c.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="g-section" style={{paddingTop:8}}>
        <div className="g-kicker">Product guide</div>
        <h2 className="g-h2">How to use in <em>3</em> steps.</h2>
        <div className="g-steps">
          <div className="g-step">
            <div className="g-step-num">1</div>
            <h4>Sign in</h4>
            <p>Use <code>customer_id</code> (e.g. C102) or email + password. Demo: <code>password123</code>. A JWT is stored locally (24h).</p>
            <div style={{marginTop:12, display:'flex', gap:6, flexWrap:'wrap'}}>
              <span className="g-chip">C102 · Alex</span><span className="g-chip">C103 · Sam</span><span className="g-chip">C104 · locked</span>
            </div>
          </div>
          <div className="g-step">
            <div className="g-step-num">2</div>
            <h4>Chat</h4>
            <p>Ask about orders, refunds, warranty or address changes. Try “My order #123 hasn’t arrived”, “Refund R421”, or “Speak to a human”.</p>
            <p style={{marginTop:12, fontSize:12, color:'#6E6E73', background:'#F6F6F3', border:'1px solid #E8E8E3', padding:'8px 10px', borderRadius:10}}>Cancellation requires explicit confirmation — “Yes, confirm”.</p>
          </div>
          <div className="g-step">
            <div className="g-step-num">3</div>
            <h4>Inspect</h4>
            <p>Open the trace drawer to see guardrail decisions, tools and latency. Metrics live at <code>/dashboard</code> and <code>/traces</code>.</p>
          </div>
        </div>

        <div style={{marginTop:20}} className="g-grid2">
          <div className="g-card">
            <h3>Tips</h3>
            <ul style={{margin:'10px 0 0', paddingLeft:18, color:'#6E6E73', fontSize:13, lineHeight:1.8}}>
              <li>Address update — provide the full new address in one message</li>
              <li>Human handoff — say “speak to a human” to create a ticket</li>
              <li>Refunds are answered via RAG, no tool needed</li>
            </ul>
          </div>
          <div className="g-card">
            <h3>Security</h3>
            <ul style={{margin:'10px 0 0', paddingLeft:18, color:'#6E6E73', fontSize:13, lineHeight:1.8}}>
              <li>Bearer JWT required for <code>/chat</code>, <code>/traces</code>, <code>/dashboard</code></li>
              <li>Rate limit 60/min · 30s timeout · input / output guards</li>
              <li>Traces owner/admin · evals admin-only</li>
            </ul>
          </div>
        </div>

        <div style={{marginTop:28, display:'flex', gap:12, alignItems:'center', flexWrap:'wrap', background:'#F6F6F3', border:'1px solid #E8E8E3', borderRadius:20, padding:'20px 24px'}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:600, letterSpacing:'-.01em'}}>Ready to try?</div>
            <div style={{fontSize:13, color:'#6E6E73', marginTop:2}}>Sign in and the chat opens instantly — quiet, fast, auditable.</div>
          </div>
          <button className="g-btn g-btn-primary" style={{height:44, padding:'0 26px'}} onClick={onCTAClick}>{isAuthed ? 'Go to chat' : 'Sign in to start'}</button>
          <button className="g-btn g-btn-secondary" style={{height:44}} onClick={()=>setView('docs')}>Documentation</button>
        </div>
      </section>
    </div>
  )
}
const varMuted2 = '#9A9A9E'

function Docs({ setView, onCTAClick }){
  const [active, setActive] = useState('overview')
  const sections = [
    {id:'overview', label:'Overview'},
    {id:'quickstart', label:'Quick start'},
    {id:'auth', label:'Authentication'},
    {id:'chat', label:'Chat API'},
    {id:'policies', label:'Policies & tools'},
    {id:'rag', label:'RAG'},
    {id:'guardrails', label:'Guardrails'},
    {id:'observability', label:'Observability'},
    {id:'evals', label:'Evaluation'},
    {id:'deploy', label:'Deployment'},
  ]
  return (
    <div className="g-page">
      <div style={{padding:'20px 0 0', display:'flex', gap:8, alignItems:'center', color:'#6E6E73', fontSize:13}}>
        <a onClick={()=>setView('home')} style={{cursor:'pointer'}}>Home</a> <span style={{color:'#9A9A9E'}}>›</span> <b style={{color:'#0F0F0F'}}>Documentation</b>
        <span style={{marginLeft:'auto'}}><button className="g-btn g-btn-primary" onClick={onCTAClick}>Sign in to chat</button></span>
      </div>
      <div className="g-docs">
        <nav className="g-docs-nav">
          {sections.map(s=>(
            <a key={s.id} className={active===s.id?'active':''} href={`#${s.id}`} onClick={(e)=>{e.preventDefault(); document.getElementById(s.id)?.scrollIntoView({behavior:'smooth', block:'start'}); setActive(s.id)}}>{s.label}</a>
          ))}
        </nav>
        <div className="g-docs-content">
          <div className="g-docs-article">
            <h2 id="overview">Overview</h2>
            <p>Guardrailed AI Customer Support — RAG + MCP + Policy Guardrails + Human Escalation + Evals + Tracing.</p>
            <p>Principle: <b>LLM decides what it wants to do; deterministic logic decides whether it is allowed to.</b> Every turn is traced and auditable.</p>
            <pre>{`Customer -> Input Guardrails -> Agent (LangGraph + Gemini) -> Memory / RAG / MCP Tools -> Policy Engine -> Output Guardrails -> Customer
                                                                               -> Human Escalation`}</pre>

            <h2 id="quickstart">Quick start</h2>
            <h3>Lightweight — no Docker</h3>
            <pre>{`pip install -r requirements.txt
cp .env.example .env   # add GOOGLE_API_KEY, JWT_SECRET
python -m app.tools.seed
python -m app.rag.ingestion
python -m app.api.main        # http://localhost:8000
cd client && npm install && npm run dev  # http://localhost:5173`}</pre>
            <h3>Production — Docker</h3>
            <pre>{`cp .env.example .env
docker-compose up --build  # API at /docs`}</pre>

            <h2 id="auth">Authentication</h2>
            <p>All <code>/chat</code>, <code>/traces</code>, <code>/dashboard</code> require <code>Authorization: Bearer &lt;JWT&gt;</code>.</p>
            <pre>{`curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" \\
  -d '{"customer_id":"C102","name":"Alex","email":"a@test.com","password":"pass123"}'
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \\
  -d '{"customer_id":"C102","password":"pass123"}'
curl -H "Authorization: Bearer $TOKEN" -d '{"message":"My order #123 hasn\\'t arrived"}' http://localhost:8000/chat`}</pre>
            <p>Demo: <code>C102 / C103 · password123</code> · C104 locked</p>

            <h2 id="chat">Chat API</h2>
            <p><code>POST /chat {"{"}"message": str, "confirm": bool{"}"}</code> — confirm on second turn for cancellations. Returns <code>response, tools_used, docs</code>. Rate limited 60/min, 30s timeout.</p>

            <h2 id="policies">Policies &amp; tools</h2>
            <ul>
              <li><b>Policy Engine:</b> SHIPPED → ticket, DELIVERED not cancellable, address change only if not shipped.</li>
              <li><b>MCP servers:</b> customer / order / support / knowledge — direct or stdio mode.</li>
              <li><b>Memory:</b> Postgres + Redis (cached), SQLite fallback.</li>
            </ul>

            <h2 id="rag">RAG</h2>
            <p>Chroma + BM25 hybrid + version/recency reranker on versioned knowledge docs. Recall@3, MRR, NDCG reported.</p>

            <h2 id="guardrails">Guardrails</h2>
            <ul>
              <li><b>Input:</b> 25+ injection patterns, 4000 char limit</li>
              <li><b>Action:</b> policy allow / block before side effects</li>
              <li><b>Output:</b> PII redaction + hallucination grounding</li>
            </ul>

            <h2 id="observability">Observability</h2>
            <p>Traces → <code>data/traces.jsonl</code> + OTLP. <code>GET /traces</code> (owner/admin), <code>GET /dashboard</code> (auth).</p>

            <h2 id="evals">Evaluation</h2>
            <pre>{`pytest -q
python -m app.evaluation.runner
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/evals/run`}</pre>

            <h2 id="deploy">Deployment</h2>
            <p>Set <code>CORS_ORIGINS</code>, <code>GOOGLE_API_KEY</code>, <code>JWT_SECRET</code>, <code>DATABASE_URL</code>, <code>REDIS_URL</code> in <code>.env</code>.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function LoginModal({ mode, setMode, form, setForm, error, onSubmit, onClose }){
  return (
    <div className="g-overlay" onClick={onClose}>
      <div className="g-login-card" onClick={e=>e.stopPropagation()}>
        <div className="g-login-head">
          <div className="g-logo" style={{margin:'0 auto'}}>◈</div>
          <h2>{mode==='login' ? 'Welcome back' : 'Create account'}</h2>
          <p>{mode==='login' ? 'Sign in to Support' : 'Get started with Support'}</p>
        </div>
        <div style={{padding:'0 28px'}}>
          <div className="g-segment">
            <button className={mode==='login'?'active':''} onClick={()=>setMode('login')}>Sign in</button>
            <button className={mode==='register'?'active':''} onClick={()=>setMode('register')}>Create account</button>
          </div>
        </div>
        <form className="g-login-form" onSubmit={onSubmit} style={{marginTop:14}}>
          <div className="g-field">
            <input placeholder=" " value={form.customer_id} onChange={e=>setForm(s=>({...s, customer_id:e.target.value}))} />
            <label>Customer ID (e.g. C102)</label>
          </div>
          {mode==='register' && (
            <div className="g-field">
              <input placeholder=" " value={form.name} onChange={e=>setForm(s=>({...s, name:e.target.value}))} />
              <label>Full name</label>
            </div>
          )}
          <div className="g-field">
            <input placeholder=" " value={form.email} onChange={e=>setForm(s=>({...s, email:e.target.value}))} />
            <label>Email</label>
          </div>
          <div className="g-field">
            <input placeholder=" " type="password" value={form.password} onChange={e=>setForm(s=>({...s, password:e.target.value}))} />
            <label>Password (min 6)</label>
          </div>
          <div style={{fontSize:11, color:'#6E6E73', background:'#F6F6F3', border:'1px solid #E8E8E3', borderRadius:10, padding:'8px 10px'}}>Demo: <b>C102</b> / <b>C103</b> · <code>password123</code> · C104 locked</div>
          {error && <div style={{color:'#8B0000', fontSize:12, background:'#FFFBFB', border:'1px solid #E8CFCF', padding:'8px 10px', borderRadius:10}}>{error}</div>}
          <button type="submit" className="g-btn g-btn-primary" style={{height:44, width:'100%'}}>{mode==='register' ? 'Create & sign in' : 'Sign in'}</button>
          <button type="button" className="g-btn g-btn-ghost" style={{width:'100%'}} onClick={onClose}>Continue browsing</button>
        </form>
      </div>
    </div>
  )
}

function ChatView({ auth, trace, setTrace }){
  const [messages,setMessages]=useState(()=> [{role:'agent', text:'Hi — I’m your Support Agent.\nI can help with orders, refunds, products, and tickets. How can I help?'}])
  const [input,setInput]=useState('')
  const [loading,setLoading]=useState(false)
  const [pendingConfirm,setPendingConfirm]=useState(false)
  const [showTrace,setShowTrace]=useState(false)
  const listRef=useRef(null)
  useEffect(()=>{ if(listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight },[messages, loading])
  async function refreshTrace(){
    try{ const r=await fetch(api('/traces'), { headers:{...authHeaders()}}); if(!r.ok) return; const traces=await r.json(); if(Array.isArray(traces)&&traces.length) setTrace(traces.at(-1)) }catch{}
  }
  async function send(confirmOverride){
    const text=input.trim()
    if((!text && confirmOverride===undefined) || loading) return
    const outgoing=text || (confirmOverride ? 'yes, cancel' : '')
    if(outgoing.length>4000){ setMessages(m=>[...m,{role:'agent', text:'Message too long (max 4000 chars)'}]); return }
    const confirm = typeof confirmOverride==='boolean' ? confirmOverride : pendingConfirm
    const userMsg={role:'user', text: confirm ? `${outgoing} (confirm)` : outgoing}
    setMessages(m=>[...m,userMsg]); setLoading(true); setInput('')
    const controller=new AbortController(); const t=setTimeout(()=>controller.abort(),30000)
    try{
      const r=await fetch(api('/chat'),{ method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body:JSON.stringify({message:outgoing, confirm}), signal:controller.signal })
      const data=await r.json().catch(()=>null)
      if(!r.ok){
        if(r.status===401) setMessages(m=>[...m,{role:'agent', text:'Session expired. Please sign in again.'}])
        else if(r.status===429) setMessages(m=>[...m,{role:'agent', text:'Rate limited (60/min). Please wait a moment.'}])
        else setMessages(m=>[...m,{role:'agent', text: data?.detail || `Error ${r.status}: ${data?.response || 'request failed'}`}])
        return
      }
      setMessages(m=>[...m,{role:'agent', text:data.response, tools:data.tools_used, docs:data.docs}])
      if(data.response && data.response.includes('explicit confirmation')) setPendingConfirm(true)
      else if(confirm) setPendingConfirm(false)
      else if(data.response && !data.response.includes('confirmation')) setPendingConfirm(false)
      await refreshTrace()
    }catch(e){
      if(e.name==='AbortError') setMessages(m=>[...m,{role:'agent', text:'Request timed out. Try again.'}])
      else setMessages(m=>[...m,{role:'agent', text:'Backend not reachable. Run: python -m app.api.main'}])
    }finally{ clearTimeout(t); setLoading(false) }
  }
  return (
    <div className="g-page">
      <div className={`g-chat-shell ${showTrace?'with-trace':''}`}>
        <div className="g-panel g-history-col">
          <div className="g-panel-header"><h3>◈ Support</h3><span>{auth.customerId}</span></div>
          <div style={{padding:'14px', flex:1, overflow:'auto'}}>
            <div style={{fontSize:11, fontWeight:600, letterSpacing:'.08em', textTransform:'uppercase', color:'#9A9A9E', marginBottom:10}}>Suggestions</div>
            {[
              "My order #123 hasn't arrived. Can you check?",
              "Can you cancel order #123?",
              "Update delivery address for order #124 to 99 New Ave",
              "Why hasn't my refund R421 arrived?",
              "What's the warranty for product-a?",
              "I want to speak to a human",
            ].map(s=>(
              <button key={s} onClick={()=>setInput(s)} className="g-chip-btn" style={{width:'100%', textAlign:'left', marginBottom:8, whiteSpace:'normal', height:'auto', padding:'10px 12px'}}>{s}</button>
            ))}
            <div style={{marginTop:16, padding:14, background:'#F6F6F3', border:'1px solid #E8E8E3', borderRadius:14}}>
              <div style={{fontSize:12, fontWeight:600}}>Tips</div>
              <div style={{fontSize:12, color:'#6E6E73', lineHeight:1.6, marginTop:6}}>Cancel needs explicit confirmation. Address change requires full new address.</div>
            </div>
          </div>
          <div style={{padding:12, borderTop:'1px solid #F0F0EC', display:'flex', alignItems:'center', gap:10}}>
            <div className="g-avatar">{auth.customerId.slice(0,2)}</div>
            <div style={{flex:1, minWidth:0}}><div style={{fontSize:13, fontWeight:600}}>{auth.customerId}</div><div style={{fontSize:11, color:'#9A9A9E'}}>Authenticated</div></div>
            <span className="g-dot" title="online"/>
          </div>
        </div>

        <div className="g-panel">
          <div className="g-panel-header">
            <h3>Conversation</h3>
            <div style={{display:'flex', gap:8, alignItems:'center'}}>
              <span style={{fontSize:11, color:'#9A9A9E'}}>{messages.length} messages</span>
              <button className="g-btn g-btn-ghost" style={{height:28, padding:'0 10px', fontSize:12, border:'1px solid #E8E8E3', background: showTrace ? '#0F0F0F' : '#fff', color: showTrace ? '#fff' : '#0F0F0F'}} onClick={()=>setShowTrace(v=>!v)}>{showTrace ? 'Hide trace' : 'Trace'}</button>
            </div>
          </div>
          <div className="g-chat-viewport" ref={listRef}>
            {messages.map((m,i)=>(
              <div key={i} className={`g-msg-row ${m.role}`}>
                {m.role==='agent' && <div className="g-avatar-sm agent">◈</div>}
                <div style={{maxWidth:'76%'}}>
                  <div className={`g-bubble ${m.role}`}>{m.text}</div>
                  {m.tools && (
                    <div className="g-meta">
                      {m.tools.length>0 && <span className="g-meta-pill">Tools · {m.tools.join(', ')}</span>}
                      {m.docs?.length>0 && <span className="g-meta-pill">Docs · {m.docs.join(', ')}</span>}
                    </div>
                  )}
                </div>
                {m.role==='user' && <div className="g-avatar-sm user">You</div>}
              </div>
            ))}
            {loading && <div className="g-msg-row"><div className="g-avatar-sm agent">◈</div><div className="g-bubble agent">Thinking…</div></div>}
          </div>
          <div className="g-composer">
            <div className="g-composer-inner">
              <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder="Ask about an order, refund, or product…" maxLength={4000} />
              <button className="g-send" onClick={()=>send()} disabled={!input.trim()||loading} aria-label="Send">↑</button>
            </div>
            {pendingConfirm && <div style={{display:'flex', gap:8, marginTop:10}}><button className="g-btn g-btn-primary" onClick={()=>send(true)} disabled={loading}>Yes, confirm</button><button className="g-btn g-btn-ghost" onClick={()=>{setPendingConfirm(false); setInput('')}}>Cancel</button></div>}
          </div>
          <div className="g-chips">
            {["Order #123","Cancel #123","Warranty","Refund R421"].map(s=>(
              <button key={s} className="g-chip-btn" onClick={()=>setInput(s)}>{s}</button>
            ))}
          </div>
        </div>

        {showTrace && (
          <div className="g-panel g-trace-col">
            <div className="g-panel-header"><h3>Trace</h3><span>{trace ? trace.trace_id?.slice(0,8) : 'idle'}</span></div>
            <div style={{overflow:'auto', flex:1, padding:12}}>
              {!trace ? (
                <div className="g-empty"><div style={{fontSize:18, letterSpacing:'.2em'}}>—</div><p style={{margin:'8px 0 4px', fontSize:13, fontWeight:600}}>No trace yet</p><span style={{fontSize:12}}>Send a message to generate audit trail</span></div>
              ) : (
                <>
                  <div style={{display:'flex', gap:6, flexWrap:'wrap', marginBottom:12}}>
                    <span className="g-chip" style={{fontFamily:'var(--font-mono)', fontSize:11}}>{trace.trace_id?.slice(0,8)}</span>
                    <span className="g-chip" style={{fontFamily:'var(--font-mono)', fontSize:11}}>{trace.latency_ms??'-'} ms</span>
                    <span className="g-chip">{trace.customer_id}</span>
                  </div>
                  {trace.steps?.map((s,i)=>(
                    <div key={i} className={`g-trace-step ${s.safe?'safe':'blocked'}`}>
                      <div style={{display:'flex', justifyContent:'space-between', gap:8, marginBottom:6}}>
                        <span style={{fontSize:12, fontWeight:600}}>{s.safe?'●':'○'} {s.name}</span>
                        <span style={{fontSize:10, fontWeight:700, letterSpacing:'.06em', textTransform:'uppercase', padding:'3px 7px', borderRadius:999, background:s.safe?'#F6F6F3':'#FFFBFB', border:`1px solid ${s.safe?'#E8E8E3':'#E8CFCF'}`}}>{s.safe?'allow':'blocked'}</span>
                      </div>
                      <pre style={{margin:0, fontFamily:'var(--font-mono)', fontSize:11, background:'#F6F6F3', border:'1px solid #E8E8E3', borderRadius:8, padding:'8px 10px', maxHeight:140, overflow:'auto', whiteSpace:'pre-wrap'}}>{JSON.stringify(s.data,null,2).slice(0,700)}</pre>
                    </div>
                  ))}
                </>
              )}
            </div>
            <MetricsPanel />
          </div>
        )}
      </div>
    </div>
  )
}

function MetricsPanel(){
  const [m,setM]=useState(null); const [busy,setBusy]=useState(false); const [err,setErr]=useState('')
  async function load(){
    setBusy(true); setErr('')
    try{ const r=await fetch(api('/dashboard'),{headers:{...authHeaders()}}); const j=await r.json().catch(()=>null); if(!r.ok) setErr(j?.detail||`Failed ${r.status}`); else setM(j) }catch{ setErr('Backend not reachable') }
    setBusy(false)
  }
  async function runEvals(){
    setBusy(true); setErr('')
    try{ const r=await fetch(api('/evals/run'),{headers:{...authHeaders()}}); const j=await r.json().catch(()=>null); if(!r.ok) setErr(j?.detail||`Failed ${r.status}`); else setM(prev=> prev? {...prev, evals:j} : {evals:j, task_success:0, tool_accuracy:0, rag_accuracy:0, policy_compliance:0, guardrail_accuracy:0, escalation_accuracy:0}) }catch{ setErr('Backend not reachable') }
    setBusy(false)
  }
  useEffect(()=>{ load() },[])
  return (
    <div style={{borderTop:'1px solid #E8E8E3', padding:12}}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:8, marginBottom:10}}>
        <span style={{fontSize:12, fontWeight:600}}>Performance</span>
        <div style={{display:'flex', gap:6}}>
          <button onClick={load} className="g-btn g-btn-ghost" style={{height:28, padding:'0 10px', fontSize:12, border:'1px solid #E8E8E3'}} disabled={busy}>↻</button>
          <button onClick={runEvals} className="g-btn g-btn-primary" style={{height:28, padding:'0 10px', fontSize:12}} disabled={busy}>Run evals</button>
        </div>
      </div>
      {err && <div style={{color:'#8B0000', fontSize:12, marginBottom:8}}>{err}</div>}
      {!m ? <div style={{fontSize:12, color:'#9A9A9E'}}>Not loaded — sign in to view</div> : (
        <div style={{display:'grid', gap:8}}>
          {[
            ['Task Success', m.task_success],
            ['Tool Accuracy', m.tool_accuracy],
            ['RAG Accuracy', m.rag_accuracy],
            ['Policy Compliance', m.policy_compliance],
            ['Guardrail', m.guardrail_accuracy],
            ['Escalation', m.escalation_accuracy],
          ].map(([label,val])=>(
            <div key={label}>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:11, marginBottom:4}}><span style={{fontWeight:600}}>{label}</span><span style={{fontFamily:'var(--font-mono)'}}>{val??0}%</span></div>
              <div style={{height:6, background:'#F0F0EC', borderRadius:999, overflow:'hidden', border:'1px solid #E8E8E3'}}><div style={{width:`${val??0}%`, height:'100%', background:'#0F0F0F', borderRadius:999}}/></div>
            </div>
          ))}
          <div style={{fontSize:11, color:'#6E6E73', background:'#F6F6F3', border:'1px solid #E8E8E3', borderRadius:10, padding:'8px 10px', lineHeight:1.6}}>
            <div>{m.avg_latency??0}ms · {m.trace_count??0} traces · {m.blocked??0} blocked</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function App(){
  const [view,setView]=useState(()=> (location.hash.replace('#','')==='docs'?'docs': location.hash.replace('#','')==='chat'?'chat':'home'))
  const [auth,setAuth]=useState(()=> ({ token:getToken(), customerId:getStoredCustomer()}))
  const [showLogin,setShowLogin]=useState(false)
  const [authMode,setAuthMode]=useState('login')
  const [authForm,setAuthForm]=useState({ customer_id:'C102', name:'Alex Johnson', email:'alex@example.com', password:'password123' })
  const [authError,setAuthError]=useState('')
  const [trace,setTrace]=useState(null)
  const isAuthed=!!auth.token

  useEffect(()=>{ const h=()=>{ const v=location.hash.replace('#',''); if(['home','docs','chat'].includes(v)) setView(v) }; window.addEventListener('hashchange',h); return()=>window.removeEventListener('hashchange',h) },[])
  useEffect(()=>{ location.hash=view },[view])
  useEffect(()=>{ if(isAuthed) { fetch(api('/traces'),{headers:{...authHeaders()}}).then(r=>r.ok?r.json():null).then(t=>{ if(Array.isArray(t)&&t.length) setTrace(t.at(-1))}).catch(()=>{}) }},[isAuthed])

  function handleCTAClick(){ if(isAuthed) setView('chat'); else setShowLogin(true) }
  function logout(){ try{ localStorage.removeItem('token'); localStorage.removeItem('customer_id')}catch{}; setAuth({token:null, customerId:'C102'}); setView('home') }
  async function handleAuth(e){
    e?.preventDefault(); setAuthError('')
    const url=authMode==='register'?api('/auth/register'):api('/auth/login')
    const body=authMode==='register'
      ? { customer_id:authForm.customer_id.trim(), name:authForm.name.trim(), email:authForm.email.trim(), password:authForm.password }
      : { customer_id:authForm.customer_id.trim()||undefined, email:authForm.email.trim()||undefined, password:authForm.password }
    if(!body.password || body.password.length<6){ setAuthError('Password must be at least 6 characters'); return }
    if(authMode==='register' && (!body.customer_id || !body.name || !body.email)){ setAuthError('All fields required'); return }
    if(!body.customer_id && !body.email){ setAuthError('Provide customer_id or email'); return }
    try{
      const r=await fetch(url,{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      const j=await r.json().catch(()=>({})); if(!r.ok){ setAuthError(j.detail||`Auth failed (${r.status})`); return }
      const token=j.access_token; const cid=j.customer_id||body.customer_id
      try{ localStorage.setItem('token',token); localStorage.setItem('customer_id',cid)}catch{}
      setAuth({token, customerId:cid}); setShowLogin(false); setView('chat')
    }catch{ setAuthError('Backend not reachable. Run: python -m app.api.main') }
  }

  return (
    <div style={{minHeight:'100vh', background:'#fff'}}>
      <Topbar view={view} setView={setView} isAuthed={isAuthed} auth={auth} onLoginClick={()=>setShowLogin(true)} onLogout={logout} />
      {view==='home' && <Home isAuthed={isAuthed} onCTAClick={handleCTAClick} setView={setView} />}
      {view==='docs' && <Docs setView={setView} onCTAClick={handleCTAClick} />}
      {view==='chat' && (isAuthed ? <ChatView auth={auth} trace={trace} setTrace={setTrace} /> : (
        <div className="g-page" style={{padding:'64px 24px', textAlign:'center'}}>
          <div style={{maxWidth:440, margin:'0 auto', border:'1px solid #E8E8E3', borderRadius:20, padding:32, background:'#fff'}}>
            <div style={{width:36,height:36, borderRadius:10, background:'#0F0F0F', color:'#fff', display:'grid', placeItems:'center', margin:'0 auto'}}>◈</div>
            <h2 style={{fontFamily:'var(--font-display)', fontWeight:500, margin:'16px 0 8px'}}>Sign in to chat</h2>
            <p style={{color:'#6E6E73', fontSize:13, margin:0}}>Authentication is required — quiet and secure, like a premium product.</p>
            <button className="g-btn g-btn-primary" style={{marginTop:18, height:42, padding:'0 22px'}} onClick={()=>setShowLogin(true)}>Sign in</button>
            <button className="g-btn g-btn-ghost" style={{marginTop:10, display:'block', width:'100%'}} onClick={()=>setView('home')}>Back to home</button>
          </div>
        </div>
      ))}
      {view!=='chat' && (
        <footer className="g-page"><div className="g-footer"><span>© 2026 Support · Quiet, auditable support experience.</span><span>PII-guarded · Policy-enforced · Traceable</span></div></footer>
      )}
      {showLogin && <LoginModal mode={authMode} setMode={setAuthMode} form={authForm} setForm={setAuthForm} error={authError} onSubmit={handleAuth} onClose={()=>setShowLogin(false)} />}
    </div>
  )
}
