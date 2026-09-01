// Legacy compatibility entrypoint.
// Quantity/inventory limits are centrally managed by FreshClubQuantityLimits
// in cart-rules-guard.js so PDP, Quick Add, Cart, and Cart Drawer share one behavior.
(() => {
  const sync = () => window.FreshClubQuantityLimits?.syncAll?.();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sync, { once: true });
  } else {
    sync();
  }
})();
