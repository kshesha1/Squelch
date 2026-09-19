import React from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

function Wave() {
  // A noisy channel that settles into a clean signal: the squelch idea.
  return (
    <svg className={styles.wave} viewBox="0 0 640 120" role="img"
         aria-label="A noisy signal settling into a clean one">
      <path d="M0 60 L18 22 L30 98 L46 12 L60 104 L78 30 L92 88 L110 40 L124 76 L142 48 L158 68 L176 54 L200 62 L240 58 L640 60"
            fill="none" stroke="var(--sq-signal)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M0 60 H640" stroke="var(--sq-amber)" strokeWidth="1.2" strokeDasharray="3 7" opacity="0.6" />
    </svg>
  );
}

const conditions = [
  {id: 'none', title: 'Nothing', body: 'The baseline. No skills loaded.'},
  {id: 'A', title: 'Skill A', body: 'One instruction set on its own.'},
  {id: 'B', title: 'Skill B', body: 'The other, on its own.'},
  {id: 'A + B', title: 'Both', body: 'Sharing a turn. Do they collide?'},
];

const built = [
  ['Trusted grading', 'A grader the agent never sees, run in a fresh directory on only the files the task allows.'],
  ['Bounded agent loop', 'Four tools, hard path boundaries, and limits on calls, tools, time and output.'],
  ['Honest classification', 'Whether the machinery worked is tracked apart from whether the work was right.'],
  ['Local or scripted', 'Run real inference on your own machine with Ollama, or replay deterministic scripts for free.'],
  ['Crash-safe campaigns', 'Interleaved order, a token ledger, resume, and preregistration bound into every result.'],
  ['Self-checking analysis', 'Confidence intervals, ceiling and floor warnings, and offline re-analysis of stored runs.'],
];

const phases = [
  ['1', 'Instrumented lab', 'built', 'Run a task with and without skills; inspect everything; reproduce a constructed conflict.'],
  ['2', 'Interaction map', 'planned', 'Do skills nobody designed to clash still interfere?'],
  ['3', 'Composition experiments', 'planned', 'Shared vs phased vs isolated, with control arms.'],
  ['4', 'Generalization', 'planned', 'Does a finding survive a new model, new tasks, an edited skill?'],
  ['5', 'Lifecycle', 'planned', 'Propose, test, decide, promote, roll back.'],
];

export default function Home() {
  return (
    <Layout title="Squelch" description="A lab for measuring interference between agent skills.">
      <header className={styles.hero}>
        <div className="container">
          <p className={styles.eyebrow}>Open-source experimental lab</p>
          <h1 className={styles.title}>Do your agent skills<br />actually work together?</h1>
          <p className={styles.sub}>
            In radio, <em>squelch</em> suppresses noise so the signal comes through. Skills that pass on their
            own can interfere when loaded together. Squelch measures that, and tests whether
            rearranging how instructions are applied fixes it.
          </p>
          <Wave />
          <div className={styles.buttons}>
            <Link className="button button--primary button--lg" to="/docs/getting-started/quickstart">
              Run the offline demo
            </Link>
            <Link className="button button--secondary button--lg" to="/docs/intro">
              What is Squelch?
            </Link>
            <Link className={clsx('button button--outline button--lg', styles.ghost)}
                  href="https://github.com/kshesha1/Squelch">
              GitHub
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className={styles.section}>
          <div className="container">
            <h2>Every task runs four ways</h2>
            <p className={styles.lede}>
              Comparing "both skills" to "no skills" can't tell you whether the pair is the problem or just one
              skill. Four conditions can.
            </p>
            <div className={styles.grid4}>
              {conditions.map((c) => (
                <div key={c.id} className={styles.card}>
                  <div className={styles.pill}>{c.id}</div>
                  <h3>{c.title}</h3>
                  <p>{c.body}</p>
                </div>
              ))}
            </div>
            <p className={styles.note}>
              Same task, fresh workspace every run, graded by code the agent never sees.
              If the pair scores below <em>both</em> singletons, that's a candidate conflict.
            </p>
          </div>
        </section>

        <section className={clsx(styles.section, styles.alt)}>
          <div className="container">
            <h2>What Phase 1 built</h2>
            <div className={styles.grid3}>
              {built.map(([t, b]) => (
                <div key={t} className={styles.card}>
                  <h3>{t}</h3>
                  <p>{b}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className="container">
            <h2>An honest status</h2>
            <div className={styles.callout}>
              <p>
                <strong>No validated research finding exists yet.</strong> The first live pilot (48 runs on a local
                8B model) showed a dip when both skills were loaded: 83% / 92% / 92% / 75% for none / A / B / both.
                With 12 runs per condition that can't be told apart from noise. The dramatic cell that
                looked like a conflict turned out to be three unrelated failures, one of which exposed a bug
                in the lab itself.
              </p>
              <p>
                <Link to="/docs/results/pilot-001">Read what was measured, what failed, and why →</Link>
              </p>
            </div>
          </div>
        </section>

        <section className={clsx(styles.section, styles.alt)}>
          <div className="container">
            <h2>Where it's going</h2>
            <div className={styles.phases}>
              {phases.map(([n, t, s, b]) => (
                <div key={n} className={styles.phase}>
                  <div className={styles.phaseNum}>{n}</div>
                  <div>
                    <h3>
                      {t}{' '}
                      <span className={clsx(styles.badge, s === 'built' ? styles.built : styles.planned)}>{s}</span>
                    </h3>
                    <p>{b}</p>
                  </div>
                </div>
              ))}
            </div>
            <p className={styles.note}>
              <Link to="/docs/roadmap">Full roadmap, including known gaps →</Link>
            </p>
          </div>
        </section>
      </main>
    </Layout>
  );
}
