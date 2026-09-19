# Squelch documentation site

A [Docusaurus](https://docusaurus.io) site that **presents** the Markdown in [`../docs`](../docs). The content lives at the repository root so it also renders on GitHub; this folder is only the presentation layer.

Live site: https://kshesha1.github.io/Squelch/

```bash
npm install
npm start            # live-reloading dev server at http://localhost:3000/Squelch/
npm run build        # production build into build/ (fails on any broken link)
npm run serve        # serve the production build locally
```

Requires Node 20 or newer.

## Notes

- `docs/*.md` files are parsed as CommonMark (`markdown.format: 'detect'`), so they can contain `<`, `{` and similar characters. Admonitions (`:::note`) and Mermaid diagrams work; JSX and Tabs would need `.mdx`.
- The sidebar is explicit, in `sidebars.js`. A new page must be added there to appear.
- Deployment is `.github/workflows/docs.yml` (GitHub Pages via Actions).
