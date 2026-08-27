document.querySelectorAll('a[href^="#"]').forEach((link) =>
  link.addEventListener("click", (event) => {
    const target = document.querySelector(link.getAttribute("href"));
    if (target) {
      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth" });
    }
  }),
);

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    });
  },
  { threshold: 0.12 },
);
document
  .querySelectorAll(".section, .product-section, .app-card, .workflow article, .feature-grid article")
  .forEach((element, index) => {
    element.classList.add("reveal");
    element.dataset.revealDelay = String(index % 4);
    observer.observe(element);
  });

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!reduceMotion) {
  document.body.classList.add("motion-ready");

  const progress = document.createElement("div");
  progress.className = "scroll-progress";
  document.body.append(progress);

  const cursorGlow = document.createElement("div");
  cursorGlow.className = "cursor-glow";
  document.body.append(cursorGlow);

  const particleLayer = document.createElement("div");
  particleLayer.className = "particle-layer";
  particleLayer.setAttribute("aria-hidden", "true");
  for (let index = 0; index < 28; index += 1) {
    const particle = document.createElement("i");
    particle.style.setProperty("--x", `${(index * 37) % 100}%`);
    particle.style.setProperty("--size", `${2 + (index % 5)}px`);
    particle.style.setProperty("--duration", `${8 + (index % 8)}s`);
    particle.style.setProperty("--delay", `${-(index % 11)}s`);
    particleLayer.append(particle);
  }
  document.body.append(particleLayer);

  let pointerX = innerWidth / 2;
  let pointerY = innerHeight / 2;
  let glowX = pointerX;
  let glowY = pointerY;
  let scrollTicking = false;

  addEventListener("pointermove", (event) => {
    pointerX = event.clientX;
    pointerY = event.clientY;
  });

  const animateGlow = () => {
    glowX += (pointerX - glowX) * 0.14;
    glowY += (pointerY - glowY) * 0.14;
    cursorGlow.style.transform = `translate3d(${glowX}px, ${glowY}px, 0)`;
    requestAnimationFrame(animateGlow);
  };
  animateGlow();

  const updateScrollEffects = () => {
    const maxScroll = document.documentElement.scrollHeight - innerHeight;
    progress.style.transform = `scaleX(${maxScroll > 0 ? scrollY / maxScroll : 0})`;
    const phones = document.querySelector(".phones");
    if (phones) phones.style.setProperty("--scroll-shift", `${Math.min(scrollY * 0.055, 34)}px`);
    scrollTicking = false;
  };

  addEventListener("scroll", () => {
    if (!scrollTicking) {
      requestAnimationFrame(updateScrollEffects);
      scrollTicking = true;
    }
  }, { passive: true });
  updateScrollEffects();

  document
    .querySelectorAll(".app-card, .compare-grid article, .workflow article, .feature-grid article")
    .forEach((card) => {
      card.classList.add("tilt-card");
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        const rotateY = ((event.clientX - rect.left) / rect.width - 0.5) * 10;
        const rotateX = ((event.clientY - rect.top) / rect.height - 0.5) * -10;
        card.style.setProperty("--rx", `${rotateX}deg`);
        card.style.setProperty("--ry", `${rotateY}deg`);
        card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
        card.style.setProperty("--my", `${event.clientY - rect.top}px`);
      });
      card.addEventListener("pointerleave", () => {
        card.style.setProperty("--rx", "0deg");
        card.style.setProperty("--ry", "0deg");
      });
    });

  document.querySelectorAll(".button, .nav-cta").forEach((button) => {
    button.addEventListener("pointermove", (event) => {
      const rect = button.getBoundingClientRect();
      button.style.setProperty("--magnet-x", `${(event.clientX - rect.left - rect.width / 2) * 0.12}px`);
      button.style.setProperty("--magnet-y", `${(event.clientY - rect.top - rect.height / 2) * 0.12}px`);
    });
    button.addEventListener("pointerleave", () => {
      button.style.setProperty("--magnet-x", "0px");
      button.style.setProperty("--magnet-y", "0px");
    });
  });
}
