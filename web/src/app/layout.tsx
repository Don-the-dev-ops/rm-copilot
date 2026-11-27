import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, IBM_Plex_Sans, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});

// Display face for the welcome heading: heavy, italic and slightly wide, in the
// spirit of the lettering on a metal card.
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  style: ["italic"],
  axes: ["wdth"],
});

export const metadata: Metadata = {
  title: {
    default: "RM Copilot | Iris Bank",
    template: "%s | RM Copilot",
  },
  description:
    "Who a relationship manager should call this morning, and what to say. A portfolio demo on synthetic data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en-ZA"
      className={`${plexSans.variable} ${plexMono.variable} ${sourceSerif.variable} ${archivo.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <a
          href="#main"
          className="sr-only z-50 rounded-md bg-navy px-3 py-2 text-sm text-white focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
