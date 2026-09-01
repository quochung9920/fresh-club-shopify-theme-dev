(() => {
  const CHECKOUT_SELECTOR = '#checkout, #CartDrawer-Checkout, #cart-notification-checkout, button[name="checkout"]';
  const EXTERNAL_DISABLED_CLASSES = ['dingdoong-disabled-checkout', 'dingdoong-disabled-buy-it-now'];

  const getCheckout = (target) => {
    if (!target) return null;
    if (target.matches?.(CHECKOUT_SELECTOR)) return target;
    return target.closest?.(CHECKOUT_SELECTOR) || null;
  };

  const getRulesState = (button) => {
    const describedBy = button.getAttribute('aria-describedby') || '';
    for (const id of describedBy.split(/\s+/).filter(Boolean)) {
      const container = document.getElementById(id);
      if (!container) continue;
      const state = container.matches?.('[data-cart-rules-valid]')
        ? container
        : container.querySelector?.('[data-cart-rules-valid]');
      if (state) return state.dataset.cartRulesValid === 'true';
    }
    return false;
  };

  const externallyDisabled = (button) => EXTERNAL_DISABLED_CLASSES.some((name) => button.classList.contains(name));

  const sync = (button) => {
    if (!button) return;
    const valid = getRulesState(button);

    if (!valid) {
      button.dataset.cartRulesDisabled = 'true';
      if (!button.disabled) button.disabled = true;
      if (!button.hasAttribute?.('disabled')) button.setAttribute('disabled', 'disabled');
      if (button.getAttribute('aria-disabled') !== 'true') button.setAttribute('aria-disabled', 'true');
      return;
    }

    if (button.dataset.cartRulesDisabled !== 'true') return;
    delete button.dataset.cartRulesDisabled;
    if (externallyDisabled(button)) {
      if (button.getAttribute('aria-disabled') !== 'true') button.setAttribute('aria-disabled', 'true');
      return;
    }

    if (button.disabled) button.disabled = false;
    button.removeAttribute('disabled');
    button.setAttribute('aria-disabled', 'false');
  };

  const syncAll = () => document.querySelectorAll(CHECKOUT_SELECTOR).forEach(sync);

  const blockInvalidCheckout = (event, button) => {
    if (!button || getRulesState(button)) return;
    sync(button);
    event.preventDefault();
    event.stopImmediatePropagation();
  };

  document.addEventListener('click', (event) => blockInvalidCheckout(event, getCheckout(event.target)), true);
  document.addEventListener(
    'submit',
    (event) => blockInvalidCheckout(event, getCheckout(event.submitter) || event.target.querySelector?.(CHECKOUT_SELECTOR)),
    true
  );

  const observer = new MutationObserver(syncAll);
  observer.observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['disabled', 'aria-disabled', 'class', 'data-cart-rules-valid'],
  });

  window.FreshClubCartRulesGuard = { sync, syncAll, getRulesState };
  syncAll();
})();

