import type { Metadata } from 'next';
import Link from 'next/link';
import { CopyCommand } from './components/CopyCommand';
import { Footer, Header, githubUrl } from './components/Shell';

const installCommand = 'git clone --depth 1 https://github.com/sunny-chandel/linkedin-campaign-operator.git';

export const metadata: Metadata = { title: 'Your LinkedIn Team in Claude', alternates: { canonical: '/' } };

const skills = [
  ['01', 'CAMPAIGN ORCHESTRATOR', '[STATEFUL]', 'IDENTITY, STATE, ROUTING, RECOVERY, DISPATCH, AND THE NEXT VALID CAMPAIGN ACTION.'],
  ['02', 'CONTENT RESEARCH', '[EVIDENCE]', 'FRESH TOPICS, PRIMARY SOURCES, VERIFIED CLAIMS, AND PRODUCTION-READY BRIEFS.'],
  ['03', 'CONTENT PRODUCTION', '[CREATIVE]', 'CAPTIONS, CREATIVE BRIEFS, HOOKS, AND VALIDATED PUBLICATION PACKAGES.'],
  ['04', 'ENGAGEMENT PLANNING', '[RANKED]', 'EVIDENCE-RANKED CONVERSATIONS BASED ON RELEVANCE, FRESHNESS, AND LEARNED PERFORMANCE.'],
  ['05', 'ANALYTICS LEARNING', '[ADAPTIVE]', 'EQUAL-AGE COMPARISONS, EXPERIMENTS, OUTCOMES, AND UPDATED STRATEGY WEIGHTS.'],
  ['06', 'BRAND SYSTEM', '[VISUAL]', 'A REUSABLE VISUAL IDENTITY AND WATERMARK KIT DERIVED FROM YOUR ACTIVE PROFILE.'],
  ['07', 'GIF INTELLIGENCE', '[MOTION]', 'REFERENCE-LED MOTION CONCEPTS, PATTERN SCORING, AND REPEATABLE CREATIVE SPECS.'],
  ['08', 'FEATURE ROUTER', '[LINKEDIN]', 'INVENTORIES AVAILABLE LINKEDIN CAPABILITIES AND ROUTES THEM INTO THE CAMPAIGN.'],
];

const commands = [
  ['/linkedin start', 'DISCOVER YOUR PROFILE, INITIALIZE STATE, AND EXECUTE THE NEXT VALID STAGE'],
  ['/linkedin research', 'FIND CURRENT, SOURCE-BACKED TOPICS FOR YOUR CONTENT PILLARS'],
  ['/linkedin produce', 'TURN APPROVED RESEARCH INTO PUBLICATION-READY PACKAGES'],
  ['/linkedin engage', 'BUILD A RANKED QUEUE OF USEFUL CONVERSATION OPPORTUNITIES'],
  ['/linkedin analyze', 'COMPARE EQUAL-AGE RESULTS AND UPDATE THE WORKING MODEL'],
  ['/linkedin resume', 'CONTINUE FROM THE LAST VERIFIED ACTION—WITHOUT RESTARTING'],
];

const faqs = [
  ['What is Claude LinkedIn?', 'Claude LinkedIn is the public interface for LinkedIn Campaign Operator: eight open-source Agent Skills that run a stateful organic LinkedIn campaign inside Claude Code and Codex.'],
  ['How do I install it?', 'Clone the repository or add the public plugin marketplace, install linkedin-campaign-operator-v3, then ask your agent to start your LinkedIn growth campaign.'],
  ['Does it remember previous sessions?', 'Yes. Campaign configuration, queues, analytics, experiments, logs, and verified actions live in portable JSON and JSONL state outside the versioned skill.'],
  ['Can I use only one part of the system?', 'Yes. You can run research, production, engagement, analytics, branding, or routing as bounded workflows while the orchestrator handles prerequisites.'],
  ['Does it work with Claude Code and Codex?', 'Yes. The repository includes plugin manifests and install paths for both Claude Code and Codex.'],
];

