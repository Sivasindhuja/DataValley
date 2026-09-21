import { useState } from 'react'

export default function App(){
  const [messages,setMessages]=useState([{role:'agent', text:'Hi! I am your Guardrailed Support Agent. I can help with orders, refunds, products, and tickets. How can I help?'}])
  const [input,setInput]=useState('')
  const [customer,setCustomer]=useState('C102')
  const [trace,setTrace]=useState(null)
  const [loading,setLoading]=useState(false)

  async function send(){
    if(!input.trim()) return
    const userMsg={role:'user', text:input}
    setMessages(m=>[...m, userMsg])
    setLoading(true)
    try{
      const r=await fetch('http://localhost:8000/chat',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:input, customer_id:customer})})
      const data=await r.json()
      setMessages(m=>[...m, {role:'agent', text:data.response, tools:data.tools_used, docs:data.docs}])
      const t=await fetch('http://localhost:8000/traces')
      const traces=await t.json()
      setTrace(traces.at(-1))
    }catch(e){
      setMessages(m=>[...m, {role:'agent', text:'Backend not reachable. Run: python -m app.api.main'}])
    }
    setLoading(false)
    setInput('')
  }
  return (
    <div style={{fontFamily:'system-ui', maxWidth:1150, margin:'0 auto', padding:20, display:'grid', gridTemplateColumns:'1fr 380px', gap:20}}>
      <div>
        <h2>Guardrailed AI Customer Support Agent</h2>
        <div style={{fontSize:12, color:'#666'}}>LLM decides what it wants to do; deterministic policy decides if allowed</div>
        <div style={{margin:'10px 0'}}>
          <label>Customer: </label>
          <select value={customer} onChange={e=>setCustomer(e.target.value)}>
            <option value="C102">C102 - Alex Johnson (SHIPPED #123, PENDING #124)</option>
            <option value="C103">C103 - Priya Singh (DELIVERED #125)</option>
            <option value="C104">C104 - Locked account</option>
          </select>
        </div>
        <div style={{border:'1px solid #ddd', borderRadius:8, height:420, overflowY:'auto', padding:12, background:'#fafafa'}}>
          {messages.map((m,i)=><div key={i} style={{margin:'8px 0', textAlign: m.role==='user'?'right':'left'}}>
            <div style={{display:'inline-block', background:m.role==='user'?'#007aff':'white', color:m.role==='user'?'white':'black', padding:'8px 12px', borderRadius:12, maxWidth:'80%', border:'1px solid #ddd', whiteSpace:'pre-wrap'}}>{m.text}</div>
            {m.tools && <div style={{fontSize:10, color:'#888'}}>Tools: {m.tools.join(', ')} | Docs: {m.docs?.join(', ')}</div>}
          </div>)}
          {loading && <div style={{color:'#888'}}>Thinking...</div>}
        </div>
        <div style={{display:'flex', gap:8, marginTop:10}}>
          <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder="e.g., My order #123 hasn't arrived. Can you check and cancel?" style={{flex:1, padding:10, borderRadius:8, border:'1px solid #ccc'}}/>
          <button onClick={send} style={{padding:'10px 18px', background:'#007aff', color:'white', border:'none', borderRadius:8}}>Send</button>
        </div>
        <div style={{marginTop:8, display:'flex', gap:6, flexWrap:'wrap'}}>
          {["My order #123 hasn't arrived. Can you check?","Can you cancel order #123?","Update delivery address for order #124 to 99 New Ave","Why hasn't my refund R421 arrived?","What's the warranty for product-a?","I want to speak to a human"].map(s=>(
            <button key={s} onClick={()=>setInput(s)} style={{fontSize:11, padding:'4px 8px', borderRadius:12, border:'1px solid #ccc', background:'white'}}>{s}</button>
          ))}
        </div>
      </div>
      <div>
        <h3>Observability / Trace</h3>
        <div style={{border:'1px solid #ddd', borderRadius:8, padding:10, fontSize:12, background:'#fff', height: 420, overflowY:'auto'}}>
          {!trace ? <div style={{color:'#888'}}>No trace yet. Send a message.</div> :
            <div>
              <div><b>Trace:</b> {trace.trace_id} | {trace.timestamp}</div>
              <div><b>Latency:</b> {trace.latency_ms}ms | <b>Cost:</b> ${trace.cost_usd} | <b>Customer:</b> {trace.customer_id}</div>
              <hr/>
              {trace.steps?.map((s,i)=><div key={i} style={{marginBottom:8, padding:6, background: s.safe?'#f0fff0':'#fff0f0', borderRadius:6}}>
                <b>{s.name}</b> {s.safe?'✓':'✗'}<pre style={{whiteSpace:'pre-wrap', fontSize:11, margin:0}}>{JSON.stringify(s.data,null,2).slice(0,600)}</pre>
              </div>)}
            </div>
          }
        </div>
        <Metrics />
      </div>
    </div>
  )
}
function Bar({label, value, color}){
  return <div style={{margin:'6px 0'}}>
    <div style={{display:'flex', justifyContent:'space-between', fontSize:11}}><span>{label}</span><span>{value}%</span></div>
    <div style={{background:'#eee', borderRadius:6, height:10}}><div style={{width:`${value}%`, background:color, height:10, borderRadius:6}}></div></div>
  </div>
}
function Metrics(){
  const [m,setM]=useState(null)
  async function load(){
    try{ const r=await fetch('http://localhost:8000/dashboard'); setM(await r.json()) }catch{}
  }
  async function runEvals(){
    try{ const r=await fetch('http://localhost:8000/evals/run'); const j=await r.json(); alert('Evals: '+Object.keys(j).length+' suites'); setM(prev=>({...prev, evals:j})) }catch{}
  }
  return <div style={{marginTop:12, border:'1px solid #ddd', borderRadius:8, padding:10, background:'#fff'}}>
    <div style={{display:'flex', gap:6, marginBottom:8}}>
      <button onClick={load} style={{fontSize:11, padding:'6px 10px', background:'#007aff', color:'white', border:'none', borderRadius:6}}>Refresh Metrics</button>
      <button onClick={runEvals} style={{fontSize:11, padding:'6px 10px', background:'#28a745', color:'white', border:'none', borderRadius:6}}>Run Evals</button>
    </div>
    {!m ? <div style={{fontSize:11, color:'#888'}}>Click refresh - shows Task Success, Tool Accuracy, RAG, Policy Compliance, Guardrail, Escalation per spec §20</div> :
      <div>
        <div style={{fontSize:12, fontWeight:600, marginBottom:6}}>Agent Performance §20</div>
        <Bar label="Task Success" value={m.task_success} color="#007aff"/>
        <Bar label="Tool Accuracy" value={m.tool_accuracy} color="#28a745"/>
        <Bar label="RAG Accuracy" value={m.rag_accuracy} color="#ffc107"/>
        <Bar label="Policy Compliance" value={m.policy_compliance} color="#6f42c1"/>
        <Bar label="Guardrail Accuracy" value={m.guardrail_accuracy} color="#fd7e14"/>
        <Bar label="Escalation Accuracy" value={m.escalation_accuracy} color="#dc3545"/>
        <div style={{fontSize:11, marginTop:8, background:'#f6f6f6', padding:6, borderRadius:6}}>
          <div><b>Operational:</b> avg latency {m.avg_latency}ms | traces {m.trace_count} | blocked {m.blocked} | escalations {m.escalations}</div>
          <div><b>Safety:</b> PII detections {m.metrics?.pii_detections} | output blocked {m.metrics?.output_blocked}</div>
          <div><b>Tokens/Cost:</b> {m.metrics?.responses} responses | cost ~${(m.trace_count*0.0001).toFixed(4)}</div>
        </div>
        <details style={{marginTop:6}}><summary style={{fontSize:11}}>Raw JSON</summary><pre style={{fontSize:10, background:'#f6f6f6', padding:6, borderRadius:6, maxHeight:200, overflow:'auto'}}>{JSON.stringify(m,null,2).slice(0,2000)}</pre></details>
      </div>
    }
  </div>
}
