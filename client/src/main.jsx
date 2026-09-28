import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(p){ super(p); this.state={ hasError:false, error:null } }
  static getDerivedStateFromError(e){ return { hasError:true, error:e } }
  componentDidCatch(e, info){ console.error('UI error', e, info) }
  render(){
    if(this.state.hasError) return <div style={{padding:32, fontFamily:'system-ui'}}><h2>Something went wrong</h2><pre style={{whiteSpace:'pre-wrap', background:'#fef2f2', padding:12, borderRadius:8}}>{String(this.state.error)}</pre><button onClick={()=>location.reload()} style={{marginTop:12, padding:'8px 14px'}}>Reload</button></div>
    return this.props.children
  }
}

createRoot(document.getElementById('root')).render(<React.StrictMode><ErrorBoundary><App /></ErrorBoundary></React.StrictMode>)
