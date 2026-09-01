class CartNotification extends HTMLElement {
  constructor() {
    super();

    this.notification = document.getElementById('cart-notification');
    this.header = document.querySelector('sticky-header');
    this.onBodyClick = this.handleBodyClick.bind(this);

    this.notification.addEventListener('keyup', (evt) => evt.code === 'Escape' && this.close());
    this.querySelectorAll('button[type="button"]').forEach((closeButton) =>
      closeButton.addEventListener('click', this.close.bind(this))
    );
  }

  open() {
    this.notification.classList.add('animate', 'active');

    this.notification.addEventListener(
      'transitionend',
      () => {
        this.notification.focus();
        trapFocus(this.notification);
      },
      { once: true }
    );

    document.body.addEventListener('click', this.onBodyClick);
  }

  close() {
    this.notification.classList.remove('active');
    document.body.removeEventListener('click', this.onBodyClick);

    removeTrapFocus(this.activeElement);
  }

  renderContents(parsedState) {
    this.cartItemKey = parsedState.key;
    this.disableCheckout();
    this.getSectionsToRender().forEach((section) => {
      const sectionElement = document.getElementById(section.id);
      const sectionHTML = parsedState.sections?.[section.id];
      if (!sectionElement) return;
      if (typeof sectionHTML !== 'string') {
        sectionElement.innerHTML = '';
        return;
      }
      sectionElement.innerHTML = this.getSectionInnerHTML(sectionHTML, section.selector);
    });

    this.updateCheckoutState();
    if (this.header) this.header.reveal();
    this.open();
  }

  disableCheckout() {
    const checkoutButton = this.querySelector('#cart-notification-checkout');
    if (!checkoutButton) return;
    checkoutButton.disabled = true;
    checkoutButton.setAttribute('aria-disabled', 'true');
  }

  updateCheckoutState() {
    const ruleState = this.querySelector('#cart-notification-rules [data-cart-rules-valid]');
    const checkoutButton = this.querySelector('#cart-notification-checkout');
    const isValid = ruleState?.dataset.cartRulesValid === 'true';

    if (!checkoutButton) return;
    if (!isValid) checkoutButton.dataset.cartRulesDisabled = 'true';
    if (window.FreshClubCartRulesGuard) {
      window.FreshClubCartRulesGuard.sync(checkoutButton);
      return;
    }
    checkoutButton.disabled = !isValid;
    checkoutButton.setAttribute('aria-disabled', String(!isValid));
  }

  getSectionsToRender() {
    return [
      {
        id: 'cart-notification-product',
        selector: `[id="cart-notification-product-${this.cartItemKey}"]`,
      },
      {
        id: 'cart-notification-button',
      },
      {
        id: 'cart-notification-rules',
      },
      {
        id: 'cart-icon-bubble',
      },
    ];
  }

  getSectionInnerHTML(html, selector = '.shopify-section') {
    return new DOMParser().parseFromString(html, 'text/html').querySelector(selector)?.innerHTML ?? '';
  }

  handleBodyClick(evt) {
    const target = evt.target;
    if (target !== this.notification && !target.closest('cart-notification')) {
      const disclosure = target.closest('details-disclosure, header-menu');
      this.activeElement = disclosure ? disclosure.querySelector('summary') : null;
      this.close();
    }
  }

  setActiveElement(element) {
    this.activeElement = element;
  }
}

customElements.define('cart-notification', CartNotification);
