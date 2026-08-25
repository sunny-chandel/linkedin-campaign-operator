import type { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'https://linkedin-campaign-operator.sunnychandel73.chatgpt.site';
  return ['', '/install', '/skills', '/examples', '/docs', '/press', '/blog/launch'].map((path, index) => ({
    url: `${base}${path}`,
    lastModified: new Date(),
    changeFrequency: index === 0 ? 'weekly' : 'monthly',
    priority: index === 0 ? 1 : path === '/install' ? 0.9 : 0.7,
  }));
}
