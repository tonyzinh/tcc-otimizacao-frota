import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'
import './styles/globals.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { App } from './App'
import { createDefaultDataSource } from './services'

const root = document.getElementById('root')
if (!root) throw new Error('Elemento #root ausente')

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <App dataSource={createDefaultDataSource()} />
    </BrowserRouter>
  </StrictMode>,
)
