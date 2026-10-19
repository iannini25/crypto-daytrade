// Salas fixas da mesa. O id vira `grok:<id>` no snapshot.
// A planta (desk-floor.ts) posiciona cada uma em volta do escritório do Chefe.

export interface DeskSector {
  id: string;
  name: string;
}

export const DESK_SECTORS: DeskSector[] = [
  { id: 'pumpfun', name: 'PumpFun Analista' },
  { id: 'monitor-x', name: 'Monitor X' },
  { id: 'trending', name: 'Monitor Trending' },
  { id: 'cacador', name: 'Caçador Memecoins' },
  { id: 'whales', name: 'Holders e Carteira' },
  { id: 'chefe', name: 'Trader Crypto - Chefe' },
  { id: 'risk', name: 'Risco Memecoins' },
  { id: 'stats', name: 'Estatística Memecoins' },
  { id: 'talk', name: 'Sala de Reunião · Core' },
  { id: 'library', name: 'Sala de Estudos' },
  { id: 'conferencia', name: 'Conferência de Dados' },
];
