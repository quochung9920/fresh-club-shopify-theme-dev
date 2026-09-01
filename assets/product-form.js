if (!customElements.get('product-form')) {
  customElements.define(
    'product-form',
    class ProductForm extends HTMLElement {
      constructor() {
        super();

        this.form = this.querySelector('form');
        this.variantIdInput.disabled = false;
        this.form.addEventListener('submit', this.onSubmitHandler.bind(this));
        this.cart = document.querySelector('cart-notification') || document.querySelector('cart-drawer');
        this.submitButton = this.querySelector('[type="submit"]');
        this.submitButtonText = this.submitButton.querySelector('span');
        this.stockConfirmation = this.querySelector('[data-stock-confirmation]');
        this.stockConfirmationConfirm = this.querySelector('[data-stock-confirmation-confirm]');
        this.stockConfirmationCancel = this.querySelector('[data-stock-confirmation-cancel]');
        this.stockConfirmationRequested = this.querySelector('[data-stock-confirmation-requested]');
        this.stockConfirmationRemaining = this.querySelector('[data-stock-confirmation-remaining]');
        this.stockConfirmationAvailable = this.querySelector('[data-stock-confirmation-available]');
        this.stockConfirmationEmpty = this.querySelector('[data-stock-confirmation-empty]');
        this.stockConfirmationQuantity = this.querySelector('[data-stock-confirmation-quantity]');
        this.stockConfirmationQuantityField = this.querySelector('[data-stock-confirmation-quantity-field]');
        this.stockRecoveryCount = 0;
        this.stockPreflightPending = false;
        this.onStockConfirmationEscape = this.onStockConfirmationEscape.bind(this);
        this.onStockConfirmationCancel = this.onStockConfirmationCancel.bind(this);
        this.onStockConfirmationClose = this.onStockConfirmationClose.bind(this);

        this.stockConfirmationConfirm?.addEventListener('click', this.confirmAvailableStock.bind(this));
        this.stockConfirmationCancel?.addEventListener('click', this.cancelStockConfirmation.bind(this));
        this.stockConfirmation?.addEventListener('keydown', this.onStockConfirmationEscape);
        this.stockConfirmation?.addEventListener('keyup', this.onStockConfirmationEscape);
        this.stockConfirmation?.addEventListener('cancel', this.onStockConfirmationCancel);
        this.stockConfirmation?.addEventListener('close', this.onStockConfirmationClose);

        if (document.querySelector('cart-drawer')) this.submitButton.setAttribute('aria-haspopup', 'dialog');

        this.hideErrors = this.dataset.hideErrors === 'true';
      }

      async onSubmitHandler(evt) {
        evt.preventDefault();
        if (this.submitButton.getAttribute('aria-disabled') === 'true') return;
        if (this.stockPreflightPending) return;
        if (!this.form.checkValidity()) {
          this.form.reportValidity();
          return;
        }

        const formData = new FormData(this.form);
        const confirmedStockQuantity = this.confirmedStockQuantity;
        if (confirmedStockQuantity === undefined) this.stockRecoveryCount = 0;
        let requestedQuantity = Math.max(
          parseInt(confirmedStockQuantity ?? formData.get('quantity') ?? '1', 10),
          1
        );

        if (this.dataset.stockLimit !== undefined || this.dataset.productQuantityLimit !== undefined) {
          this.stockPreflightPending = true;
          try {
            await this.refreshInventoryFromServer(formData.get('id'));
          } finally {
            this.stockPreflightPending = false;
          }

          const addableStock = this.getAddableStock();
          if (addableStock !== null && confirmedStockQuantity === undefined && requestedQuantity > addableStock) {
            this.showStockConfirmation(requestedQuantity, addableStock);
            return;
          }

          if (addableStock !== null && confirmedStockQuantity !== undefined) {
            requestedQuantity = Math.min(requestedQuantity, addableStock);
            if (requestedQuantity === 0) {
              this.confirmedStockQuantity = undefined;
              this.showStockConfirmation(confirmedStockQuantity, 0);
              return;
            }
            formData.set('quantity', requestedQuantity);
            const quantityInput = this.form.elements.namedItem('quantity');
            if (quantityInput) quantityInput.value = String(requestedQuantity);
          }
        }
        this.confirmedStockQuantity = undefined;

        if (!this.form.checkValidity()) {
          this.form.reportValidity();
          return;
        }

        this.handleErrorMessage();

        this.submitButton.setAttribute('aria-disabled', true);
        this.submitButton.classList.add('loading');
        this.querySelector('.loading__spinner').classList.remove('hidden');

        const config = fetchConfig('javascript');
        config.headers['X-Requested-With'] = 'XMLHttpRequest';
        delete config.headers['Content-Type'];

        if (this.cart) {
          formData.append(
            'sections',
            this.cart.getSectionsToRender().map((section) => section.id)
          );
          formData.append('sections_url', window.location.pathname);
          this.cart.setActiveElement(document.activeElement);
        }
        config.body = formData;

        fetch(`${routes.cart_add_url}`, config)
          .then((response) => response.json())
          .then(async (response) => {
            if (response.status) {
              if (await this.recoverFromStockError(formData)) {
                this.error = false;
                return;
              }
              publish(PUB_SUB_EVENTS.cartError, {
                source: 'product-form',
                productVariantId: formData.get('id'),
                errors: response.errors || response.description,
                message: response.message,
              });
              this.handleErrorMessage(response.description);

              const soldOutMessage = this.submitButton.querySelector('.sold-out-message');
              if (!soldOutMessage) return;
              this.submitButton.setAttribute('aria-disabled', true);
              this.submitButtonText.classList.add('hidden');
              soldOutMessage.classList.remove('hidden');
              this.error = true;
              return;
            } else if (!this.cart) {
              this.incrementCartQuantity(formData);
              window.location = window.routes.cart_url;
              return;
            }

            this.stockRecoveryCount = 0;
            this.incrementCartQuantity(formData);
            const startMarker = CartPerformance.createStartingMarker('add:wait-for-subscribers');
            if (!this.error)
              publish(PUB_SUB_EVENTS.cartUpdate, {
                source: 'product-form',
                productVariantId: formData.get('id'),
                cartData: response,
              }).then(() => {
                CartPerformance.measureFromMarker('add:wait-for-subscribers', startMarker);
              });
            this.error = false;
            const quickAddModal = this.closest('quick-add-modal');
            if (quickAddModal) {
              document.body.addEventListener(
                'modalClosed',
                () => {
                  setTimeout(() => {
                    CartPerformance.measure("add:paint-updated-sections", () => {
                      this.cart.renderContents(response);
                    });
                  });
                },
                { once: true }
              );
              quickAddModal.hide(true);
            } else {
              CartPerformance.measure("add:paint-updated-sections", () => {
                this.cart.renderContents(response);
              });
            }
          })
          .catch((e) => {
            console.error(e);
          })
          .finally(() => {
            this.submitButton.classList.remove('loading');
            if (this.cart && this.cart.classList.contains('is-empty')) this.cart.classList.remove('is-empty');
            if (!this.error) this.submitButton.removeAttribute('aria-disabled');
            this.querySelector('.loading__spinner').classList.add('hidden');

            CartPerformance.measureFromEvent("add:user-action", evt);
            const cart_counter_bubble = document.querySelector(".cart-count-bubble");
            if(cart_counter_bubble){
              cart_counter_bubble.classList.add("pulse");
              setTimeout(() => {
                cart_counter_bubble.classList.remove("pulse");
              }, 2000);
            }
          });
      }

      handleErrorMessage(errorMessage = false) {
        if (this.hideErrors) return;

        this.errorMessageWrapper =
          this.errorMessageWrapper || this.querySelector('.product-form__error-message-wrapper');
        if (!this.errorMessageWrapper) return;
        this.errorMessage = this.errorMessage || this.errorMessageWrapper.querySelector('.product-form__error-message');

        this.errorMessageWrapper.toggleAttribute('hidden', !errorMessage);

        if (errorMessage) {
          this.errorMessage.textContent = errorMessage;
        }
      }

      getRemainingStock() {
        return this.getAddableStock();
      }

      normalizeStockIdentity(value) {
        return value?.replaceAll('quickadd-', '');
      }

      async refreshInventoryFromServer(variantId = this.variantIdInput.value) {
        const refreshUrl = this.dataset.stockRefreshUrl || this.dataset.stockProductUrl;
        const stockFormKey = this.normalizeStockIdentity(this.dataset.stockFormKey);
        const sectionId = this.normalizeStockIdentity(this.dataset.sectionId);
        if (!refreshUrl || !stockFormKey || !sectionId || !variantId) return false;

        const currentQuery =
          this.dataset.stockRefreshQuery === 'true' && refreshUrl === window.location.pathname
            ? window.location.search.replace(/^\?/, '')
            : '';
        const query = [
          currentQuery,
          `variant=${encodeURIComponent(variantId)}`,
          `section_id=${encodeURIComponent(sectionId)}`,
        ]
          .filter(Boolean)
          .join('&');
        const separator = refreshUrl.includes('?') ? '&' : '?';

        try {
          const response = await fetch(`${refreshUrl}${separator}${query}`);
          if (response.ok === false) return false;

          const html = new DOMParser().parseFromString(await response.text(), 'text/html');
          const sourceProductForm = Array.from(html.querySelectorAll('product-form[data-stock-form-key]')).find(
            (productForm) =>
              this.normalizeStockIdentity(productForm.dataset.stockFormKey) === stockFormKey &&
              String(productForm.dataset.stockVariantId) === String(variantId)
          );
          if (!sourceProductForm) return false;

          this.updateInventoryFrom(sourceProductForm);
          return true;
        } catch (_error) {
          return false;
        }
      }

      async recoverFromStockError(formData) {
        if (
          (this.dataset.stockLimit === undefined && this.dataset.productQuantityLimit === undefined) ||
          this.stockRecoveryCount >= 1
        )
          return false;
        const requestedQuantity = Math.max(parseInt(formData.get('quantity') || '1', 10), 1);
        if (!(await this.refreshInventoryFromServer(formData.get('id')))) return false;

        const addableStock = this.getAddableStock();
        if (addableStock === null || requestedQuantity <= addableStock) return false;

        this.stockRecoveryCount += 1;
        this.handleErrorMessage();
        this.showStockConfirmation(requestedQuantity, addableStock);
        return true;
      }

      getAddableStock() {
        if (this.dataset.stockLimit === undefined && this.dataset.productQuantityLimit === undefined) return null;
        const cartQuantity = Math.max(parseInt(this.dataset.stockCartQuantity, 10) || 0, 0);
        const productQuantityLimit = Math.max(parseInt(this.dataset.productQuantityLimit, 10) || 0, 0);
        const productCartQuantity = Math.max(parseInt(this.dataset.productCartQuantity, 10) || 0, 0);
        const stockIncrement = Math.max(parseInt(this.dataset.stockIncrement, 10) || 1, 1);
        const remainingStock =
          this.dataset.stockLimit === undefined
            ? Number.POSITIVE_INFINITY
            : Math.max((parseInt(this.dataset.stockLimit, 10) || 0) - cartQuantity, 0);
        const remainingProductQuantity = Math.max(productQuantityLimit - productCartQuantity, 0);
        const remainingQuantity = Math.min(remainingStock, remainingProductQuantity);
        const addableStock = Math.floor(remainingQuantity / stockIncrement) * stockIncrement;

        if (addableStock < this.getMinimumAddableStock()) return 0;
        return addableStock;
      }

      getMinimumAddableStock() {
        const cartQuantity = Math.max(parseInt(this.dataset.stockCartQuantity, 10) || 0, 0);
        const stockMin = Math.max(parseInt(this.dataset.stockMin, 10) || 1, 1);
        const stockIncrement = Math.max(parseInt(this.dataset.stockIncrement, 10) || 1, 1);
        const minimumNeeded = cartQuantity < stockMin ? stockMin - cartQuantity : stockIncrement;
        return Math.ceil(minimumNeeded / stockIncrement) * stockIncrement;
      }

      showStockConfirmation(requestedQuantity, remainingStock) {
        if (!this.stockConfirmation) {
          const message =
            remainingStock > 0
              ? `Only ${remainingStock} item(s) are available.`
              : 'All available stock is already in your cart.';
          this.handleErrorMessage(message);
          return;
        }
        const hasAvailableStock = remainingStock > 0;
        this.pendingStockQuantity = hasAvailableStock ? remainingStock : undefined;
        this.stockConfirmationRequested.textContent = String(requestedQuantity);
        this.stockConfirmationRemaining.textContent = String(remainingStock);
        this.stockConfirmationAvailable.hidden = !hasAvailableStock;
        this.stockConfirmationEmpty.hidden = hasAvailableStock;
        this.stockConfirmationQuantityField.hidden = !hasAvailableStock;
        this.stockConfirmationConfirm.hidden = !hasAvailableStock;
        this.stockConfirmationConfirm.disabled = false;
        if (hasAvailableStock) {
          this.stockConfirmationQuantity.min = String(this.getMinimumAddableStock());
          this.stockConfirmationQuantity.max = String(remainingStock);
          this.stockConfirmationQuantity.step = String(Math.max(parseInt(this.dataset.stockIncrement, 10) || 1, 1));
          this.stockConfirmationQuantity.value = String(remainingStock);
        }
        this.stockConfirmationCancel.textContent = hasAvailableStock ? 'Cancel' : 'Close';
        this.stockConfirmation.showModal();
        (hasAvailableStock ? this.stockConfirmationQuantity : this.stockConfirmationCancel)?.focus();
      }

      confirmAvailableStock() {
        if (this.pendingStockQuantity === undefined) return;
        if (!this.stockConfirmationQuantity.checkValidity()) {
          this.stockConfirmationQuantity.reportValidity();
          this.stockConfirmationQuantity.focus();
          return;
        }
        const selectedQuantity = parseInt(this.stockConfirmationQuantity.value, 10);
        if (!Number.isInteger(selectedQuantity) || selectedQuantity > this.pendingStockQuantity) return;
        this.stockConfirmationConfirm.disabled = true;
        this.confirmedStockQuantity = selectedQuantity;
        const quantityInput = this.form.elements.namedItem('quantity');
        if (quantityInput) quantityInput.value = String(this.confirmedStockQuantity);
        this.pendingStockQuantity = undefined;
        this.stockConfirmation.close();
        this.form.requestSubmit(this.submitButton);
      }

      cancelStockConfirmation() {
        this.pendingStockQuantity = undefined;
        this.stockConfirmation?.close();
      }

      onStockConfirmationEscape(event) {
        if (event.code === 'Escape') event.stopPropagation();
      }

      onStockConfirmationCancel(event) {
        event.stopPropagation();
        this.pendingStockQuantity = undefined;
      }

      onStockConfirmationClose() {
        if (this.submitButton.isConnected === false) return;
        const quickAddModal = this.closest('quick-add-modal');
        if (quickAddModal && !quickAddModal.hasAttribute('open')) return;
        this.submitButton.focus();
      }

      incrementCartQuantity(formData) {
        const currentQuantity = Math.max(parseInt(this.dataset.stockCartQuantity, 10) || 0, 0);
        const currentProductQuantity = Math.max(parseInt(this.dataset.productCartQuantity, 10) || 0, 0);
        const addedQuantity = Math.max(parseInt(formData.get('quantity') || '1', 10), 1);
        this.dataset.stockCartQuantity = String(currentQuantity + addedQuantity);
        this.dataset.productCartQuantity = String(currentProductQuantity + addedQuantity);
      }

      updateInventoryFrom(sourceProductForm) {
        const persistentAttributes = new Set([
          'data-stock-product-url',
          'data-stock-refresh-url',
          'data-stock-refresh-query',
          'data-stock-form-key',
        ]);
        for (const attribute of [
          'data-stock-product-url',
          'data-stock-refresh-url',
          'data-stock-refresh-query',
          'data-stock-form-key',
          'data-stock-variant-id',
          'data-stock-limit',
          'data-stock-cart-quantity',
          'data-stock-min',
          'data-stock-increment',
          'data-product-cart-quantity',
          'data-product-quantity-limit',
        ]) {
          if (sourceProductForm?.hasAttribute(attribute)) {
            this.setAttribute(attribute, sourceProductForm.getAttribute(attribute));
          } else if (!persistentAttributes.has(attribute)) {
            this.removeAttribute(attribute);
          }
        }
      }

      toggleSubmitButton(disable = true, text) {
        if (disable) {
          this.submitButton.setAttribute('disabled', 'disabled');
          if (text) this.submitButtonText.textContent = text;
        } else {
          this.submitButton.removeAttribute('disabled');
          this.submitButtonText.textContent = window.variantStrings.addToCart;
        }
      }

      get variantIdInput() {
        return this.form.querySelector('[name=id]');
      }
    }
  );
}
