#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class ClassList {
  constructor() {
    this.values = new Set();
  }
  add(...names) {
    names.forEach((name) => this.values.add(name));
  }
  remove(...names) {
    names.forEach((name) => this.values.delete(name));
  }
  contains(name) {
    return this.values.has(name);
  }
}

const layoutSource = fs.readFileSync('layout/theme.liquid', 'utf8');
const cssSource = fs.readFileSync('assets/freshclub-global-shell.css', 'utf8');
const searchRowSource = fs.readFileSync('snippets/header-search-row.liquid', 'utf8');
const footerSource = fs.readFileSync('sections/footer.liquid', 'utf8');
const headerSource = fs.readFileSync('sections/header.liquid', 'utf8');
const cssBlocks = (selector) => {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...cssSource.matchAll(new RegExp(`(?<![\\w-])${escaped}\\s*\\{([^{}]*)\\}`, 'gs'))].map((match) => match[1]);
};
const cssValues = (blocks, property) => blocks.flatMap((block) => {
  const escaped = property.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...block.matchAll(new RegExp(`(?:^|;)\\s*${escaped}\\s*:\\s*([^;}]+)`, 'g'))].map((match) => match[1].trim());
});
assert.equal(fs.existsSync('assets/freshclub-global-shell.js'), false, 'always-visible header has no autohide behavior asset');
assert.equal(layoutSource.includes('freshclub-global-shell.js'), false, 'layout does not load scroll behavior');
const cartBadgeBlocks = cssBlocks('[data-fc-header-primary] .cart-count-bubble');
for (const [property, expected] of [['display', 'grid'], ['place-items', 'center'], ['line-height', '1'], ['padding', '0'], ['text-align', 'center']]) {
  assert.deepEqual(cssValues(cartBadgeBlocks, property), [expected], `cart badge uses ${property}: ${expected}`);
}
for (const token of ['fc-secondary-hidden', 'requestAnimationFrame', "addEventListener('scroll'", 'scrollY']) {
  assert.equal(cssSource.includes(token), false, `always-visible CSS excludes ${token}`);
  assert.equal(layoutSource.includes(token), false, `always-visible layout excludes ${token}`);
}
assert.match(cssSource, /\.fc-header-search-row\s*\{[^}]*margin-inline:\s*auto/s, 'page-width search row is centered');
assert.match(cssSource, /\.fc-header-search-actions\s*\{[^}]*margin-inline:\s*auto/s, 'search action group is centered');
assert.match(cssSource, /grid-template-columns:\s*minmax\(0, 1fr\)\s+minmax\(0, 480px\)\s+minmax\(0, 1fr\)/, 'desktop search uses symmetric columns');
assert.match(cssSource, /predictive-search,\s*\.fc-header-search-actions search-form\s*\{[^}]*grid-column:\s*2/s, 'search occupies the center column');
assert.match(cssSource, /\.fc-header-contact\s*\{[^}]*grid-column:\s*3[^}]*justify-self:\s*end/s, 'Contact Us occupies the right column');
const contactBlocks = cssBlocks('.fc-header-contact');
for (const property of ['min-height', 'padding', 'border-radius', 'font-size', 'font-weight', 'line-height', 'background', 'color']) {
  assert.deepEqual(cssValues(contactBlocks, property), [], `Contact Us inherits standard button ${property}`);
}
assert.equal(cssSource.includes('.fc-header-contact:hover'), false, 'Contact Us inherits standard primary-button hover');
assert.equal(cssSource.includes('.fc-header-search-spacer'), false, 'asymmetric search spacer CSS is removed');
assert.equal(searchRowSource.includes('fc-header-search-spacer'), false, 'asymmetric search spacer markup is removed');
assert.match(footerSource, /class="fc-footer-brand"/, 'footer logo uses a footer-specific brand container');
assert.match(footerSource, /class="fc-footer-logo motion-reduce"/, 'footer logo uses a footer-specific image class');
assert.equal(footerSource.includes('header__heading-logo-wrapper'), false, 'footer cannot inherit header wrapper positioning');
assert.match(cssSource, /\.fc-footer-brand\s*\{[^}]*align-items:\s*flex-start[^}]*gap:\s*32px/s, 'footer brand is left-pinned with authority spacing');
assert.match(cssSource, /\.fc-footer-logo\s*\{[^}]*object-position:\s*left center/s, 'footer logo pixels are pinned left');
assert.match(cssSource, /\.newsletter-form__button\s*\{[^}]*position:\s*relative/s, 'Subscribe contains its own absolute button pseudo-element');
assert.deepEqual(cssValues(cssBlocks('[data-fc-header-secondary]'), 'transform'), ['translateY(0)'], 'secondary row cannot be translated out of view');
assert.deepEqual(cssValues(cssBlocks('[data-fc-header-secondary]'), 'opacity'), ['1'], 'secondary row remains opaque');
assert.deepEqual(cssValues(cssBlocks('[data-fc-header-secondary]'), 'overflow'), ['visible'], 'secondary row cannot collapse overflow');
assert.deepEqual(cssValues(cssBlocks('[data-fc-header-secondary]'), 'max-height'), ['72px', '100px'], 'secondary row keeps visible responsive heights');
assert.deepEqual(cssValues(cssBlocks('[data-fc-global-footer] .newsletter-form__button'), 'position'), ['relative'], 'scoped Subscribe rule contains its pseudo-element without decoys');
assert.equal(cssValues(cssBlocks('[data-fc-global-footer] .footer__content-top .footer__blocks-wrapper'), 'align-items').includes('flex-start'), true, 'footer wrapper overrides native centered grid alignment');
const authorityHeaderLogos = [...headerSource.matchAll(/<img\b[^>]*freshclub-logo-header\.png[^>]*>/gs)].map((match) => match[0]);
assert.equal(authorityHeaderLogos.length, 2, 'both header logo branches render authority images');
for (const tag of authorityHeaderLogos) {
  assert.match(tag, /class="[^"]*\bheader__heading-logo\b[^"]*\bmotion-reduce\b[^"]*"/);
  for (const attribute of ['width="133"', 'height="32"', 'alt="FreshClub"', 'loading="eager"']) assert.equal(tag.includes(attribute), true);
}
assert.equal(footerSource.indexOf('fc-footer-brand') < footerSource.indexOf('{%- if section.blocks.size > 0 -%}'), true, 'footer logo renders before the optional blocks branch');

