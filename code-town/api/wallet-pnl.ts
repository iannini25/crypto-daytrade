import { handleWalletPnl } from '../shared/wallet/server';

// Edge, não Node: o pacote é ESM e o compilador Node da Vercel sobe a função
// sem conseguir executá-la. Edge recebe o Response direto.
export const config = {
  runtime: 'edge',
};

export default function handler(): Promise<Response> {
  return handleWalletPnl();
}
