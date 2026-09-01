const fs = require('fs');
const path = require('path');
const vm = require('vm');

const asset = path.resolve(__dirname, '..', 'assets', 'product-form.js');
const listeners = new Map();
const attributes = new Map();
const dialogListeners = new Map();
let ProductFormElement;
let authorityFetchCount = 0;
let cartFetchCount = 0;
let lastSubmitPromise;
let submittedPayloads = [];
let cartResponses = [];
let dialogOpened = false;
let rejectAuthorityOnce = false;
const authorityUrls = [];

const dataName = (attribute) => attribute
  .slice(5)
  .replace(/-([a-z])/g, (_match, letter) => letter.toUpperCase());

const authorityState = {
  stockProductUrl: '/products/test',
  stockRefreshUrl: '/collections/all',
  stockFormKey: 'quick-add-section-1101',
  stockVariantId: '101',
  stockLimit: '3',
  stockCartQuantity: '1',
  stockMin: '1',
  stockIncrement: '1',
  productQuantityLimit: '10',
  productCartQuantity: '1',
};

const sourceProductForm = {
  get dataset() { return { ...authorityState }; },
  hasAttribute(attribute) { return authorityState[dataName(attribute)] !== undefined; },
  getAttribute(attribute) { return authorityState[dataName(attribute)] ?? null; },
};

const variantInput = { disabled: true, value: '101' };
const quantityInput = { value: '5' };
const form = {
  addEventListener(type, handler) { listeners.set(`form:${type}`, handler); },
  requestSubmit() {
    lastSubmitPromise = listeners.get('form:submit')({ preventDefault() {} });
    return lastSubmitPromise;
  },
  elements: { namedItem(name) { return name === 'quantity' ? quantityInput : null; } },
  checkValidity() { return true; },
  reportValidity() {},
  querySelector(selector) {
    if (selector === '[name=id]') return variantInput;
    return null;
  },
};
const spinner = { classList: { add() {}, remove() {} } };
const submitText = { classList: { add() {}, remove() {} }, textContent: 'Add to cart' };
const submitButton = {
  isConnected: true,
  classList: { add() {}, remove() {} },
  focus() {},
  getAttribute(name) { return attributes.get(name) ?? null; },
  setAttribute(name, value) { attributes.set(name, String(value)); },
  removeAttribute(name) { attributes.delete(name); },
  querySelector(selector) {
    if (selector === 'span') return submitText;
    if (selector === '.sold-out-message') return null;
    return null;
  },
};
const requestedOutput = { textContent: '' };
const remainingOutput = { textContent: '' };
const availableMessage = { hidden: false };
const emptyMessage = { hidden: true };
let confirmationValidityReports = 0;
const confirmationQuantityInput = {
  value: '1',
  min: '1',
  max: '1',
  step: '1',
  focus() {},
  checkValidity() {
    const value = Number(this.value);
    const min = Number(this.min);
    const max = Number(this.max);
    const step = Number(this.step);
    return Number.isInteger(value) && value >= min && value <= max && (value - min) % step === 0;
  },
  reportValidity() { confirmationValidityReports += 1; },
};
const confirmationQuantityField = { hidden: false };
const dialog = {
  open: false,
  addEventListener(type, handler) { dialogListeners.set(type, handler); },
  showModal() { this.open = true; dialogOpened = true; },
  close() { this.open = false; dialogListeners.get('close')?.(); },
};
const confirmButton = {
  hidden: false,
  disabled: false,
  addEventListener(type, handler) { listeners.set(`confirm:${type}`, handler); },
  focus() {},
};
const cancelButton = {
  textContent: 'Cancel',
  addEventListener(type, handler) { listeners.set(`cancel:${type}`, handler); },
  focus() {},
};

