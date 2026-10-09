import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Nav } from "@/components/Nav";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Mesa paper",
    template: "%s · Mesa paper",
  },
  description:
    "Painel de paper trading spot da mesa de Bernardo Iannini. Simulação. Nenhuma ordem real.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <a className="skip" href="#conteudo">
          Ir para o conteúdo
        </a>
        <header className="top">
          <div>
            <p className="eyebrow">Paper trading · Bybit spot · BRT</p>
            <p className="title">Mesa de Bernardo Iannini</p>
          </div>
          <Nav />
        </header>
        <main id="conteudo">{children}</main>
        <footer>
          <p>Simulação. Isto não é recomendação de investimento. Nenhuma ordem real sai deste painel.</p>
        </footer>
      </body>
    </html>
  );
}
