if (!customElements.get('ripeness-select')) {
  customElements.define(
    'ripeness-select',
    class RipenessSelect extends HTMLElement {
      constructor() {
        super();
        this.initialized = false;
        this.suppressModalEscape = false;

        this.onTriggerClick = this.onTriggerClick.bind(this);
        this.onTriggerKeydown = this.onTriggerKeydown.bind(this);
        this.onListboxClick = this.onListboxClick.bind(this);
        this.onListboxKeydown = this.onListboxKeydown.bind(this);
        this.onKeyup = this.onKeyup.bind(this);
        this.onDocumentClick = this.onDocumentClick.bind(this);
        this.onNativeChange = this.syncFromNative.bind(this);
        this.onFormReset = () =>
          requestAnimationFrame(() => {
            this.syncFromNative();
            this.close();
          });
      }

      connectedCallback() {
        if (this.initialize()) return;

        this.pendingObserver = new MutationObserver(() => {
          if (!this.initialize()) return;
          this.pendingObserver?.disconnect();
          this.pendingObserver = null;
        });
        this.pendingObserver.observe(this.closest('form') || this, { childList: true, subtree: true });
      }

      disconnectedCallback() {
        this.pendingObserver?.disconnect();
        this.pendingObserver = null;
        this.submitStateObserver?.disconnect();
        this.submitStateObserver = null;
        if (!this.initialized) return;

        this.trigger.removeEventListener('click', this.onTriggerClick);
        this.trigger.removeEventListener('keydown', this.onTriggerKeydown);
        this.listbox.removeEventListener('click', this.onListboxClick);
        this.listbox.removeEventListener('keydown', this.onListboxKeydown);
        this.removeEventListener('keyup', this.onKeyup);
        this.nativeSelect.removeEventListener('change', this.onNativeChange);
        this.form.removeEventListener('reset', this.onFormReset);
        document.removeEventListener('click', this.onDocumentClick);
        this.initialized = false;
      }

      initialize() {
        if (this.initialized) return true;

        const nativeSelect = this.querySelector('[data-ripeness-select-native]');
        const trigger = this.querySelector('[data-ripeness-select-trigger]');
        const value = this.querySelector('[data-ripeness-select-value]');
        const listbox = this.querySelector('[data-ripeness-select-listbox]');
        const options = Array.from(this.querySelectorAll('[data-ripeness-select-option]'));
        const form = this.closest('form');
        const submitButton = form?.querySelector('[data-ripeness-submit]');
        if (!nativeSelect || !trigger || !value || !listbox || !form || !submitButton || !options.length) return false;

        this.nativeSelect = nativeSelect;
        this.trigger = trigger;
        this.value = value;
        this.listbox = listbox;
        this.options = options;
        this.form = form;
        this.submitButton = submitButton;
        this.placeholder = nativeSelect.options[0]?.textContent?.trim() || '';

        this.trigger.addEventListener('click', this.onTriggerClick);
        this.trigger.addEventListener('keydown', this.onTriggerKeydown);
        this.listbox.addEventListener('click', this.onListboxClick);
        this.listbox.addEventListener('keydown', this.onListboxKeydown);
        this.addEventListener('keyup', this.onKeyup);
        this.nativeSelect.addEventListener('change', this.onNativeChange);
        this.form.addEventListener('reset', this.onFormReset);
        document.addEventListener('click', this.onDocumentClick);
        this.submitStateObserver = new MutationObserver(() => {
          if (!this.nativeSelect.value && this.submitButton.getAttribute('aria-disabled') !== 'true') {
            this.submitButton.setAttribute('aria-disabled', 'true');
          }
        });
        this.submitStateObserver.observe(this.submitButton, {
          attributes: true,
          attributeFilter: ['aria-disabled'],
        });
        this.initialized = true;
        this.syncFromNative();
        return true;
      }

      onTriggerClick() {
        if (this.hasAttribute('open')) {
          this.close();
        } else {
          this.open();
        }
      }

      onTriggerKeydown(event) {
        switch (event.key) {
          case 'ArrowDown':
            event.preventDefault();
            this.open(0);
            break;
          case 'ArrowUp':
            event.preventDefault();
            this.open(this.options.length - 1);
            break;
          case 'Home':
            event.preventDefault();
            this.open(0);
            break;
          case 'End':
            event.preventDefault();
            this.open(this.options.length - 1);
            break;
          case 'Enter':
          case ' ':
            event.preventDefault();
            this.open();
            break;
          case 'Escape':
            if (!this.hasAttribute('open')) return;
            event.preventDefault();
            event.stopPropagation();
            this.suppressModalEscape = true;
            this.close(true);
            break;
        }
      }

      onListboxClick(event) {
        const option = event.target.closest('[data-ripeness-select-option]');
        if (option) this.selectOption(option);
      }

      onListboxKeydown(event) {
        const option = event.target.closest('[data-ripeness-select-option]');
        if (!option) return;
        const index = this.options.indexOf(option);

        switch (event.key) {
          case 'ArrowDown':
            event.preventDefault();
            this.focusOption((index + 1) % this.options.length);
            break;
          case 'ArrowUp':
            event.preventDefault();
            this.focusOption((index - 1 + this.options.length) % this.options.length);
            break;
          case 'Home':
            event.preventDefault();
            this.focusOption(0);
            break;
          case 'End':
            event.preventDefault();
            this.focusOption(this.options.length - 1);
            break;
          case 'Enter':
          case ' ':
            event.preventDefault();
            this.selectOption(option);
            break;
          case 'Escape':
            event.preventDefault();
            event.stopPropagation();
            this.suppressModalEscape = true;
            this.close(true);
            break;
          case 'Tab':
            this.close();
            break;
        }
      }

      onDocumentClick(event) {
        if (this.hasAttribute('open') && !this.contains(event.target)) this.close();
      }

      onKeyup(event) {
        if (event.code.toUpperCase() !== 'ESCAPE' || !this.suppressModalEscape) return;
        event.stopPropagation();
        this.suppressModalEscape = false;
      }

      open(focusIndex) {
        if (!this.options.length) return;
        this.setAttribute('open', '');
        this.trigger.setAttribute('aria-expanded', 'true');
        this.listbox.setAttribute('aria-hidden', 'false');

        const selectedIndex = this.options.findIndex((option) => option.getAttribute('aria-selected') === 'true');
        const targetIndex = Number.isInteger(focusIndex) ? focusIndex : Math.max(selectedIndex, 0);
        requestAnimationFrame(() => {
          if (this.hasAttribute('open')) this.focusOption(targetIndex);
        });
      }

      close(restoreFocus = false) {
        this.removeAttribute('open');
        this.trigger.setAttribute('aria-expanded', 'false');
        this.listbox.setAttribute('aria-hidden', 'true');
        this.options.forEach((option) => option.setAttribute('tabindex', '-1'));
        if (restoreFocus) this.trigger.focus();
      }

      focusOption(index) {
        const option = this.options[index];
        if (!option) return;
        this.options.forEach((item) => item.setAttribute('tabindex', '-1'));
        option.setAttribute('tabindex', '0');
        option.focus();
      }

      selectOption(option) {
        this.nativeSelect.value = option.dataset.value;
        this.nativeSelect.dispatchEvent(new Event('change', { bubbles: true }));
        this.close(true);
      }

      syncFromNative() {
        const selectedOption = this.options.find((option) => option.dataset.value === this.nativeSelect.value);
        this.options.forEach((option) => {
          option.setAttribute('aria-selected', option === selectedOption ? 'true' : 'false');
        });
        this.value.textContent = selectedOption?.textContent?.trim() || this.placeholder;
        this.submitButton.setAttribute('aria-disabled', String(!this.nativeSelect.value));
      }
    }
  );
}

