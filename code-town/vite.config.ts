import { defineConfig, type Plugin } from 'vite';
import { fileURLToPath } from 'node:url';

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

function walletApi(): Plugin {
  return {
    name: 'wallet-pnl-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = req.url?.split('?')[0];
        if (path !== '/api/wallet-pnl') return next();
        void (async () => {
          try {
            const mod = (await server.ssrLoadModule(r('./shared/wallet/server.ts'))) as { handleWalletPnl: () => Promise<Response> };
            const response = await mod.handleWalletPnl();
            res.statusCode = response.status;
            response.headers.forEach((value, key) => res.setHeader(key, value));
            res.end(Buffer.from(await response.arrayBuffer()));
          } catch (error) {
            res.statusCode = 500;
            res.setHeader('content-type', 'text/plain; charset=utf-8');
            res.end(error instanceof Error ? error.message : 'erro');
          }
        })();
      });
    },
  };
}

// Cliente do Habblaud como site estático (Vercel). Os dados vêm do Supabase no navegador
// (client/src/grok/source.ts); ?mock=1 mantém a simulação original do Habblaud.
// /api/wallet-pnl é a função serverless; no dev o plugin abaixo serve a mesma conta.
export default defineConfig({
  root: r('./client'),
  publicDir: r('./client/public'),
  envDir: r('.'),
  envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
  plugins: [walletApi()],
  build: {
    outDir: r('./dist'),
    emptyOutDir: true,
    assetsDir: 'bundle',
    assetsInlineLimit: 0,
    rollupOptions: { input: { main: r('./client/index.html') } },
  },
  server: { port: 5173, host: true, fs: { allow: [r('.'), r('./client'), r('./shared')] } },
});
