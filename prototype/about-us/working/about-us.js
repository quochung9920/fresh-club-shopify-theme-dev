(() => {
  'use strict';

  const root = document.querySelector('[data-about-us-root]');
  if (!root || typeof window.gsap === 'undefined') return;

  const targets = [
    ...root.querySelectorAll(
      '.hero-lede, .hero-photo, .value-card, .stats-eyebrow, .stat, .story-heading, .story-photo, .story-text, .day-heading, .step, .cta-copy, .cta > .btn'
    ),
  ];

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  const pending = new Set(targets);
  const reveal = (element) => {
    if (!pending.delete(element)) return;
    window.gsap.to(element, {
      autoAlpha: 1,
      y: 0,
      duration: 0.65,
      ease: 'power2.out',
      clearProps: 'transform,opacity,visibility',
    });
  };

  window.gsap.set(targets, { autoAlpha: 0, y: 24 });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        reveal(entry.target);
      });
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }
  );

  targets.forEach((target) => observer.observe(target));

  const cleanup = () => {
    observer.disconnect();
    window.gsap.killTweensOf(targets);
    window.gsap.set(targets, { clearProps: 'all' });
    pending.clear();
  };

  window.addEventListener('pagehide', cleanup, { once: true });
})();
