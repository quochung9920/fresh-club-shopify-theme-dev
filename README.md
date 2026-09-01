# Fresh Club Shopify Theme

Private source repository for the Fresh Club Shopify theme.

## Environment map

| Git branch | Shopify theme | ID | Status |
|---|---|---:|---|
| `main` | `Main` baseline | `150898606277` | Production source history; live theme is not auto-published |
| `dev` | `Main - dev [Git]` | `160342835397` | Git-connected draft development theme |
| — | `Main - dev` | `158473355461` | Legacy rollback/reference draft |

## Start here

Humans and coding agents must read:

1. [`AGENTS.md`](AGENTS.md) — safety and LLM contract.
2. [`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md) — HTML → GSAP → Liquid → QA process.
3. [`docs/QA_CHECKLIST.md`](docs/QA_CHECKLIST.md) — release gates and evidence.

## Safe feature flow

```bash
git fetch origin
git checkout dev
git pull --ff-only origin dev
git checkout -b feat/<feature-name>
```

Develop and validate on the feature branch, then open a PR into `dev`. Merging into `dev` syncs code to the unpublished `Main - dev [Git]` theme. It does not authorize production publishing.

## Local validation

```bash
npm ci --ignore-scripts
npm run validate
```

The imported theme currently has a reviewed Theme Check baseline. CI rejects new offense signatures rather than forcing unrelated refactoring during feature work.

## Production rule

No repository workflow publishes Shopify themes. Production promotion requires a reviewed `dev → main` PR, preview QA on an unpublished candidate, explicit owner approval, and a separate controlled cutover.