if (!customElements.get('quick-add-modal')) {
  customElements.define(
    'quick-add-modal',
    class QuickAddModal extends ModalDialog {
      constructor() {
        super();
        this.modalContent = this.querySelector('[id^="QuickAddInfo-"]');

        this.addEventListener('product-info:loaded', ({ target }) => {
          target.addPreProcessCallback(this.preprocessHTML.bind(this));
        });
      }

      hide(preventFocus = false) {
        const cartNotification = document.querySelector('cart-notification') || document.querySelector('cart-drawer');
        if (cartNotification) cartNotification.setActiveElement(this.openedBy);

        if (this.hasAttribute('data-ripeness-static')) {
          this.modalContent.querySelector('form')?.reset();
          const errorWrapper = this.modalContent.querySelector('.product-form__error-message-wrapper');
          if (errorWrapper) errorWrapper.hidden = true;
        } else {
          this.modalContent.innerHTML = '';
        }

        if (preventFocus) this.openedBy = null;
        super.hide();
      }

      show(opener) {
        if (this.hasAttribute('data-ripeness-static')) {
          const sourceQuantity = opener.closest('quantity-input-custom')?.querySelector('.quantity__input')?.value;
          const modalQuantity = this.querySelector('[data-ripeness-modal-quantity]');

          if (sourceQuantity && modalQuantity) modalQuantity.value = sourceQuantity;

          super.show(opener);
          this.querySelector('[id^="ModalClose-Ripeness-"]')?.focus();
          return;
        }

        opener.setAttribute('aria-disabled', true);
        opener.classList.add('loading');
        opener.querySelector('.loading__spinner').classList.remove('hidden');

        fetch(opener.getAttribute('data-product-url'))
          .then((response) => response.text())
          .then((responseText) => {
            const responseHTML = new DOMParser().parseFromString(responseText, 'text/html');
            const productElement = responseHTML.querySelector('product-info');

            this.preprocessHTML(productElement);
            HTMLUpdateUtility.setInnerHTML(this.modalContent, productElement.outerHTML);

            if (window.Shopify && Shopify.PaymentButton) {
              Shopify.PaymentButton.init();
            }
            if (window.ProductModel) window.ProductModel.loadShopifyXR();

            super.show(opener);
          })
          .finally(() => {
            opener.removeAttribute('aria-disabled');
            opener.classList.remove('loading');
            opener.querySelector('.loading__spinner').classList.add('hidden');
          });
      }

      preprocessHTML(productElement) {
        productElement.classList.forEach((classApplied) => {
          if (classApplied.startsWith('color-') || classApplied === 'gradient')
            this.modalContent.classList.add(classApplied);
        });
        this.preventDuplicatedIDs(productElement);
        this.removeDOMElements(productElement);
        this.removeGalleryListSemantic(productElement);
        this.updateImageSizes(productElement);
        this.preventVariantURLSwitching(productElement);
      }

      preventVariantURLSwitching(productElement) {
        productElement.setAttribute('data-update-url', 'false');
      }

      removeDOMElements(productElement) {
        const pickupAvailability = productElement.querySelector('pickup-availability');
        if (pickupAvailability) pickupAvailability.remove();

        const productModal = productElement.querySelector('product-modal');
        if (productModal) productModal.remove();

        const modalDialog = productElement.querySelectorAll('modal-dialog');
        if (modalDialog) modalDialog.forEach((modal) => modal.remove());
      }

      preventDuplicatedIDs(productElement) {
        const sectionId = productElement.dataset.section;

        const oldId = sectionId;
        const newId = `quickadd-${sectionId}`;
        productElement.innerHTML = productElement.innerHTML.replaceAll(oldId, newId);
        Array.from(productElement.attributes).forEach((attribute) => {
          if (attribute.value.includes(oldId)) {
            productElement.setAttribute(attribute.name, attribute.value.replace(oldId, newId));
          }
        });

        productElement.dataset.originalSection = sectionId;
      }

      removeGalleryListSemantic(productElement) {
        const galleryList = productElement.querySelector('[id^="Slider-Gallery"]');
        if (!galleryList) return;

        galleryList.setAttribute('role', 'presentation');
        galleryList.querySelectorAll('[id^="Slide-"]').forEach((li) => li.setAttribute('role', 'presentation'));
      }

      updateImageSizes(productElement) {
        const product = productElement.querySelector('.product');
        const desktopColumns = product?.classList.contains('product--columns');
        if (!desktopColumns) return;

        const mediaImages = product.querySelectorAll('.product__media img');
        if (!mediaImages.length) return;

        let mediaImageSizes =
          '(min-width: 1000px) 715px, (min-width: 750px) calc((100vw - 11.5rem) / 2), calc(100vw - 4rem)';

        if (product.classList.contains('product--medium')) {
          mediaImageSizes = mediaImageSizes.replace('715px', '605px');
        } else if (product.classList.contains('product--small')) {
          mediaImageSizes = mediaImageSizes.replace('715px', '495px');
        }

        mediaImages.forEach((img) => img.setAttribute('sizes', mediaImageSizes));
      }
    }
  );

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-ripeness-modal]');
    if (!button || button.getAttribute('aria-disabled') === 'true') return;

    const modal = document.querySelector(button.dataset.ripenessModal);
    if (!modal) return;

    event.preventDefault();
    modal.show(button);
  });
}
