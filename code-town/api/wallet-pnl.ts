import { handleWalletPnl } from '../shared/wallet/server';

// /api numa app Vite usa o handler Node (req, res). `export function GET`
// é convenção do Next e a função sobe sem handler — a Vercel responde 500 na hora.
export const config = {
  maxDuration: 60,
};

interface NodeRes {
  statusCode: number;
  setHeader(name: string, value: string): void;
  end(body: string): void;
}

export default async function handler(_req: unknown, res: NodeRes): Promise<void> {
  const response = await handleWalletPnl();
  res.statusCode = response.status;
  response.headers.forEach((value, key) => {
    res.setHeader(key, value);
  });
  res.end(await response.text());
}