export default function Home() {
  return <main><Header />
    <section className="hero" id="hero">
      <span className="float-label float-a">RESEARCHER</span><span className="float-label float-b">WRITER</span><span className="float-label float-c">ENGAGER</span><span className="float-label float-d">ANALYST</span>
      <div className="hero-inner"><p className="release-badge"><strong>v1.1.0</strong> {'//'} LATEST {'//'} FREE {'//'} OPEN SOURCE</p><h1>YOUR LINKEDIN TEAM<br /><span>IN CLAUDE.</span></h1><p className="hero-lede">Claude LinkedIn is a free, open-source LinkedIn toolkit for Claude Code and Codex: 8 specialist skills, one stateful operator, and a campaign memory that continues between sessions.</p><p className="byline">By Sunny Chandel {'//'} Built for campaigns that learn</p><CopyCommand command={installCommand} /><p className="platform-note">WORKS WITH CLAUDE CODE + CODEX. {'//'} <Link href="/install">FULL INSTALL GUIDE</Link></p><p className="search-note">Also searched as Claude for LinkedIn, Claude LinkedIn agent, LinkedIn Claude skill, or LinkedIn AI agent.</p><div className="hero-actions"><a className="button button-outline" href={githubUrl}>★ OPEN SOURCE</a><a className="text-link" href="#demo">SEE DEMO</a><a className="text-link" href="#features">FEATURES</a><Link className="text-link" href="/docs">DOCS</Link></div></div>
    </section>
    <section className="section demo-section" id="demo"><p className="eyebrow">{'//'} SEE IT IN ACTION</p><h2>HOW DOES CLAUDE RUN A CAMPAIGN WITHOUT LOSING CONTEXT?</h2><p className="section-kicker">ONE SYSTEM. EIGHT SPECIALISTS. EVERY ACTION WRITTEN BACK TO SHARED CAMPAIGN STATE.</p><div className="terminal-demo"><div className="terminal-bar"><span>CLAUDE LINKEDIN {'//'} CAMPAIGN LIVE</span><span className="green">● ADAPTIVE</span></div><div className="terminal-body"><p><span>01</span> VERIFY PROFILE + CAMPAIGN STATE <b>DONE</b></p><p><span>02</span> RESEARCH CURRENT TOPICS <b>DONE</b></p><p><span>03</span> BUILD PUBLICATION PACKAGE <b className="coral">RUNNING</b></p><p><span>04</span> QUEUE ENGAGEMENT <b>READY</b></p><div className="terminal-result"><small>CURRENT STAGE</small><strong>RESEARCH → PRODUCTION</strong><em>Evidence-ranked topic selected. Campaign memory updated.</em></div></div></div></section>
    <section className="section" id="install"><p className="eyebrow">{'//'} INSTALL</p><h2>HOW DO YOU INSTALL AND RUN CLAUDE LINKEDIN?</h2><div className="steps-grid"><article><span>01</span><h3>Clone</h3><code>git clone --depth 1 github.com/sunny-chandel/linkedin-campaign-operator.git</code></article><article><span>02</span><h3>Install</h3><code>/plugin marketplace add sunny-chandel/linkedin-campaign-operator</code></article><article><span>03</span><h3>Start</h3><code>Start my LinkedIn growth campaign.</code><p>Claude discovers your profile, initializes state, and routes the first valid stage.</p></article></div></section>
    <section className="stats-band" aria-label="Product facts"><div><strong>8</strong><span>SPECIALIST<br />SKILLS</span></div><div><strong>1</strong><span>SHARED<br />MEMORY</span></div><div><strong>2</strong><span>AGENT<br />PLATFORMS</span></div><div><strong>20</strong><span>PASSING<br />TESTS</span></div><div><strong>$0</strong><span>FREE<br />FOREVER</span></div></section>
    <section className="section" id="features"><p className="eyebrow">{'//'} WHAT IT COVERS</p><h2>WHAT LINKEDIN SKILLS ARE INCLUDED?</h2><div className="feature-list">{skills.map(([number,name,tag,description]) => <Link href="/skills" className="feature-row" key={number}><span>{number}</span><strong>{name}</strong><em>{tag}</em><p>{description}</p></Link>)}</div></section>
    <section className="section commands-section" id="skills"><p className="eyebrow">{'//'} CORE WORKFLOWS</p><h2>ASK CLAUDE. PICK YOUR WORKFLOW.</h2><div className="command-list">{commands.map(([command,description]) => <div key={command}><code>{command}</code><span>{description}</span></div>)}</div></section>
    <section className="section continuity-section"><p className="eyebrow">{'//'} HOW CONTINUITY WORKS</p><h2>START TODAY. RESUME TOMORROW.</h2><div className="continuity-grid"><article><strong>01</strong><h3>READ</h3><p>LOAD PROFILE, GOALS, QUEUES, EXPERIMENTS, AND THE LAST VERIFIED ACTION.</p></article><article><strong>02</strong><h3>ROUTE</h3><p>AUDIT WHAT IS MISSING AND CHOOSE THE HIGHEST-PRIORITY READY WORK.</p></article><article><strong>03</strong><h3>WRITE BACK</h3><p>STORE ARTIFACTS, EVIDENCE, OUTCOMES, AND THE NEXT RESUMABLE STATE.</p></article></div></section>
    <section className="section faq-section" id="faq"><p className="eyebrow">{'//'} FAQ</p><h2>QUESTIONS PEOPLE ASK</h2><div className="faq-list">{faqs.map(([q,a],index) => <details key={q} open={index===0}><summary>{q}<span>+</span></summary><p>{a}</p></details>)}</div></section>
    <section className="pitch-section"><p className="eyebrow">[THE PITCH]</p><h2>YOU ALREADY HAVE<br /><span>CLAUDE OPEN.</span></h2><p>Eight specialist skills. One shared campaign memory. The install takes two commands. The operator handles what comes next.</p><div className="hero-actions"><Link className="button button-primary" href="/install">COPY THE INSTALL COMMAND</Link><a className="button button-outline" href={githubUrl}>EXPLORE GITHUB →</a></div></section>
    <section className="about-section" aria-label="About Claude LinkedIn"><p className="eyebrow">{'//'} ABOUT CLAUDE LINKEDIN</p><h2>AN OPEN-SOURCE LINKEDIN OPERATING SYSTEM FOR AI AGENTS.</h2><p>Claude LinkedIn coordinates research, content production, engagement planning, analytics learning, brand systems, motion creative, and LinkedIn feature routing. Versioned instructions stay separate from mutable campaign learning, so the system can improve without erasing what your campaign already knows.</p><p>Built by Sunny Chandel. Source, documentation, tests, examples, and releases are available on <a href={githubUrl}>GitHub</a>.</p></section>
    <Footer />
  </main>;
}
