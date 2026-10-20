import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App.jsx'
import { loadBackendStatus } from '@/data/backend'
import '@/index.css'

// Pipeline data patches the mock modules in place, so it must land before the first render.
loadBackendStatus().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <App />
  )
})
