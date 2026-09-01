(() => {
  'use strict';

  const RUNTIME_KEY = '__freshClubAboutUsRuntime';
  if (window[RUNTIME_KEY]) return;
  window[RUNTIME_KEY] = true;

  const SELECTOR = 'freshclub-about-us';
  const TARGETS =
    '.fc-hero-lede, .fc-hero-photo, .fc-value-card, .fc-stats-eyebrow, .fc-stat, .fc-story-heading, .fc-story-photo, .fc-story-text, .fc-day-heading, .fc-step, .fc-cta-copy, .fc-cta > .fc-btn';

  class FreshClubAboutUs extends HTMLElement {
    connectedCallback() {
      this.initialize();
    }

    disconnectedCallback() {
      this.destroy();
    }

    initialize() {
      this.destroy();
      this.setupMenu();
      if (typeof window.gsap === 'undefined') return;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

      this.targets = [...this.querySelectorAll(TARGETS)];
      this.pending = new Set(this.targets);
      window.gsap.set(this.targets, { autoAlpha: 0, y: 24 });

      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            this.observer?.unobserve(entry.target);
            this.reveal(entry.target);
          });
        },
        { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }
      );

      this.targets.forEach((target) => this.observer.observe(target));
    }

    setupMenu() {
      this.menuButton = this.querySelector('.fc-menu-btn');
      this.mobileMenu = this.querySelector('.fc-mobile-nav:not(.fc-mobile-nav--noscript)');
      if (!this.menuButton || !this.mobileMenu) return;

      this.handleMenuClick = () => this.setMenuOpen(this.mobileMenu.hidden);
      this.handleMenuKeydown = (event) => {
        if (event.key === 'Escape' && !this.mobileMenu.hidden) {
          this.setMenuOpen(false);
          this.menuButton.focus();
        }
      };
      this.handleMenuNavigation = (event) => {
        if (event.target.closest?.('a')) this.setMenuOpen(false);
      };
      this.menuButton.addEventListener('click', this.handleMenuClick);
      this.mobileMenu.addEventListener('click', this.handleMenuNavigation);
      this.addEventListener('keydown', this.handleMenuKeydown);
    }

    setMenuOpen(open) {
      if (!this.menuButton || !this.mobileMenu) return;
      this.mobileMenu.hidden = !open;
      this.menuButton.setAttribute('aria-expanded', String(open));
      this.menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      if (open) this.mobileMenu.querySelector('a')?.focus();
    }

    reveal(element) {
      if (!this.pending?.delete(element)) return;
      window.gsap.to(element, {
        autoAlpha: 1,
        y: 0,
        duration: 0.65,
        ease: 'power2.out',
        clearProps: 'transform,opacity,visibility',
      });
    }

    destroy() {
      this.menuButton?.removeEventListener('click', this.handleMenuClick);
      this.mobileMenu?.removeEventListener('click', this.handleMenuNavigation);
      this.removeEventListener('keydown', this.handleMenuKeydown);
      if (this.menuButton && this.mobileMenu) this.setMenuOpen(false);
      this.observer?.disconnect();
      if (this.targets?.length && typeof window.gsap !== 'undefined') {
        window.gsap.killTweensOf(this.targets);
        window.gsap.set(this.targets, { clearProps: 'all' });
      }
      this.pending?.clear();
      this.targets = [];
      this.observer = null;
      this.menuButton = null;
      this.mobileMenu = null;
      this.handleMenuClick = null;
      this.handleMenuKeydown = null;
      this.handleMenuNavigation = null;
    }
  }

  if (!customElements.get(SELECTOR)) {
    customElements.define(SELECTOR, FreshClubAboutUs);
  }

  document.addEventListener('shopify:section:load', (event) => {
    event.target.querySelectorAll(SELECTOR).forEach((element) => element.initialize());
  });

  document.addEventListener('shopify:section:unload', (event) => {
    event.target.querySelectorAll(SELECTOR).forEach((element) => element.destroy());
  });
})();
