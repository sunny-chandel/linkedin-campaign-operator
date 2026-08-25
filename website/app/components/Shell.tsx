import Link from 'next/link';

export const githubUrl = 'https://github.com/sunny-chandel/linkedin-campaign-operator';

export function Header() {
  return (
    <nav className="nav-shell" aria-label="Primary navigation">
      <Link className="wordmark" href="/" aria-label="LinkedIn Campaign Operator home">
        <span className="wordmark-mark">LCO</span>
        <span>Campaign Operator</span>
      </Link>
      <div className="nav-links">
        <Link href="/skills">Skills</Link>
        <Link href="/examples">Examples</Link>
        <Link href="/docs">Docs</Link>
        <Link href="/press">Press</Link>
        <a className="nav-cta" href={githubUrl}>GitHub ↗</a>
      </div>
    </nav>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div>
        <span className="wordmark-mark">LCO</span>
        <p>Your LinkedIn operating system. Inside your AI agent.</p>
      </div>
      <div className="footer-links">
        <Link href="/install">Install</Link>
        <Link href="/skills">Skills</Link>
        <Link href="/examples">Examples</Link>
        <Link href="/docs">Docs</Link>
        <Link href="/press">Press</Link>
        <a href={githubUrl}>GitHub</a>
      </div>
      <p>Free and open source · MIT licensed · Built by Sunny Chandel</p>
    </footer>
  );
}

export function PageHero({ eyebrow, title, lede }: { eyebrow: string; title: string; lede: string }) {
  return (
    <section className="page-hero">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p className="hero-lede">{lede}</p>
    </section>
  );
}
