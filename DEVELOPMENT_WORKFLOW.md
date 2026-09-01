# Fresh Club Development Workflow

This workflow turns an approved static page into production-ready Shopify Liquid while keeping development safe, reviewable, and friendly to human and LLM developers.

## System map

```text
Static HTML authority
        ↓ Gate 1
GSAP interaction prototype
        ↓ Gate 2
Shopify Liquid implementation on feature branch
        ↓ Gate 3
PR → dev
        ↓ native Shopify GitHub sync
Main - dev [Git] #160342835397
        ↓ Gate 4 preview QA
PR dev → main (separate approval)
        ↓
Production candidate / controlled cutover
```

`Main` `#150898606277` remains live throughout development. Merging code is not permission to publish.

## Branch model

| Branch | Purpose | Shopify relationship |
|---|---|---|
| `main` | Reviewed production source history | No automatic production publish |
| `dev` | Shared integration branch | Connected to draft `Main - dev [Git]` `#160342835397` |
| `feat/*` | One feature/page/section | Not connected; PR into `dev` |
| `fix/*` | One focused correction | Not connected; PR into `dev` |
| `chore/*` | Tooling/docs/CI only | Not connected; PR into `dev` |

Use Conventional Commits such as `feat(about): add story timeline section`.

## Feature workspace

For a feature named `about-story`, use:

```text
prototype/about-story/
├── reference/       # immutable approved HTML/CSS/JS/assets
├── working/         # static component and GSAP iteration
├── evidence/
│   ├── screenshots/
│   ├── visual-diff.json
│   └── interaction-results.json
└── COMPONENT_MAP.md
```

Theme implementation remains in Shopify's standard root folders:

```text
assets/  config/  layout/  locales/  sections/  snippets/  templates/
```

## Stage 0 — Intake and contract

Before coding:

1. Update `dev`, create a feature branch, and confirm a clean working tree.
2. Save the supplied static source unchanged in `prototype/<feature>/reference/`.
3. Hash and inventory the reference files and assets.
4. Record authoritative copy, images, fonts, colors, breakpoints, states, and interactions.
5. Create `COMPONENT_MAP.md` with:
   - static selector/component;
   - Shopify section/snippet/block target;
   - merchant-editable settings;
   - asset source;
   - responsive behavior;
   - GSAP trigger/timeline and cleanup behavior.
6. Define acceptance screenshots at 390, 768, and 1440 pixels.

**Gate 0:** no implementation begins until source authority and acceptance criteria are explicit.

## Stage 1 — Static HTML

Build semantic, accessible HTML before animation or Liquid:

1. Preserve approved visual geometry and copy.
2. Use reusable components/data registries for repeated cards, steps, FAQs, and navigation.
3. Keep local assets auditable; do not substitute assets silently.
4. Implement responsive behavior at 390, 768, and 1440 plus intermediate widths.
5. Ensure keyboard order, headings, labels, landmarks, and links are correct.
6. Verify no horizontal overflow, duplicate IDs, missing assets, or console errors.

**Gate 1 evidence:** reference and candidate screenshots, DOM metrics, asset inventory, accessibility checks, and deterministic visual diff. Non-zero visual differences must be reported numerically.

## Stage 2 — GSAP

Add motion only after static layout approval:

1. Put each feature's animation in an isolated module.
2. Scope queries to a component/section root; never query the entire document when section scope is available.
3. Use GSAP context and explicit cleanup to prevent duplicate timelines.
4. Animate `transform` and `opacity` by default.
5. Avoid animation-dependent content visibility; content must remain usable without JavaScript.
6. Implement `prefers-reduced-motion` with immediate readable end states.
7. Define behavior for resize, breakpoint changes, repeated initialization, and dynamic section reload.
8. Test fast navigation, back/forward cache, and repeated Theme Editor section loading.

**Gate 2 evidence:** normal motion, reduced motion, keyboard interaction, mobile touch, resize behavior, no duplicate initialization, and no console/page errors.

## Stage 3 — Shopify Liquid conversion

Convert the approved static/GSAP contract without redesigning it:

1. Create or update the smallest appropriate section, snippet, template, and asset set.
2. Keep section instances isolated using a root keyed by `section.id`.
3. Convert content controls into clear section settings and repeatable content into blocks.
4. Use Shopify image objects and responsive `image_url`/`image_tag` output with dimensions and useful alt behavior.
5. Keep schema labels merchant-friendly and defaults safe.
6. Preserve valid JSON templates and avoid unrelated `settings_data.json` changes.
7. Support Theme Editor lifecycle events:
   - `shopify:section:load`;
   - `shopify:section:unload`;
   - `shopify:section:reorder` when relevant;
   - block select/deselect when animation state depends on blocks.
8. Keep static class names where they are part of the approved visual contract.
9. Run structure validation and Theme Check regression locally.

**Gate 3:** PR into `dev`; review the exact diff, generated evidence, settings/schema behavior, and regression checks. No direct push to `dev`.

## Stage 4 — Shopify draft QA

After the PR is merged, Shopify syncs `dev` to `Main - dev [Git]` `#160342835397`.

1. Confirm the theme card still shows repository `fresh-club-shopify-theme`, branch `dev`, and unpublished status.
2. Review sync logs and verify the expected commit.
3. Preview the draft; never publish it.
4. Test homepage, header, footer, target page/templates, Theme Editor settings, assets, and responsive behavior.
5. Validate 390, 768, and 1440 pixel screenshots against the approved static candidate in the same browser/DPR/font state.
6. Test animations, reduced motion, keyboard access, console errors, network failures, and no-JS readability.
7. Re-test unaffected critical pages to catch shared CSS/JS regressions.

**Gate 4:** QA signs off the exact commit SHA and preview theme ID. A draft QA pass is not production approval.

## Stage 5 — Promotion

1. Open a PR from `dev` to `main` with QA evidence and release notes.
2. Require review and green checks.
3. Confirm `main` contains only approved changes.
4. Create/refresh an unpublished production candidate from `main` and compare it with live `Main`.
5. Publish only under a separate, explicit owner-approved cutover procedure with rollback authority.

## Daily commands

```bash
git fetch origin
git checkout dev
git pull --ff-only origin dev
git checkout -b feat/<feature-name>

npm ci --ignore-scripts
npm run validate
git diff --check
git status --short
git push -u origin HEAD
gh pr create --base dev --draft
```

The locked Theme Check process currently returns exit code 1 because the imported baseline contains known offenses. `npm run validate` captures that expected code, then runs the blocking regression gate: the reviewed baseline is permitted, but newly introduced or increased offense signatures fail.

## Definition of done

A feature is done only when all four implementation gates pass, the exact commit is previewed on `#160342835397`, evidence is attached to the PR, no new Theme Check offenses are introduced, and nothing has been published.
