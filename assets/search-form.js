class SearchForm extends HTMLElement {
  constructor() {
    super();
    this.searchFormInitialized = false;
    this.searchInitializationObserver = null;

    if (this.constructor === SearchForm) this.ensureSearchFormInitialization();
  }

  ensureSearchFormInitialization() {
    if (this.initializeSearchForm()) return true;

    this.observeSearchInitialization(() => this.initializeSearchForm());
    return false;
  }

  observeSearchInitialization(initializer) {
    if (this.searchInitializationObserver) return;

    this.searchInitializationObserver = new MutationObserver(() => {
      if (!initializer()) return;

      this.searchInitializationObserver.disconnect();
      this.searchInitializationObserver = null;
    });
    this.searchInitializationObserver.observe(this, { childList: true, subtree: true });
  }

  initializeSearchForm() {
    if (this.searchFormInitialized) return true;

    this.input = this.querySelector('input[type="search"]');
    this.resetButton = this.querySelector('button[type="reset"]');

    if (!this.input?.form || !this.resetButton) return false;

    this.input.form.addEventListener('reset', this.onFormReset.bind(this));
    this.input.addEventListener(
      'input',
      debounce((event) => {
        this.onChange(event);
      }, 300).bind(this)
    );
    this.searchFormInitialized = true;
    return true;
  }

  toggleResetButton() {
    const resetIsHidden = this.resetButton.classList.contains('hidden');
    if (this.input.value.length > 0 && resetIsHidden) {
      this.resetButton.classList.remove('hidden');
    } else if (this.input.value.length === 0 && !resetIsHidden) {
      this.resetButton.classList.add('hidden');
    }
  }

  onChange() {
    this.toggleResetButton();
  }

  shouldResetForm() {
    return !document.querySelector('[aria-selected="true"] a');
  }

  onFormReset(event) {
    // Prevent default so the form reset doesn't set the value gotten from the url on page load
    event.preventDefault();
    // Don't reset if the user has selected an element on the predictive search dropdown
    if (this.shouldResetForm()) {
      this.input.value = '';
      this.input.focus();
      this.toggleResetButton();
    }
  }
}

customElements.define('search-form', SearchForm);
