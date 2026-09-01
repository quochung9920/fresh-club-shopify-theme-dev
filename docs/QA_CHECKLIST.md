# Fresh Club QA Checklist

Record the tested commit SHA and Shopify preview theme ID in every QA report.

## A. Static HTML gate

- [ ] Approved reference source is preserved unchanged and hashed.
- [ ] Copy, assets, fonts, colors, spacing, and section order match authority.
- [ ] Semantic landmarks and heading hierarchy are valid.
- [ ] Keyboard order and focus indicators work.
- [ ] No duplicate IDs or broken internal links.
- [ ] No missing local assets or unexpected remote dependencies.
- [ ] No console/page errors.
- [ ] No horizontal overflow at 390, 768, or 1440 pixels.
- [ ] Reference/candidate screenshots use the same browser, DPR, font state, and viewport.
- [ ] Visual differences are recorded numerically, not described only by eye.

## B. GSAP gate

- [ ] Static content is readable before JavaScript and when JavaScript fails.
- [ ] `prefers-reduced-motion` produces an immediate readable state.
- [ ] Animation selectors are scoped to the component/section root.
- [ ] Timelines are cleaned up before re-initialization.
- [ ] Repeated initialization does not duplicate handlers or timelines.
- [ ] Resize and breakpoint changes are stable.
- [ ] Keyboard and touch interactions are tested.
- [ ] Animation uses transform/opacity unless an exception is documented.
- [ ] No layout shift, horizontal overflow, or console errors are introduced.

## C. Liquid/Theme Editor gate

- [ ] Section and block schema labels are clear to merchants.
- [ ] Repeatable content uses blocks or structured settings.
- [ ] Images use Shopify image objects, dimensions, responsive output, and correct alt behavior.
- [ ] CSS/JS is section-instance safe.
- [ ] `shopify:section:load` and `shopify:section:unload` are handled when JavaScript is present.
- [ ] Theme Editor block selection works where applicable.
- [ ] JSON templates parse and preserve unrelated content/settings.
- [ ] `config/settings_data.json` has no unrelated changes.
- [ ] Theme structure validator passes.
- [ ] Theme Check regression gate reports no new offense signatures.
- [ ] `git diff --check` passes.

## D. Shopify preview gate

- [ ] Theme is `Main - dev [Git]` `#160342835397`.
- [ ] Theme is unpublished.
- [ ] Theme card shows repository `fresh-club-shopify-theme` and branch `dev`.
- [ ] Shopify sync log references the expected commit.
- [ ] Homepage, header, footer, target templates, and shared components render.
- [ ] Theme settings and sections can be edited without errors.
- [ ] About Us and How It Works are regression-tested when shared assets change.
- [ ] 390, 768, and 1440 pixel captures are compared with the approved static candidate.
- [ ] Reduced motion, keyboard, touch, resize, no-JS, console, and network states are tested.
- [ ] No production theme was changed or published.

## E. Promotion gate

- [ ] PR is `dev → main` and references the exact QA-approved SHA.
- [ ] CI and human review are green.
- [ ] Release notes and rollback steps are attached.
- [ ] Unpublished production candidate is compared with live `Main`.
- [ ] Separate owner approval exists before any publish/cutover action.
