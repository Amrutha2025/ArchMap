import React, { useEffect, useState } from 'react'

const apiBase = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [status, setStatus] = useState<string>('loading...')
  const [apiUrl] = useState<string>(apiBase)

  useEffect(() => {
    fetch(`${apiBase}/health`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status}`)
        const data = await r.json()
        setStatus(JSON.stringify(data))
      })
      .catch((e) => setStatus(`error: ${String(e)}`))
  }, [])

  return (
    <div style={{ fontFamily: 'Inter, system-ui, Arial', padding: 24 }}>
      <h1>ArchMap Frontend</h1>
      <p>
        Backend URL: <code>{apiUrl}</code>
      </p>
      <p>
        Health check: <code>{status}</code>
      </p>
      <p>
        Try the API docs: <a href={`${apiBase}/docs`} target="_blank">{`${apiBase}/docs`}</a>
      </p>
    </div>
  )
}
