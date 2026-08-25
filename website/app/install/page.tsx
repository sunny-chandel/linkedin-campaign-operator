import type { Metadata } from 'next';
import { Footer, Header, PageHero } from '../components/Shell';

export const metadata: Metadata = {
  title: 'Install the LinkedIn Agent Skill for Claude Code and Codex',
  description: 'Install LinkedIn Campaign Operator in Claude Code or Codex and start a stateful LinkedIn content and engagement campaign.',
};

export default function InstallPage() {
  return <main><Header /><PageHero eyebrow="Install · Two platforms" title="Your campaign starts with two commands." lede="Add the marketplace, install the operator, and ask your agent to start. The first run discovers your profile and creates portable campaign state." />
    <section className="docs-grid">
      <article className="doc-card"><p className="eyebrow">Claude Code</p><h2>Install from the plugin marketplace</h2><pre><code>{`/plugin marketplace add sunny-chandel/linkedin-campaign-operator
/plugin install linkedin-campaign-operator-v3@sunny-linkedin-tools`}</code></pre><p>Then run <code>/linkedin-campaign-operator-v3:linkedin-campaign-orchestrator</code>.</p></article>
      <article className="doc-card"><p className="eyebrow">Codex</p><h2>Add the public marketplace</h2><pre><code>{`codex plugin marketplace add sunny-chandel/linkedin-campaign-operator
codex plugin add linkedin-campaign-operator-v3@linkedin-campaign-operator`}</code></pre><p>Open a new task and say: <strong>Start my LinkedIn growth campaign.</strong></p></article>
    </section>
    <section className="section"><p className="eyebrow">First prompt</p><blockquote>Start my LinkedIn growth campaign. Discover my profile, initialize campaign state, and execute the next valid stage.</blockquote><p className="section-lede">Want exact starting values? The initializer supports owner name, profile URL, timezone, niche, baselines, campaign ID, follower goal, and connection goal.</p></section>
    <Footer /></main>;
}
