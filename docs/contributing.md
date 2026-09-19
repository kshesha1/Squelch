---
title: Contributing
---

# Contributing

Squelch is an experimental project and small contributions are welcome. The most valuable one is **a real pair of skills you'd bet would fight**, with a task that shows it.

## Set up

```bash
git clone https://github.com/kshesha1/Squelch.git
cd Squelch
uv sync
uv run pytest -m "not docker"
uv run ruff check .
```

## Ground rules

- **Tests for failure paths, not just the happy path.** Squelch's value is that it fails toward `invalid`, never toward a fake result. New code that can fail should have a test that makes it fail.
- **Never invent results.** Missing credentials or compute don't block offline progress; report the remaining live step instead.
- **Label the evidence stage** (`scripted`, `screening`, `confirmation`) on anything you claim, and keep constructed fixtures labelled as constructed.
- **Don't commit `.squelch/`.** Publish only selected, redacted bundles under `examples/`, and check them for local paths and identifiers first.
- **Editing a skill changes its identity.** If a published result used it, the result no longer matches the file. Prefer adding a new skill over editing one that results depend on.

## Common contributions

| To add | Start here |
|---|---|
| a skill fixture | [Write a skill](./guides/write-a-skill.md) |
| a task and grader | [Write a task](./guides/write-a-task.md) (include a hidden reference solution) |
| an experiment | [Write a campaign](./guides/write-a-campaign.md) and a preregistration |
| a backend | [Backends](./architecture/backends.md#adding-another-backend) |

## Docs

The documentation is Markdown in `docs/`, presented by a Docusaurus site in `website/`:

```bash
cd website
npm install
npm start          # live-reloading dev server
npm run build      # production build; fails on broken links
```

Pages under `docs/` render on GitHub too, so write them as plain Markdown.

## Licence

Apache-2.0. Third-party skill and fixture licences are tracked separately and don't inherit the project licence.