class FakeHTMLElement {
  constructor() {
    this.dataset = {
      stockProductUrl: '/products/test',
      stockRefreshUrl: '/collections/all',
      stockRefreshQuery: 'true',
      stockFormKey: 'quick-add-section-1101',
      stockVariantId: '101',
      stockLimit: '3',
      stockCartQuantity: '1',
      stockMin: '1',
      stockIncrement: '1',
      productQuantityLimit: '10',
      productCartQuantity: '1',
      sectionId: 'section-1',
    };
  }
  querySelector(selector) {
    if (selector === 'form') return form;
    if (selector === '[type="submit"]') return submitButton;
    if (selector === '.loading__spinner') return spinner;
    if (selector === '[data-stock-confirmation]') return dialog;
    if (selector === '[data-stock-confirmation-confirm]') return confirmButton;
    if (selector === '[data-stock-confirmation-cancel]') return cancelButton;
    if (selector === '[data-stock-confirmation-requested]') return requestedOutput;
    if (selector === '[data-stock-confirmation-remaining]') return remainingOutput;
    if (selector === '[data-stock-confirmation-available]') return availableMessage;
    if (selector === '[data-stock-confirmation-empty]') return emptyMessage;
    if (selector === '[data-stock-confirmation-quantity]') return confirmationQuantityInput;
    if (selector === '[data-stock-confirmation-quantity-field]') return confirmationQuantityField;
    if (selector === '.product-form__error-message-wrapper') return null;
    return null;
  }
  setAttribute(attribute, value) {
    if (attribute.startsWith('data-')) this.dataset[dataName(attribute)] = String(value);
  }
  removeAttribute(attribute) {
    if (attribute.startsWith('data-')) delete this.dataset[dataName(attribute)];
  }
  closest() { return null; }
}

class FakeFormData {
  constructor() {
    this.values = new Map([
      ['id', variantInput.value],
      ['quantity', quantityInput.value],
      ['properties[Ripeness preference]', 'Ready'],
    ]);
  }
  get(name) { return this.values.get(name) ?? null; }
  set(name, value) { this.values.set(name, String(value)); }
  append(name, value) { this.values.set(name, value); }
}

class FakeDOMParser {
  parseFromString() {
    return {
      querySelectorAll(selector) {
        return selector === 'product-form[data-stock-form-key]' ? [sourceProductForm] : [];
      },
    };
  }
}

const context = {
  HTMLElement: FakeHTMLElement,
  customElements: {
    get() { return undefined; },
    define(_name, elementClass) { ProductFormElement = elementClass; },
  },
  DOMParser: FakeDOMParser,
  document: {
    activeElement: submitButton,
    querySelector() { return null; },
  },
  window: {
    location: { pathname: '/collections/all', search: '?page=2&filter.v.availability=1' },
    routes: { cart_url: '/cart' },
    variantStrings: { addToCart: 'Add to cart' },
  },
  routes: { cart_add_url: '/cart/add.js' },
  FormData: FakeFormData,
  fetch(url, config) {
    if (url === '/cart/add.js') {
      cartFetchCount += 1;
      submittedPayloads.push({
        id: config.body.get('id'),
        quantity: config.body.get('quantity'),
        ripeness: config.body.get('properties[Ripeness preference]'),
      });
      const response = cartResponses.shift() || { id: 101 };
      if (response.authority) Object.assign(authorityState, response.authority);
      return Promise.resolve({ json: () => Promise.resolve(response) });
    }

    authorityFetchCount += 1;
    authorityUrls.push(url);
    if (rejectAuthorityOnce) {
      rejectAuthorityOnce = false;
      return Promise.reject(new Error('authority unavailable'));
    }
    return Promise.resolve({ ok: true, text: () => Promise.resolve('<section></section>') });
  },
  fetchConfig() { return { headers: {} }; },
  publish() { return Promise.resolve(); },
  PUB_SUB_EVENTS: { cartError: 'cart-error', cartUpdate: 'cart-update' },
  CartPerformance: {
    createStartingMarker() { return null; },
    measureFromMarker() {},
    measure(_name, callback) { callback(); },
    measureFromEvent() {},
  },
  console,
  setTimeout,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(asset, 'utf8'), context, { filename: asset });

const submit = async () => {
  lastSubmitPromise = listeners.get('form:submit')({ preventDefault() {} });
  await lastSubmitPromise;
  await new Promise((resolve) => setTimeout(resolve, 0));
};

