import { handleWalletPnl } from '../shared/wallet/server';

export function GET(): Promise<Response> {
  return handleWalletPnl();
}
