import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Mirrors the alias mobile/ sets up in its own tsconfig/metro
      // config, so admin/ can consume the same shared domain types
      // (e.g. the Role union) without duplicating them.
      '@shared': path.resolve(import.meta.dirname, '../shared'),
    },
  },
})
