import type { Metadata } from 'next';
import { Footer, Header, PageHero } from '../components/Shell';

export const metadata: Metadata = { title: 'Eight LinkedIn Agent Skills', description: 'Explore eight composable LinkedIn skills for campaign orchestration, research, writing, engagement, analytics, branding, GIFs, and feature routing.' };
const entries = [
  ['Campaign orchestrator', 'The governing layer for identity, state, routing, recovery, dispatch, and campaign completion.'],
  ['Content research', 'Finds timely topics, verifies claims, and produces source-backed briefs ready for production.'],
  ['Content production', 'Transforms research into captions, creative briefs, and validated publication packages.'],
  ['Engagement planning', 'Scores candidates and builds a queue around relevance, conversation probability, freshness, and learned performance.'],
  ['Analytics learning', 'Compares equal-age snapshots, records outcomes, and updates experiments and strategy weights.'],
  ['Brand system', 'Derives a reusable visual identity and watermark kit from the active LinkedIn profile.'],
  ['GIF creative intelligence', 'Studies references, scores patterns, and produces repeatable motion-creative specifications.'],
  ['Premium router', 'Inventories included LinkedIn capabilities and routes useful features into the campaign workflow.'],
];
export default function SkillsPage() { return <main><Header /><PageHero eyebrow="System map" title="Eight specialists. One operator." lede="Each skill owns one bounded part of the campaign and returns structured artifacts to the orchestrator." /><section className="detail-list">{entries.map(([name, description], i) => <article key={name}><span>{String(i + 1).padStart(2, '0')}</span><div><h2>{name}</h2><p>{description}</p></div></article>)}</section><Footer /></main>; }