(() => {
  const PRODUCT_LIMIT = 10;
  const MESSAGE_CLASS = 'fc-quantity-limit-message';
  const WARNING_CLASS = 'fc-quantity-limit-message--warning';
  const PRODUCT_FORM_SELECTOR = 'product-form[data-product-quantity-limit]';
  const STOCK_ATTRIBUTES = [
    'data-stock-limit',
    'data-stock-cart-quantity',
    'data-stock-min',
    'data-stock-increment',
    'data-product-cart-quantity',
    'data-product-quantity-limit',
  ];

  let messageSequence = 0;
  let cartRefreshTimer;
  let cartRequest;

  const number = (value, fallback = 0) => {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  const installStyles = () => {
    if (document.getElementById('FreshClubQuantityLimitStyles')) return;
    const style = document.createElement('style');
    style.id = 'FreshClubQuantityLimitStyles';
    style.textContent = `
      .${MESSAGE_CLASS} {
        display: block;
        margin: .6rem 0 0;
        font-size: 1.2rem;
        line-height: 1.4;
        color: rgba(var(--color-foreground), .7);
      }
      .${WARNING_CLASS} {
        color: rgb(var(--color-foreground));
        font-weight: 600;
      }
      quantity-input .quantity__button:disabled,
      quantity-input-custom .quantity__button:disabled {
        cursor: not-allowed;
        opacity: .45;
      }
    `;
    document.head.appendChild(style);
  };

  const getContextFromDataset = (dataset) => {
    if (!dataset || dataset.productQuantityLimit === undefined) return null;

    const productLimit = Math.max(number(dataset.productQuantityLimit, PRODUCT_LIMIT), 0);
    const productCartQuantity = Math.max(number(dataset.productCartQuantity), 0);
    const variantCartQuantity = Math.max(number(dataset.stockCartQuantity), 0);
    const businessRemaining = Math.max(productLimit - productCartQuantity, 0);
    const stockRemaining =
      dataset.stockLimit === undefined
        ? Number.POSITIVE_INFINITY
        : Math.max(number(dataset.stockLimit) - variantCartQuantity, 0);
    const max = Math.max(Math.min(businessRemaining, stockRemaining), 0);
    const reason = stockRemaining <= businessRemaining ? 'stock' : 'business';

    return {
      max,
      reason,
      productLimit,
      stockRemaining,
      businessRemaining,
    };
  };

  const getProductFormForControl = (control) => {
    if (!control) return null;

    const direct = control.closest(PRODUCT_FORM_SELECTOR);
    if (direct) return direct;

    const productInfo = control.closest('product-info');
    const productInfoForm = productInfo?.querySelector(PRODUCT_FORM_SELECTOR);
    if (productInfoForm) return productInfoForm;

    const modalTrigger = control.querySelector?.('[data-ripeness-modal]') || control.closest('[data-ripeness-modal]');
    const modalSelector = modalTrigger?.dataset.ripenessModal;
    if (modalSelector) {
      try {
        return document.querySelector(modalSelector)?.querySelector(PRODUCT_FORM_SELECTOR) || null;
      } catch (_error) {
        return null;
      }
    }

    return null;
  };

  const getControlContext = (control) => {
    const productForm = getProductFormForControl(control);
    if (productForm) return { ...getContextFromDataset(productForm.dataset), productForm };

    if (control?.dataset?.productQuantityLimit !== undefined) {
      return { ...getContextFromDataset(control.dataset), productForm: null };
    }

    return null;
  };

  const getMessage = (context, corrected = false, isCart = false) => {
    if (!context) return '';

    if (context.max <= 0) {
      return context.reason === 'stock'
        ? 'No more stock is currently available.'
        : `Maximum ${context.productLimit || PRODUCT_LIMIT} per product reached.`;
    }

    if (context.reason === 'stock') {
      return corrected
        ? `Only ${context.max} item${context.max === 1 ? '' : 's'} are currently available.`
        : `${context.max} available to add.`;
    }

    if (isCart) {
      return `Maximum ${context.productLimit || PRODUCT_LIMIT} per product.`;
    }

    return corrected
      ? `You can add up to ${context.max} more (maximum ${context.productLimit || PRODUCT_LIMIT} per product).`
      : `Maximum ${context.productLimit || PRODUCT_LIMIT} per product · ${context.max} more can be added.`;
  };

  const ensureMessage = (control, input) => {
    let message = control.parentElement?.querySelector(`:scope > .${MESSAGE_CLASS}`);
    if (message) return message;

    message = document.createElement('p');
    message.className = MESSAGE_CLASS;
    message.setAttribute('role', 'status');
    message.setAttribute('aria-live', 'polite');
    message.id = `FreshClubQuantityLimit-${++messageSequence}`;

    if (control.tagName === 'QUANTITY-INPUT-CUSTOM') {
      const submit = control.querySelector('.submit_btn');
      if (submit) control.insertBefore(message, submit);
      else control.appendChild(message);
    } else {
      control.insertAdjacentElement('afterend', message);
    }

    const describedBy = new Set((input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
    describedBy.add(message.id);
    input.setAttribute('aria-describedby', Array.from(describedBy).join(' '));
    return message;
  };

  const setButtonState = (control, input, max) => {
    const plus = control.querySelector('.quantity__button[name="plus"]');
    if (!plus) return;
    const shouldDisable = max <= 0 || number(input.value) >= max;
    plus.disabled = shouldDisable;
    plus.classList.toggle('disabled', shouldDisable);
  };

  const applyInputContext = (input, context, { clamp = false, isCart = false } = {}) => {
    if (!input || !context) return;
    const control = input.closest('quantity-input, quantity-input-custom');
    if (!control) return;

    if (input.dataset.fcNativeMax === undefined) {
      input.dataset.fcNativeMax = input.hasAttribute('max') ? input.getAttribute('max') : '';
    }

    const nativeMax = input.dataset.fcNativeMax === '' ? Number.POSITIVE_INFINITY : number(input.dataset.fcNativeMax);
    const effectiveMax = Math.max(Math.min(context.max, nativeMax), 0);
    const current = Math.max(number(input.value), 0);
    const corrected = clamp && current > effectiveMax && effectiveMax > 0;

    if (effectiveMax > 0) {
      if (input.getAttribute('max') !== String(effectiveMax)) input.setAttribute('max', String(effectiveMax));
      if (corrected) {
        input.value = String(effectiveMax);
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    } else {
      input.setAttribute('max', '0');
    }

    setButtonState(control, input, effectiveMax);

    const message = ensureMessage(control, input);
    message.textContent = getMessage({ ...context, max: effectiveMax }, corrected, isCart);
    message.classList.toggle(WARNING_CLASS, corrected || effectiveMax <= 0);
    message.hidden = message.textContent === '';
  };

  const syncProductForm = (productForm, clamp = false) => {
    const context = getContextFromDataset(productForm.dataset);
    if (!context) return;

    const form = productForm.querySelector('form');
    const formId = form?.id;
    const linkedInput = formId
      ? Array.from(document.querySelectorAll('input[name="quantity"][form]')).find((input) => input.getAttribute('form') === formId)
      : null;
    const input = productForm.querySelector('input[name="quantity"]:not([type="hidden"])') || linkedInput;

    if (input) applyInputContext(input, { ...context, productForm }, { clamp });

    const submitButton = productForm.querySelector('[type="submit"][name="add"]');
    if (!submitButton) return;

    if (context.max <= 0) {
      if (!submitButton.disabled) {
        submitButton.disabled = true;
        submitButton.dataset.fcQuantityDisabled = 'true';
      }
      submitButton.setAttribute('aria-disabled', 'true');

      if (!input) {
        let message = productForm.querySelector(`.${MESSAGE_CLASS}`);
        if (!message) {
          message = document.createElement('p');
          message.className = `${MESSAGE_CLASS} ${WARNING_CLASS}`;
          message.setAttribute('role', 'status');
          message.setAttribute('aria-live', 'polite');
          submitButton.insertAdjacentElement('afterend', message);
        }
        message.textContent = getMessage(context);
      }
      return;
    }

    if (submitButton.dataset.fcQuantityDisabled === 'true') {
      submitButton.disabled = false;
      delete submitButton.dataset.fcQuantityDisabled;
      if (submitButton.getAttribute('aria-disabled') === 'true' && !submitButton.matches('[data-ripeness-submit]')) {
        submitButton.setAttribute('aria-disabled', 'false');
      }
    }
  };

  const syncProductControls = (clamp = false) => {
    document.querySelectorAll(PRODUCT_FORM_SELECTOR).forEach((productForm) => syncProductForm(productForm, clamp));

    document.querySelectorAll('quantity-input-custom[data-product-quantity-limit]').forEach((control) => {
      const input = control.querySelector('.quantity__input');
      const context = getControlContext(control);
      if (input && context) applyInputContext(input, context, { clamp });
    });
  };

  const fetchCart = () => {
    if (cartRequest) return cartRequest;
    cartRequest = fetch(`${routes.cart_url}.js`, { headers: { Accept: 'application/json' } })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error('Unable to load cart'))))
      .finally(() => {
        cartRequest = null;
      });
    return cartRequest;
  };

  const syncCartControls = async (clamp = false) => {
    const inputs = Array.from(document.querySelectorAll('cart-items input[name="updates[]"], cart-drawer-items input[name="updates[]"]'));
    if (!inputs.length) return;

    let cart;
    try {
      cart = await fetchCart();
    } catch (_error) {
      return;
    }

    const totals = new Map();
    cart.items.forEach((item) => totals.set(item.product_id, (totals.get(item.product_id) || 0) + item.quantity));

    inputs.forEach((input) => {
      const line = number(input.dataset.index);
      const item = cart.items[line - 1];
      if (!item) return;

      const productTotal = totals.get(item.product_id) || item.quantity;
      const otherLinesQuantity = Math.max(productTotal - item.quantity, 0);
      const businessLineMax = Math.max(PRODUCT_LIMIT - otherLinesQuantity, 0);
      const context = {
        max: businessLineMax,
        reason: 'business',
        productLimit: PRODUCT_LIMIT,
        businessRemaining: businessLineMax,
        stockRemaining: Number.POSITIVE_INFINITY,
      };
      applyInputContext(input, context, { clamp, isCart: true });
    });
  };

  const scheduleCartSync = (clamp = false) => {
    clearTimeout(cartRefreshTimer);
    cartRefreshTimer = setTimeout(() => syncCartControls(clamp), 80);
  };

  const bindInput = (input) => {
    if (input.dataset.fcQuantityBound === 'true') return;
    input.dataset.fcQuantityBound = 'true';

    input.addEventListener('input', () => {
      const control = input.closest('quantity-input, quantity-input-custom');
      const isCart = Boolean(input.closest('cart-items, cart-drawer-items'));
      if (isCart) {
        scheduleCartSync(true);
        return;
      }
      const context = getControlContext(control);
      if (context) applyInputContext(input, context, { clamp: true });
    });

    input.addEventListener('change', () => {
      const control = input.closest('quantity-input, quantity-input-custom');
      const isCart = Boolean(input.closest('cart-items, cart-drawer-items'));
      if (isCart) {
        scheduleCartSync(true);
        return;
      }
      const context = getControlContext(control);
      if (context) applyInputContext(input, context, { clamp: true });
    });
  };

  const bindAll = () => {
    document.querySelectorAll('quantity-input .quantity__input, quantity-input-custom .quantity__input').forEach(bindInput);
  };

  const syncAll = () => {
    installStyles();
    bindAll();
    syncProductControls(false);
    scheduleCartSync(false);
  };

  const mutationObserver = new MutationObserver((mutations) => {
    const needsProductSync = mutations.some((mutation) =>
      mutation.type === 'attributes' && STOCK_ATTRIBUTES.includes(mutation.attributeName)
    );
    const hasNewNodes = mutations.some((mutation) => mutation.type === 'childList' && mutation.addedNodes.length > 0);
    if (!needsProductSync && !hasNewNodes) return;
    syncAll();
  });

  mutationObserver.observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: STOCK_ATTRIBUTES,
  });

  if (typeof subscribe === 'function' && window.PUB_SUB_EVENTS?.cartUpdate) {
    subscribe(PUB_SUB_EVENTS.cartUpdate, () => setTimeout(syncAll, 0));
  }

  window.FreshClubQuantityLimits = {
    productLimit: PRODUCT_LIMIT,
    syncAll,
    syncProductControls,
    syncCartControls,
    getContextFromDataset,
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', syncAll, { once: true });
  else syncAll();
})();
