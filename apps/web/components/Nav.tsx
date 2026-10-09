"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  ["/", "Início"],
  ["/ledger", "Livro"],
  ["/posicao", "Posição"],
  ["/sinal", "Sinal"],
  ["/risco", "Risco"],
] as const;

export function Nav() {
  const path = usePathname();
  return (
    <nav aria-label="Seções da mesa">
      {links.map(([href, label]) => {
        const current = href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link key={href} href={href} aria-current={current ? "page" : undefined}>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
