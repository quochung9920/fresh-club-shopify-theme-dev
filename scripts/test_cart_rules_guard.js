const fs = require('fs');
const path = require('path');
const vm = require('vm');

const asset = path.resolve(__dirname, '..', 'assets', 'cart-rules-guard.js');
if (!fs.existsSync(asset)) throw new Error('cart-rules-guard.js is required');

const listeners = new Map();
const observerCallbacks = [];
class MockObserver {
  constructor(callback) { observerCallbacks.push(callback); }
  observe() {}
}
function makeButton(id, describedBy, valid) {
  const rules = { dataset: { cartRulesValid: String(valid) }, matches: () => true, querySelector: () => null };
  const attrs = new Map([['aria-describedby', describedBy], ['aria-disabled', valid ? 'false' : 'true']]);
  const classes = new Set();
  const button = {
    id,
    disabled: !valid,
    dataset: valid ? {} : { cartRulesDisabled: 'true' },
    classList: { contains: (name) => classes.has(name), add: (name) => classes.add(name), remove: (name) => classes.delete(name) },
    getAttribute: (name) => attrs.get(name) ?? null,
    setAttribute: (name, value) => attrs.set(name, String(value)),
    removeAttribute: (name) => attrs.delete(name),
    matches: (selector) => selector.includes(`#${id}`) || selector.includes('[name="checkout"]'),
    closest: () => null,
    form: null,
    _rules: rules,
  };
  return button;
}

const buttons = [];
const document = {
  documentElement: {},
  head: { appendChild() {} },
  readyState: 'complete',
  addEventListener(type, handler, capture) { listeners.set(`${type}:${capture}`, handler); },
  querySelector() { return null; },
  querySelectorAll(selector = '') {
    if (
      selector.includes('quantity-input') ||
      selector.includes('product-form') ||
      selector.includes('cart-items') ||
      selector.includes('cart-drawer-items')
    ) return [];
    return buttons;
  },
  createElement() {
    return {
      id: '',
      textContent: '',
      className: '',
      dataset: {},
      setAttribute() {},
      classList: { toggle() {} },
    };
  },
  getElementById(id) {
    if (id === 'FreshClubQuantityLimitStyles') return null;
    const button = buttons.find((item) => item.getAttribute('aria-describedby') === id);
    return button?._rules || null;
  },
};
const context = { document, MutationObserver: MockObserver, window: {}, console, setTimeout, clearTimeout };
vm.createContext(context);
vm.runInContext(fs.readFileSync(asset, 'utf8'), context, { filename: asset });

const invalid = makeButton('checkout', 'CartRules-main', false);
buttons.push(invalid);
context.window.FreshClubCartRulesGuard.syncAll();
if (!invalid.disabled || invalid.getAttribute('aria-disabled') !== 'true') throw new Error('initial invalid checkout not disabled');

// Reproduce DingDoong allowing checkout and removing the native attribute.
invalid.disabled = false;
invalid.removeAttribute('disabled');
invalid.classList.remove('dingdoong-disabled-checkout');
observerCallbacks[0]([{ type: 'attributes', target: invalid, attributeName: 'disabled' }]);
if (!invalid.disabled || invalid.getAttribute('aria-disabled') !== 'true') throw new Error('DingDoong mutation bypassed invalid merchant rule');

let clickBlocked = false;
listeners.get('click:true')({
  target: invalid,
  preventDefault() { clickBlocked = true; },
  stopImmediatePropagation() {},
});
if (!clickBlocked) throw new Error('invalid checkout click was not capture-blocked');

let submitBlocked = false;
listeners.get('submit:true')({
  submitter: invalid,
  target: { querySelector: () => invalid },
  preventDefault() { submitBlocked = true; },
  stopImmediatePropagation() {},
});
if (!submitBlocked) throw new Error('invalid checkout submit was not capture-blocked');

// A merchant-valid cart must not override DingDoong's own delivery-date block.
const valid = makeButton('CartDrawer-Checkout', 'CartDrawer-Rules', true);
valid.disabled = true;
valid.classList.add('dingdoong-disabled-checkout');
buttons.push(valid);
context.window.FreshClubCartRulesGuard.sync(valid);
if (!valid.disabled) throw new Error('merchant guard overrode DingDoong disabled state');

// When both authorities allow checkout, remove only the merchant-owned disable marker.
valid.dataset.cartRulesDisabled = 'true';
valid.classList.remove('dingdoong-disabled-checkout');
valid.disabled = true;
context.window.FreshClubCartRulesGuard.sync(valid);
if (valid.disabled || valid.dataset.cartRulesDisabled) throw new Error('valid checkout did not release merchant-owned disable state');

if (!context.window.FreshClubQuantityLimits) throw new Error('shared quantity limit controller was not initialized');

console.log('Cart rules app-mutation guard behavior passed');
