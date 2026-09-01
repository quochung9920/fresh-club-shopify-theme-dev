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
