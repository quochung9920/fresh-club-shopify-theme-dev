# Fresh Club Theme — Agent Contract

This repository is the source of truth for the Fresh Club Shopify theme. These rules apply to humans, LLMs, and coding agents.

## Authorities

- `main` represents the production `Main` baseline. Never develop directly on it.
- `dev` is connected to Shopify draft theme `Main - dev [Git]` (`#160342835397`).
- Original draft `Main - dev` (`#158473355461`) is a rollback/reference copy, not the active development target.
- Live theme `Main` (`#150898606277`) must not be changed or published by automation.
- Static HTML approved for a feature is the visual and behavior authority for its Liquid conversion.

## Mandatory branch flow

1. Update local `dev` from `origin/dev`.
2. Create `feat/<short-name>`, `fix/<short-name>`, or `chore/<short-name>`.
3. Work through the stage gates in `DEVELOPMENT_WORKFLOW.md`.
4. Open a PR into `dev` and obtain QA approval.
5. Merge only after required checks pass. Shopify then syncs `dev` to `Main - dev [Git]`.
6. Promote `dev` to `main` only through a separately approved PR.

Never commit feature work directly to `dev` or `main`.

## Safety boundaries

- Never run or add automation that publishes a theme.
- Never use live-theme override flags.
- Never delete, rename, or overwrite Shopify theme `#150898606277`.
- Never treat a draft deployment as production approval.
- Never put tokens, passwords, `.env` files, private keys, or credentials in Git.
- Do not manually edit `config/settings_data.json` unless the task explicitly requires a reviewed settings migration.
- Do not repair unrelated baseline Theme Check offenses while implementing a feature.
- Preserve user-authored Theme Editor content and settings unless the task explicitly changes them.

## LLM working protocol

Before editing, an LLM must:

1. Read this file, `DEVELOPMENT_WORKFLOW.md`, and `docs/QA_CHECKLIST.md`.
2. Inspect `git status`, the current branch, and the complete task diff.
3. Identify the authoritative static reference, target viewport sizes, assets, copy, and interactions.
4. Write a component map from static selectors to Shopify sections, blocks, snippets, settings, and assets.
5. State which files will change and which Shopify content/settings must remain untouched.

During implementation:

- Keep the untouched approved HTML under `prototype/<feature>/reference/`.
- Work in `prototype/<feature>/working/` until HTML and GSAP gates pass.
- Scope CSS and JavaScript to the section instance. Avoid global selectors and global mutable state.
- Use `data-section-id="{{ section.id }}"` or a section-root custom element for lifecycle isolation.
- Initialize and destroy animation code on Shopify section load/unload events.
- Support `prefers-reduced-motion` and a no-JavaScript readable state.
- Prefer `transform` and `opacity` for animation; avoid layout-thrashing animation properties.
- Use Shopify image filters, responsive dimensions, semantic HTML, and valid section schema.
- Keep copy/settings merchant-editable where appropriate; do not hard-code store content without approval.

Before claiming completion, provide real command output and evidence for:

- changed-file inventory;
- static HTML and GSAP QA;
- Shopify Theme Check regression status;
- JSON/structure validation;
- preview QA at 390, 768, and 1440 pixels;
- keyboard, reduced-motion, console, and horizontal-overflow checks;
- exact Shopify preview theme ID;
- confirmation that nothing was published.

A build, lint pass, source inspection, or self-reported screenshot is not sufficient by itself.
