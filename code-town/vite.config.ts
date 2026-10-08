import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

// Cliente do Habblaud como site estático (Vercel). Os dados vêm do Supabase no navegador
// (client/src/grok/source.ts); ?mock=1 mantém a simulação original do Habblaud.
export default defineConfig({
  root: r('./client'),
  publicDir: r('./client/public'),
  envDir: r('.'),
  envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
  build: {
    outDir: r('./dist'),
    emptyOutDir: true,
    assetsDir: 'bundle',
    assetsInlineLimit: 0,
    rollupOptions: { input: { main: r('./client/index.html') } },
  },
  server: { port: 5173, host: true },
});
