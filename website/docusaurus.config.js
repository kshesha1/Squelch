// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

const REPO = 'https://github.com/kshesha1/Squelch';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Squelch',
  tagline: 'Do your agent skills actually work together?',
  favicon: 'img/favicon.svg',

  url: 'https://kshesha1.github.io',
  baseUrl: '/Squelch/',
  organizationName: 'kshesha1',
  projectName: 'Squelch',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'warn',

  markdown: {
    // .md files are plain CommonMark (the project docs contain <, {, and
    // similar characters that MDX would try to parse as JSX); .mdx stays MDX.
    format: 'detect',
    mermaid: true,
    hooks: {onBrokenMarkdownLinks: 'throw'},
  },
  themes: [
    '@docusaurus/theme-mermaid',
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        docsDir: '../docs',
        indexBlog: false,
        docsRouteBasePath: '/docs',
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        // The docs live at the repository root so they render on GitHub too;
        // this site is only the presentation layer.
        docs: {
          path: '../docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.js',
          editUrl: `${REPO}/edit/main/docs/`,
        },
        blog: false,
        theme: {customCss: './src/css/custom.css'},
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {defaultMode: 'dark', respectPrefersColorScheme: true},
      navbar: {
        title: 'Squelch',
        logo: {alt: 'Squelch logo', src: 'img/logo.svg'},
        items: [
          {type: 'docSidebar', sidebarId: 'docs', position: 'left', label: 'Docs'},
          {to: '/docs/results/pilot-001', label: 'Results', position: 'left'},
          {to: '/docs/roadmap', label: 'Roadmap', position: 'left'},
          {href: REPO, label: 'GitHub', position: 'right'},
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Learn',
            items: [
              {label: 'What is Squelch?', to: '/docs/intro'},
              {label: 'Quickstart', to: '/docs/getting-started/quickstart'},
              {label: 'Core concepts', to: '/docs/concepts/core-ideas'},
            ],
          },
          {
            title: 'Evidence',
            items: [
              {label: 'Pilot results', to: '/docs/results/pilot-001'},
              {label: 'Methodology', to: '/docs/methodology'},
              {label: 'Prior art', to: '/docs/prior-art'},
            ],
          },
          {
            title: 'Project',
            items: [
              {label: 'GitHub', href: REPO},
              {label: 'Roadmap', to: '/docs/roadmap'},
              {label: 'Contributing', to: '/docs/contributing'},
            ],
          },
        ],
        copyright: `Squelch is Apache-2.0 licensed. Work in progress: no validated research finding yet.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'yaml', 'json', 'python', 'diff'],
      },
      mermaid: {theme: {light: 'neutral', dark: 'dark'}},
    }),
};

export default config;
