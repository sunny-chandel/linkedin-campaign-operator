import type { Metadata } from 'next';
import { Footer, Header, PageHero } from '../components/Shell';

export const metadata: Metadata = { title: 'Claude LinkedIn Examples and Prompts', description: 'Copy practical LinkedIn agent prompts for founders, technical professionals, consultants, content creation, engagement, and analytics.', alternates: { canonical: '/examples' } };
const examples = [
  ['Solo founder', 'Research two current topics at the intersection of AI agents and developer tools. Prepare one practical post and one opinionated post.'],
  ['Technical professional', 'Review my recent posts, identify the strongest content pillar at equal post age, and update the next two publication packages.'],
  ['Consultant', 'Build an engagement queue around data platform leaders. Prioritize posts where a specific, useful reply can start a real conversation.'],
  ['Campaign operator', 'Audit the campaign, recover incomplete analytics, refresh the adaptive reserve, and execute the highest-priority ready work.'],
  ['Content-only workflow', 'Use research and production only. Give me two source-backed LinkedIn packages and do not publish them.'],
  ['Resume and learn', 'Resume from the last verified state, compare the latest analytics snapshots, and choose the next best campaign action.'],
];
export default function ExamplesPage() { return <main><Header /><PageHero eyebrow="Copy and run" title="Prompts for real LinkedIn workflows." lede="Start with one clear outcome. The operator handles the prerequisite skills, state, and routing." /><section className="example-grid">{examples.map(([name, prompt]) => <article className="example-card" key={name}><h2>{name}</h2><blockquote>{prompt}</blockquote></article>)}</section><Footer /></main>; }