(async () => {
  const productForm = new ProductFormElement();

  productForm.updateInventoryFrom(undefined);
  if (!productForm.dataset.stockFormKey || !productForm.dataset.stockRefreshUrl) {
    throw new Error('missing source erased persistent stock identity');
  }
  if (productForm.dataset.stockLimit !== undefined) throw new Error('missing source retained variant stock metadata');
  productForm.updateInventoryFrom(sourceProductForm);

  Object.assign(productForm.dataset, { stockLimit: '4', stockCartQuantity: '0', stockMin: '1', stockIncrement: '3' });
  if (productForm.getAddableStock() !== 3) throw new Error('increment cap did not return the largest valid quantity');
  Object.assign(productForm.dataset, { stockLimit: '3', stockCartQuantity: '0', stockMin: '5', stockIncrement: '1' });
  if (productForm.getAddableStock() !== 0) throw new Error('stock below minimum did not become close-only');
  Object.assign(productForm.dataset, { stockLimit: '8', stockCartQuantity: '2', stockMin: '5', stockIncrement: '3' });
  if (productForm.getAddableStock() !== 6) throw new Error('existing valid cart quantity did not cap by increment');
  Object.assign(productForm.dataset, {
    stockLimit: '100',
    stockCartQuantity: '2',
    stockMin: '1',
    stockIncrement: '1',
    productQuantityLimit: '10',
    productCartQuantity: '9',
  });
  if (productForm.getAddableStock() !== 1) throw new Error('per-product limit did not include other variants');
  productForm.dataset.productCartQuantity = '10';
  if (productForm.getAddableStock() !== 0) throw new Error('product already at ten did not become close-only');
  Object.assign(productForm.dataset, { stockLimit: '3', stockCartQuantity: '1', stockMin: '1', stockIncrement: '1' });
  productForm.dataset.productCartQuantity = '1';

  let escapedEventsStopped = 0;
  const escapeEvent = { code: 'Escape', stopPropagation() { escapedEventsStopped += 1; } };
  dialogListeners.get('keydown')(escapeEvent);
  dialogListeners.get('keyup')(escapeEvent);
  productForm.pendingStockQuantity = 2;
  dialogListeners.get('cancel')(escapeEvent);
  if (escapedEventsStopped !== 3) throw new Error('nested dialog Escape events were not isolated');
  if (productForm.pendingStockQuantity !== undefined) throw new Error('native dialog cancel retained pending stock');

  quantityInput.value = '5';
  await submit();
  if (authorityFetchCount !== 1) throw new Error('tracked submit did not refresh server authority');
  if (!authorityUrls[0].includes('page=2') || !authorityUrls[0].includes('section_id=section-1')) {
    throw new Error('card authority refresh dropped current query or section identity');
  }
  if (cartFetchCount !== 0) throw new Error('over-stock submit reached Shopify before confirmation');
  if (!dialogOpened || requestedOutput.textContent !== '5' || remainingOutput.textContent !== '2') {
    throw new Error('over-stock confirmation quantities were incorrect');
  }
  if (confirmationQuantityInput.value !== '2' || confirmationQuantityInput.max !== '2') {
    throw new Error('confirmation input did not default and cap to available stock');
  }
  confirmationQuantityInput.value = '3';
  listeners.get('confirm:click')({ preventDefault() {} });
  await new Promise((resolve) => setTimeout(resolve, 0));
  if (cartFetchCount !== 0 || !dialog.open || confirmationValidityReports !== 1) {
    throw new Error('invalid edited quantity was not blocked inside confirmation');
  }

  listeners.get('cancel:click')({ preventDefault() {} });
  if (cartFetchCount !== 0 || dialog.open) throw new Error('cancelled confirmation changed cart or remained open');

  await submit();
  Object.assign(authorityState, { stockLimit: '3', stockCartQuantity: '2' });
  confirmationQuantityInput.value = '1';
  listeners.get('confirm:click')({ preventDefault() {} });
  listeners.get('confirm:click')({ preventDefault() {} });
  await lastSubmitPromise;
  await new Promise((resolve) => setTimeout(resolve, 0));
  if (cartFetchCount !== 1) throw new Error('repeated confirm submitted more than once');
  if (submittedPayloads.at(-1).quantity !== '1') throw new Error('confirm-time authority did not lower capped quantity');
  if (submittedPayloads.at(-1).id !== '101' || submittedPayloads.at(-1).ripeness !== 'Ready') {
    throw new Error('confirmed retry did not preserve variant ID and line-item property');
  }

  Object.assign(authorityState, { stockLimit: '3', stockCartQuantity: '3' });
  quantityInput.value = '1';
  await submit();
  if (
    cartFetchCount !== 1 ||
    !dialog.open ||
    !confirmButton.hidden ||
    !confirmationQuantityField.hidden ||
    emptyMessage.hidden
  ) {
    throw new Error('zero remaining stock did not show a close-only message');
  }
  listeners.get('cancel:click')({ preventDefault() {} });

  Object.assign(authorityState, { stockLimit: '5', stockCartQuantity: '1' });
  Object.assign(productForm.dataset, authorityState);
  quantityInput.value = '3';
  cartResponses.push({
    status: 422,
    description: 'Only 2 items are available.',
    authority: { stockLimit: '3', stockCartQuantity: '1' },
  });
  await submit();
  if (!dialog.open || remainingOutput.textContent !== '2') throw new Error('server inventory race did not refresh and re-offer');
  listeners.get('confirm:click')({ preventDefault() {} });
  await lastSubmitPromise;
  await new Promise((resolve) => setTimeout(resolve, 0));
  if (submittedPayloads.at(-1).quantity !== '2') throw new Error('bounded stock recovery did not submit refreshed remainder');

  Object.assign(authorityState, { stockLimit: '5', stockCartQuantity: '1' });
  Object.assign(productForm.dataset, authorityState);
  quantityInput.value = '3';
  cartResponses.push(
    {
      status: 422,
      description: 'Only 2 items are available.',
      authority: { stockLimit: '3', stockCartQuantity: '1' },
    },
    {
      status: 422,
      description: 'Only 1 item is available.',
      authority: { stockLimit: '2', stockCartQuantity: '1' },
    }
  );
  await submit();
  listeners.get('confirm:click')({ preventDefault() {} });
  await lastSubmitPromise;
  await new Promise((resolve) => setTimeout(resolve, 0));
  if (dialog.open) throw new Error('second server race exceeded the single recovery offer');

  Object.assign(authorityState, { stockLimit: '3', stockCartQuantity: '1' });
  Object.assign(productForm.dataset, authorityState);
  quantityInput.value = '5';
  rejectAuthorityOnce = true;
  await submit();
  if (!dialog.open || remainingOutput.textContent !== '2') {
    throw new Error('authority network failure did not fall back to rendered stock preflight');
  }
  listeners.get('cancel:click')({ preventDefault() {} });

  delete productForm.dataset.stockLimit;
  delete authorityState.stockLimit;
  Object.assign(productForm.dataset, { productQuantityLimit: '10', productCartQuantity: '9' });
  Object.assign(authorityState, { productQuantityLimit: '10', productCartQuantity: '9' });
  const authorityBeforeUntracked = authorityFetchCount;
  quantityInput.value = '5';
  await submit();
  if (authorityFetchCount !== authorityBeforeUntracked + 1) throw new Error('untracked product limit skipped authority refresh');
  if (!dialog.open || remainingOutput.textContent !== '1') throw new Error('untracked product did not enforce remaining quota');
  confirmationQuantityInput.value = '1';
  listeners.get('confirm:click')({ preventDefault() {} });
  await lastSubmitPromise;
  await new Promise((resolve) => setTimeout(resolve, 0));
  if (submittedPayloads.at(-1).quantity !== '1') throw new Error('untracked product quota confirmation was incorrect');

  console.log('Product form authoritative insufficient-stock behavior passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