const lifecycleDefinitions = new Map();
const lifecycleObservers = [];
const lifecycleEventCounts = { form: {}, input: {}, element: {} };
let lifecycleReadiness = 'base-only';
const countEvent = (target, name) => {
  target[name] = (target[name] || 0) + 1;
};
const lifecycleForm = {
  addEventListener: (name) => countEvent(lifecycleEventCounts.form, name),
};
const lifecycleInput = {
  form: lifecycleForm,
  value: '',
  addEventListener: (name) => countEvent(lifecycleEventCounts.input, name),
};
const lifecycleReset = { classList: new ClassList() };
const lifecycleResults = {};
const lifecycleStatus = { setAttribute() {}, textContent: '' };
class LifecycleHTMLElement {
  querySelector(selector) {
    if (selector === 'input[type="search"]') return lifecycleReadiness === 'empty' ? null : lifecycleInput;
    if (selector === 'button[type="reset"]') return lifecycleReadiness === 'empty' ? null : lifecycleReset;
    if (selector === '[data-predictive-search]') return ['results-only', 'complete'].includes(lifecycleReadiness) ? lifecycleResults : null;
    if (selector === '.predictive-search-status') return lifecycleReadiness === 'complete' ? lifecycleStatus : null;
    return null;
  }
  querySelectorAll() {
    return [];
  }
  addEventListener(name) {
    countEvent(lifecycleEventCounts.element, name);
  }
}
class LifecycleMutationObserver {
  constructor(callback) {
    this.callback = callback;
    this.connected = false;
    lifecycleObservers.push(this);
  }
  observe() {
    this.connected = true;
  }
  disconnect() {
    this.connected = false;
  }
}
const lifecycleContext = {
  AbortController,
  console,
  debounce: (callback) => callback,
  document: { querySelectorAll: () => [] },
  HTMLElement: LifecycleHTMLElement,
  MutationObserver: LifecycleMutationObserver,
  queueMicrotask: (callback) => callback(),
  customElements: {
    define: (name, constructor) => lifecycleDefinitions.set(name, constructor),
  },
};
vm.runInNewContext(fs.readFileSync('assets/search-form.js', 'utf8'), lifecycleContext, { filename: 'search-form.js' });
vm.runInNewContext(fs.readFileSync('assets/predictive-search.js', 'utf8'), lifecycleContext, {
  filename: 'predictive-search.js',
});
const PredictiveSearch = lifecycleDefinitions.get('predictive-search');
let lifecycleInstance;
assert.doesNotThrow(() => {
  lifecycleInstance = new PredictiveSearch();
}, 'predictive search must not throw when upgraded before all descendants are parsed');
assert.deepEqual(lifecycleEventCounts.form, {}, 'predictive search must not partially bind form listeners');
assert.deepEqual(lifecycleEventCounts.input, {}, 'predictive search must not partially bind input listeners');
assert.deepEqual(lifecycleEventCounts.element, {}, 'predictive search must not bind element listeners before results exist');
assert.equal(lifecycleObservers.filter((observer) => observer.connected).length, 1, 'incomplete predictive search observes descendant completion');

lifecycleReadiness = 'results-only';
lifecycleObservers.forEach((observer) => {
  if (observer.connected) observer.callback();
});
assert.deepEqual(lifecycleEventCounts.form, {}, 'results without status must not partially bind form listeners');
assert.deepEqual(lifecycleEventCounts.input, {}, 'results without status must not partially bind input listeners');
assert.equal(lifecycleObservers.filter((observer) => observer.connected).length, 1, 'predictive search keeps observing until live status exists');

lifecycleReadiness = 'complete';
lifecycleObservers.forEach((observer) => {
  if (observer.connected) observer.callback();
});
assert.equal(lifecycleInstance.input, lifecycleInput, 'observer initialization discovers the search input');
assert.equal(lifecycleEventCounts.form.reset, 1, 'observer initialization binds base reset exactly once');
assert.equal(lifecycleEventCounts.form.submit, 1, 'observer initialization binds predictive submit exactly once');
assert.equal(lifecycleEventCounts.input.input, 1, 'observer initialization binds base input exactly once');
assert.equal(lifecycleEventCounts.input.focus, 1, 'observer initialization binds predictive focus exactly once');
assert.equal(lifecycleEventCounts.element.focusout, 1, 'observer initialization binds focusout exactly once');
assert.equal(lifecycleEventCounts.element.keyup, 1, 'observer initialization binds keyup exactly once');
assert.equal(lifecycleEventCounts.element.keydown, 1, 'observer initialization binds keydown exactly once');
assert.equal(lifecycleObservers.every((observer) => !observer.connected), true, 'observer disconnects after complete initialization');
lifecycleInstance.initializePredictiveSearch();
assert.equal(lifecycleEventCounts.form.reset, 1, 'repeated initialization does not duplicate base listeners');
assert.equal(lifecycleEventCounts.form.submit, 1, 'repeated initialization does not duplicate predictive listeners');

console.log('Always-visible global shell and predictive-search lifecycle behavior passed');
