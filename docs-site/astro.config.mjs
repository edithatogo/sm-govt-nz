import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import astroExpressiveCode from 'astro-expressive-code';
import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://edithatogo.github.io',
  base: '/sm-govt-nz/',
  integrations: [
    astroExpressiveCode(),
    mdx(),
    sitemap(),
    starlight({
      title: 'SM Govt NZ',
      description: 'Legal NZ documentation portal for SM Govt NZ.',
      sidebar: [
        { label: 'Start', items: ['index', 'docs-tooling-audit'] },
      ],
    }),
  ],
});
