import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Configuração isolada do frontend FleetLab. Nada aqui lê arquivos fora de `frontend/`.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { host: '127.0.0.1', port: 5173 },
  preview: { host: '127.0.0.1', port: 4173 },
  build: {
    target: 'es2022',
    // MapLibre, deck.gl e ECharts só entram por páginas carregadas sob demanda, então ficam fora do
    // pacote inicial sem divisão manual; o limite reflete o tamanho dessas bibliotecas.
    chunkSizeWarningLimit: 1800,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
    // Testes nunca dependem dos dados reais servidos localmente, mesmo com `.env.local` em modo http.
    env: { VITE_DATA_SOURCE: 'mock' },
  },
})
