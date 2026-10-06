import { cell, type DeskRead, type Row } from "@/lib/desk";

export function DeskTable({
  read,
  columns,
  empty,
}: {
  read: DeskRead;
  columns: { key: string; label: string }[];
  empty: string;
}) {
  if (!read.configured) {
    return (
      <p className="note">
        Supabase ainda não está ligado. Defina <code>SUPABASE_URL</code> e <code>SUPABASE_ANON_KEY</code> no
        servidor (veja <code>docs/deploy.md</code>). Sem essas variáveis o painel não inventa saldo nem sinal.
      </p>
    );
  }
  if (read.error) {
    const rls = read.error === "42501" || read.error.startsWith("http_401") || read.error.startsWith("http_403");
    return (
      <p className="note">
        {rls
          ? "A leitura foi recusada (RLS ou GRANT). Isso é o padrão desta migração até você criar uma policy para o seu usuário."
          : `Não foi possível ler a tabela (${read.error}).`}
      </p>
    );
  }
  if (read.rows.length === 0) {
    return <p className="note">{empty}</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {read.rows.map((row, index) => (
            <tr key={rowKey(row, index)}>
              {columns.map((column) => (
                <td key={column.key}>{cell(row, column.key)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function rowKey(row: Row, index: number): string {
  const id = row.id ?? row.event_date ?? row.ts;
  return id === undefined || id === null ? `row-${index}` : String(id);
}
