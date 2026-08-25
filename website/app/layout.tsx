import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://linkedin-campaign-operator.sunnychandel73.chatgpt.site'),
  title: {
    default: 'LinkedIn Agent Skill — LinkedIn Campaign Operator',
    template: '%s — LinkedIn Campaign Operator',
  },
  description:
    'A free, open-source LinkedIn agent skill for research, content production, engagement planning, analytics, and adaptive learning in Claude Code and Codex.',
  keywords: ['LinkedIn agent skill', 'LinkedIn content agent', 'Claude Code LinkedIn plugin', 'Codex LinkedIn plugin', 'open-source LinkedIn agent', 'LinkedIn engagement assistant'],
  authors: [{ name: 'Sunny Chandel', url: 'https://github.com/sunny-chandel' }],
  creator: 'Sunny Chandel',
  manifest: '/manifest.webmanifest',
  category: 'technology',
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    title: 'LinkedIn Campaign Operator',
    description: 'Your LinkedIn operating system. Inside your AI agent.',
    siteName: 'LinkedIn Campaign Operator',
    images: [{ url: '/og-card.png', width: 1536, height: 1024, alt: 'LinkedIn Campaign Operator system map' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'LinkedIn Campaign Operator',
    description: 'Your LinkedIn operating system. Inside your AI agent.',
    images: ['/og-card.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const software = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'LinkedIn Campaign Operator',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Claude Code, Codex',
    description: 'A free, open-source LinkedIn campaign operating system made from eight composable Agent Skills.',
    author: { '@type': 'Person', name: 'Sunny Chandel' },
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
    codeRepository: 'https://github.com/sunny-chandel/linkedin-campaign-operator',
    license: 'https://opensource.org/license/mit',
  };
  return <html lang="en"><body className={`${geistSans.variable} ${geistMono.variable}`}><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(software) }} />{children}</body></html>;
}
