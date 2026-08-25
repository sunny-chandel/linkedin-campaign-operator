import Link from 'next/link';
import { Footer, Header, githubUrl } from './components/Shell';

const installCommand = 'codex plugin marketplace add sunny-chandel/linkedin-campaign-operator';

const skills = [
  ['01', 'Orchestrate', 'State, routing, recovery, and the next best campaign action.'],
  ['02', 'Research', 'Fresh topics, primary sources, and defensible claims.'],
  ['03', 'Produce', 'Posts, creative briefs, and validated publication packages.'],
  ['04', 'Engage', 'Evidence-ranked opportunities for useful conversations.'],
  ['05', 'Learn', 'Equal-age analytics, experiments, and runtime learning.'],
  ['06', 'Brand', 'A reusable visual identity derived from your profile.'],
  ['07', 'Create GIFs', 'Reference-led motion concepts and pattern intelligence.'],
  ['08', 'Route features', 'Make better use of the LinkedIn capabilities you already have.'],
];

export default function Home() {
  return (
    <main>
      <Header />

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Free · Open source · Agent-native</p>
          <h1>Your LinkedIn operating system. Inside your AI agent.</h1>
          <p className="hero-lede">
            Research, create, schedule, engage, measure, and learn through one
            adaptive campaign skill for Claude Code and compatible agents.
          </p>

          <div className="hero-actions" id="install">
            <Link className="button button-primary" href="/install">
              Install free
            </Link>
            <a className="button button-secondary" href="#system">See the system</a>
          </div>

          <div className="install-line" aria-label="Installation command">
            <span>$</span>
            <code>{installCommand}</code>
          </div>
        </div>

        <div className="operator-card" aria-label="Campaign operating system preview">
          <div className="operator-topline">
            <span>CAMPAIGN / LIVE</span>
            <span className="status-dot">ADAPTIVE</span>
          </div>
          <div className="operator-stage">
            <p>Current stage</p>
            <strong>Research → Production</strong>
            <span>Evidence-ranked topic selected</span>
          </div>
          <div className="operator-grid">
            <div><span>08</span><p>composable skills</p></div>
            <div><span>24h</span><p>adaptive dispatch</p></div>
            <div><span>01</span><p>shared memory</p></div>
            <div><span>∞</span><p>learning loop</p></div>
          </div>
          <div className="operator-log">
            <p><span>01</span> Verify profile and campaign state</p>
            <p><span>02</span> Research current, source-backed topics</p>
            <p><span>03</span> Build the next publication package</p>
          </div>
        </div>
      </section>

      <section className="system-strip" id="system" aria-label="System capabilities">
        <span>RESEARCH</span><span>CREATE</span><span>ENGAGE</span><span>MEASURE</span><span>LEARN</span>
      </section>

      <section className="section section-intro">
        <p className="eyebrow">Not another post generator</p>
        <h2>One campaign. Eight specialist skills. Shared memory.</h2>
        <p className="section-lede">The operator remembers what happened, audits what is missing, and routes the next useful stage. Instructions stay versioned. Your campaign learning stays portable and inspectable.</p>
      </section>

      <section className="skill-grid" aria-label="Eight Agent Skills">
        {skills.map(([number, name, description]) => (
          <article className="skill-card" key={number}>
            <span>{number}</span>
            <h3>{name}</h3>
            <p>{description}</p>
          </article>
        ))}
      </section>

      <section className="split-section">
        <div>
          <p className="eyebrow">Built to continue</p>
          <h2>Start today. Resume tomorrow. Keep the learning.</h2>
        </div>
        <div className="flow-list">
          <p><span>01</span> Read the profile and initialize campaign state.</p>
          <p><span>02</span> Research, create, and validate the next packages.</p>
          <p><span>03</span> Rank engagement and publication opportunities.</p>
          <p><span>04</span> Measure results and update the working model.</p>
          <p><span>05</span> Resume from the last verified action.</p>
        </div>
      </section>

      <section className="proof-band">
        <div><strong>8</strong><span>composable skills</span></div>
        <div><strong>2</strong><span>agent platforms</span></div>
        <div><strong>15+</strong><span>acceptance tests</span></div>
        <div><strong>MIT</strong><span>free and open source</span></div>
      </section>

      <section className="cta-section">
        <p className="eyebrow">One command away</p>
        <h2>Put the whole campaign inside your agent.</h2>
        <div className="hero-actions">
          <Link className="button button-primary" href="/install">Install the operator</Link>
          <a className="button button-secondary" href={githubUrl}>Explore on GitHub ↗</a>
        </div>
      </section>

      <Footer />
    </main>
  );
}
