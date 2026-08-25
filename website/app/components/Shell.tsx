import Link from 'next/link';

export const githubUrl = 'https://github.com/sunny-chandel/linkedin-campaign-operator';

export function Header() {
  return <header className="site-header"><nav className="nav-shell" aria-label="Primary navigation">
    <Link className="wordmark" href="/" aria-label="Claude LinkedIn home"><span className="wordmark-mark" />CLAUDE LINKEDIN</Link>
    <div className="nav-links"><Link href="/#demo">DEMO</Link><Link href="/#features">FEATURES</Link><Link href="/skills">SKILLS</Link><Link href="/examples">EXAMPLES</Link><Link href="/docs">DOCS</Link><Link href="/#faq">FAQ</Link></div>
    <a className="github-mark" href={githubUrl} aria-label="Claude LinkedIn on GitHub">GH</a>
  </nav></header>;
}

export function Footer() {
  return <footer className="footer">
    <p>CLAUDE LINKEDIN V1.1.0 {'//'} FREE + OPEN SOURCE {'//'} BUILT BY <a href="https://github.com/sunny-chandel">SUNNY CHANDEL</a></p>
    <div className="footer-links"><Link href="/install">INSTALL</Link><Link href="/skills">SKILLS</Link><Link href="/examples">EXAMPLES</Link><Link href="/docs">DOCS</Link><Link href="/press">PRESS</Link><a href={githubUrl}>GITHUB</a><a href="/llms.txt">LLMS.TXT</a></div>
  </footer>;
}

export function PageHero({ eyebrow, title, lede }: { eyebrow: string; title: string; lede: string }) {
  return <section className="page-hero"><p className="eyebrow">{'//'} {eyebrow}</p><h1>{title}</h1><p className="hero-lede">{lede}</p></section>;
}
