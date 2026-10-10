'use strict';
// Content remains visible without JavaScript; motion is optional enhancement.
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
if (!motionPreference.matches && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.remove('motion-pending');
        observer.unobserve(entry.target);
      }
    }
  }, { threshold: 0.08 });
  let revealIndex = 0;
  for (const section of document.querySelectorAll('.reveal')) {
    if (section.style) section.style.setProperty('--reveal-delay', `${(revealIndex++ % 3) * 65}ms`);
    if (section.getBoundingClientRect().top > window.innerHeight) {
      section.classList.add('motion-pending');
      observer.observe(section);
    }
  }
  motionPreference.addEventListener('change', (event) => {
    if (event.matches) {
      document.querySelectorAll('.motion-pending').forEach((section) => section.classList.remove('motion-pending'));
      observer.disconnect();
    }
  });
}
const dialog = document.getElementById('case-dialog');
const caseContent = document.getElementById('case-content');
let previousFocus;
for (const button of document.querySelectorAll('[data-case]')) {
  button.addEventListener('click', () => {
    const template = document.getElementById(`case-${button.dataset.case}`);
    if (!template) return;
    previousFocus = button;
    caseContent.replaceChildren(template.content.cloneNode(true));
    dialog.showModal();
    dialog.scrollTop = 0;
    document.body.classList.add('dialog-open');
    document.getElementById('close-case').focus();
  });
}
document.getElementById('close-case').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => {
  const rect = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
});
dialog.addEventListener('close', () => {
  document.body.classList.remove('dialog-open');
  previousFocus?.focus();
});

const workFilters = document.querySelector('.work-filters');
if (workFilters) {
  workFilters.hidden = false;
  for (const filter of document.querySelectorAll('[data-filter]')) {
    filter.addEventListener('click', () => {
      for (const button of document.querySelectorAll('[data-filter]')) {
        button.setAttribute('aria-pressed', String(button === filter));
      }
      for (const project of document.querySelectorAll('[data-category]')) {
        project.hidden = filter.dataset.filter !== 'all' && !project.dataset.category.split(' ').includes(filter.dataset.filter);
        if (!project.hidden) {
          project.classList.remove('motion-pending');
          if (!motionPreference.matches && typeof project.animate === 'function') {
            project.animate([{ opacity: 0, transform: 'translateY(18px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 470, easing: 'cubic-bezier(.16,1,.3,1)' });
          }
        }
      }
    });
  }
}

// A lightweight reading-progress accent; no scroll interception or scroll-jacking.
if (document.documentElement && typeof window.requestAnimationFrame === 'function') {
  let scrollFramePending = false;
  const updateReadingProgress = () => {
    const root = document.documentElement;
    const distance = root.scrollHeight - window.innerHeight;
    const progress = distance > 0 ? Math.max(0, Math.min(1, window.scrollY / distance)) : 0;
    root.style.setProperty('--reading-progress', progress);
    scrollFramePending = false;
  };
  window.addEventListener('scroll', () => {
    if (!scrollFramePending) {
      scrollFramePending = true;
      window.requestAnimationFrame(updateReadingProgress);
    }
  }, { passive: true });
  window.addEventListener('resize', updateReadingProgress, { passive: true });
  updateReadingProgress();
}
