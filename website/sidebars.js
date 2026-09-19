// @ts-check
/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'intro',
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: [
        'getting-started/installation',
        'getting-started/quickstart',
        'getting-started/live-local-runs',
      ],
    },
    {
      type: 'category',
      label: 'Concepts',
      items: [
        'concepts/core-ideas',
        'concepts/experiment-design',
        'concepts/status-vs-quality',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/runner',
        'architecture/tools-and-sandbox',
        'architecture/evaluation',
        'architecture/backends',
        'architecture/campaigns',
        'architecture/analysis',
        'architecture/reporting',
        'architecture/data-contracts',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/write-a-skill',
        'guides/write-a-task',
        'guides/write-a-campaign',
        'guides/read-results',
        'guides/preregistration',
        'guides/troubleshooting',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/cli',
        'reference/campaign-config',
        'reference/fixtures',
        'reference/artifacts',
        'reference/agent-skills-compat',
      ],
    },
    {
      type: 'category',
      label: 'Research',
      items: [
        'methodology',
        'results/pilot-001',
        'weekly/week-01',
        'decisions/phase-01-checklist',
        'history-rewrite',
      ],
    },
    'roadmap',
    'prior-art',
    'contributing',
  ],
};

export default sidebars;
