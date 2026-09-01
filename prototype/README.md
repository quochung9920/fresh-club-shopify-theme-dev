# Static and GSAP Prototypes

Create one folder per feature:

```text
prototype/<feature>/
├── reference/       # untouched approved source
├── working/         # semantic HTML/CSS and GSAP iteration
├── evidence/        # screenshots, DOM metrics, visual diffs, interaction results
└── COMPONENT_MAP.md # static → Shopify mapping
```

Do not edit files under `reference/`. Hash them before work begins. The `working/` result must pass the HTML and GSAP gates in `DEVELOPMENT_WORKFLOW.md` before conversion to Liquid.

`COMPONENT_MAP.md` should contain this table:

| Static selector/component | Shopify target | Merchant setting/block | Asset | Responsive contract | GSAP lifecycle |
|---|---|---|---|---|---|

Prototype files are development evidence. Shopify runtime code belongs only in the standard theme directories at the repository root.
