'use strict';
(() => {
  const root = document.documentElement;
  const body = document.body;
  const motionButton = document.getElementById('motion-toggle');
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const roomy = window.matchMedia('(min-width: 960px) and (min-height: 720px)');
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const hero = document.querySelector('.photo-hero');
  const photo = document.querySelector('.portrait-stage');
  const reel = document.querySelector('.chapter-reel');
  const work = document.getElementById('work');
  const rail = work.querySelector('.project-grid');
  const railWindow = work.querySelector('.project-window');
  const navigation = work.querySelector('.rail-navigation');
  const positionLabel = document.getElementById('rail-position');
  const arrows = [...work.querySelectorAll('[data-rail-step]')];
  const cards = [...rail.querySelectorAll('.project')];
  let manualMotion = null;
  let enabled = !preference.matches;
  let railActive = false;
  let distance = 0;
  let frame = 0;
  let currentCard = 0;
  let shownCards = cards;
  cards.forEach((card, index) => card.dataset.sceneNumber = String(index + 1).padStart(2, '0'));
  const clamp = (n, a = 0, b = 1) => Math.min(b, Math.max(a, n));
  const headerHeight = () => window.innerWidth > 600 ? 68 : 62;
  function setLabel() {
    positionLabel.textContent = `${String(currentCard + 1).padStart(2, '0')} / ${String(shownCards.length).padStart(2, '0')}`;
    arrows.forEach(button => button.disabled = Number(button.dataset.railStep) < 0 ? currentCard === 0 : currentCard >= shownCards.length - 1);
  }
  function update() {
    frame = 0;
    if (!enabled) return;
    const heroRect = hero.getBoundingClientRect();
    const heroProgress = clamp(-heroRect.top / Math.max(heroRect.height, 1));
    hero.style.setProperty('--hero-scroll', heroProgress.toFixed(4));
    const reelRect = reel.getBoundingClientRect();
    const reelProgress = clamp((window.innerHeight - reelRect.top) / (window.innerHeight + reelRect.height));
    reel.style.setProperty('--reel-shift', `${Math.round(reelProgress * -360)}px`);
    if (!railActive) return;
    const workRect = work.getBoundingClientRect();
    const progress = clamp((headerHeight() - workRect.top) / Math.max(distance, 1));
    const offset = progress * distance;
    work.style.setProperty('--rail-x', `${-offset.toFixed(2)}px`);
    work.style.setProperty('--rail-progress', Math.max(.02, progress).toFixed(4));
    let nearest = 0;
    let closest = Infinity;
    shownCards.forEach((card, index) => {
      const relative = card.offsetLeft - offset;
      const proximity = Math.abs(relative);
      if (proximity < closest) { closest = proximity; nearest = index; }
      card.style.setProperty('--card-away', clamp(relative / (window.innerWidth * .7), -1, 1).toFixed(3));
    });
    if (progress >= .998) nearest = shownCards.length - 1;
    currentCard = nearest;
    setLabel();
  }
  function schedule() { if (!frame) frame = window.requestAnimationFrame(update); }
  function measure() {
    railActive = enabled && roomy.matches;
    work.classList.toggle('rail-active', railActive);
    navigation.hidden = !railActive;
    shownCards = cards.filter(card => !card.hidden);
    if (railActive) {
      cards.forEach(card => card.classList.remove('motion-pending'));
      distance = Math.max(0, rail.scrollWidth - railWindow.clientWidth);
      work.style.setProperty('--rail-height', `${Math.ceil(window.innerHeight - headerHeight() + distance)}px`);
    } else {
      distance = 0;
      work.style.removeProperty('--rail-height');
      work.style.removeProperty('--rail-x');
      cards.forEach(card => card.style.removeProperty('--card-away'));
    }
    schedule();
  }
  function applyMotion() {
    enabled = manualMotion === null ? !preference.matches : manualMotion;
    body.dataset.motion = enabled ? 'on' : 'off';
    motionButton.setAttribute('aria-pressed', String(enabled));
    motionButton.setAttribute('aria-label', enabled ? 'Pause decorative animation' : 'Enable decorative animation');
    motionButton.querySelector('span').textContent = enabled ? 'Motion on' : 'Motion off';
    motionButton.title = !enabled && preference.matches ? 'Your device prefers reduced motion. Select to enable animation.' : 'Toggle decorative motion';
    if (!enabled) {
      document.querySelectorAll('.motion-pending').forEach(element => element.classList.remove('motion-pending'));
      photo.style.removeProperty('--photo-pan-x');
      photo.style.removeProperty('--photo-pan-y');
    }
    measure();
  }
  motionButton.addEventListener('click', () => { manualMotion = !enabled; applyMotion(); });
  preference.addEventListener('change', () => { manualMotion = null; applyMotion(); });
  roomy.addEventListener('change', measure);
  window.addEventListener('resize', measure, { passive: true });
  window.addEventListener('scroll', schedule, { passive: true });
  function goToCard(index) {
    if (!railActive) return;
    const card = shownCards[clamp(index, 0, shownCards.length - 1)];
    const target = window.scrollY + work.getBoundingClientRect().top - headerHeight() + Math.min(card.offsetLeft, distance);
    window.scrollTo({ top: target, behavior: enabled ? 'smooth' : 'auto' });
  }
  arrows.forEach(button => button.addEventListener('click', () => goToCard(currentCard + Number(button.dataset.railStep))));
  rail.addEventListener('focusin', event => {
    if (!railActive) return;
    const card = event.target.closest('.project');
    if (!card) return;
    const rect = card.getBoundingClientRect();
    if (rect.left < 0 || rect.right > window.innerWidth) goToCard(shownCards.indexOf(card));
  });
  work.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    measure();
    if (railActive) {
      const target = window.scrollY + work.getBoundingClientRect().top - headerHeight();
      window.scrollTo({ top: target, behavior: 'auto' });
    }
  }));
  hero.addEventListener('pointermove', event => {
    if (!enabled || !finePointer.matches) return;
    const rect = photo.getBoundingClientRect();
    photo.style.setProperty('--photo-pan-x', `${((event.clientX - rect.left) / rect.width - .5) * 10}px`);
    photo.style.setProperty('--photo-pan-y', `${((event.clientY - rect.top) / rect.height - .5) * 7}px`);
  });
  hero.addEventListener('pointerleave', () => {
    photo.style.setProperty('--photo-pan-x', '0px');
    photo.style.setProperty('--photo-pan-y', '0px');
  });
  if ('IntersectionObserver' in window) {
    const timelineObserver = new IntersectionObserver(entries => entries.forEach(entry => entry.target.classList.toggle('is-in-view', entry.isIntersecting)), { threshold: .6 });
    document.querySelectorAll('.experience-item').forEach(item => timelineObserver.observe(item));
  }
  applyMotion();
  window.addEventListener('load', measure, { once: true });
  // Documented read-only diagnostics for QA, no network or tracking.
  window.portfolioMotion = Object.freeze({
    get state() { return { enabled, systemReducedMotion: preference.matches, railActive, distance, currentCard, visibleProjects: shownCards.length }; }
  });
})();
