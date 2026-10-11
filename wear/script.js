const products = [
  {
    id: "storm-overshirt",
    name: "Storm Overshirt",
    type: "shirt",
    price: 3490,
    detail: "Relaxed black overshirt, red stitch language, cotton twill feel.",
    image: "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80",
    sizes: ["S", "M", "L", "XL", "XXL"],
    colors: ["Black/Red", "Graphite", "Ivory"]
  },
  {
    id: "match-tee",
    name: "Match Graphic Tee",
    type: "tee",
    price: 1990,
    detail: "Heavy cotton tee with oversized fit and original stripe graphic.",
    image: "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=80",
    sizes: ["XS", "S", "M", "L", "XL", "XXL"],
    colors: ["Black", "Chilli", "White"]
  },
  {
    id: "tempo-shirt",
    name: "Tempo Poplin Shirt",
    type: "shirt",
    price: 2890,
    detail: "Crisp city shirt with curved hem, made for day-to-night wear.",
    image: "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=900&q=80",
    sizes: ["S", "M", "L", "XL", "XXL"],
    colors: ["White", "Sky", "Black"]
  }
];

const rupee = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0
});

const state = {
  active: products[0].id,
  filter: "all",
  cart: [],
  selections: Object.fromEntries(products.map((product) => [
    product.id,
    { size: product.sizes[1] || product.sizes[0], color: product.colors[0] }
  ]))
};

const root = document.documentElement;
const title = document.querySelector("#product-title");
const price = document.querySelector(".price");
const productSelector = document.querySelector(".products");
const sizeSelector = document.querySelector(".sizes");
const colorSelector = document.querySelector(".colors");
const grid = document.querySelector(".catalog-grid");
const cartPanel = document.querySelector(".cart-panel");
const cartItems = document.querySelector(".cart-items");
const toast = document.querySelector(".toast");
let audioContext;
let musicTimer;

function activeProduct() {
  return products.find((product) => product.id === state.active);
}

function renderSelectors() {
  const product = activeProduct();
  const selection = state.selections[product.id];
  title.textContent = product.name;
  price.textContent = rupee.format(product.price);
  productSelector.innerHTML = products.map((item) => button(item.name, item.id, "product", item.id === product.id)).join("");
  sizeSelector.innerHTML = product.sizes.map((size) => button(size, size, "size", selection.size === size)).join("");
  colorSelector.innerHTML = product.colors.map((color) => button(color, color, "color", selection.color === color)).join("");
  document.querySelectorAll(".hero-product").forEach((image) => image.classList.toggle("active", image.dataset.productImage === product.id));
}

function button(label, value, kind, active) {
  return `<button class="${active ? "active" : ""}" type="button" data-kind="${kind}" data-value="${value}" aria-pressed="${active}">${label}</button>`;
}

function renderCatalog() {
  const visible = products.filter((product) => state.filter === "all" || product.type === state.filter);
  grid.innerHTML = visible.map((product) => `
    <article class="card">
      <img src="${product.image}" alt="${product.name}">
      <div class="card-body">
        <h3>${product.name}</h3>
        <p>${product.detail}</p>
        <p><strong>${rupee.format(product.price)}</strong></p>
        <button class="add-button" type="button" data-pick="${product.id}">Select drop</button>
      </div>
    </article>
  `).join("");
}

function renderCart() {
  cartItems.innerHTML = state.cart.map((item, index) => `
    <article class="cart-row">
      <img src="${item.image}" alt="${item.name}">
      <div>
        <h3>${item.name}</h3>
        <p>${item.size} / ${item.color}</p>
        <p>${rupee.format(item.price)}</p>
      </div>
      <div class="qty">
        <button type="button" data-qty="${index}" data-delta="-1" aria-label="Decrease quantity">-</button>
        <span>${item.qty}</span>
        <button type="button" data-qty="${index}" data-delta="1" aria-label="Increase quantity">+</button>
      </div>
    </article>
  `).join("");
  const count = state.cart.reduce((sum, item) => sum + item.qty, 0);
  const subtotal = state.cart.reduce((sum, item) => sum + item.qty * item.price, 0);
  document.querySelectorAll(".cart-count").forEach((el) => { el.textContent = count; });
  document.querySelector(".subtotal").textContent = rupee.format(subtotal);
  document.querySelector(".cart-empty").hidden = count !== 0;
}

function addToCart(productId = state.active) {
  const product = products.find((item) => item.id === productId);
  const selection = state.selections[product.id];
  const existing = state.cart.find((item) => item.id === product.id && item.size === selection.size && item.color === selection.color);
  if (existing) existing.qty += 1;
  else state.cart.push({ ...product, ...selection, qty: 1 });
  renderCart();
  openCart();
  showToast(`${product.name} added: ${selection.size}, ${selection.color}.`);
}

function openCart() {
  cartPanel.classList.add("open");
}

function closeCart() {
  cartPanel.classList.remove("open");
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function updateScrollScene() {
  const max = document.querySelector(".scroll-stage").offsetHeight - innerHeight;
  const progress = Math.min(1, Math.max(0, scrollY / max));
  root.style.setProperty("--zoom", (1 + progress * 1.95).toFixed(3));
  root.style.setProperty("--deck-x", `${Math.max(0, 120 - progress * 220)}%`);
  document.querySelector(".copy-one").style.setProperty("--copy-opacity", progress > 0.15 && progress < 0.52 ? 1 : 0);
  document.querySelector(".copy-one").style.setProperty("--copy-x", `${Math.round(progress * -160)}`);
  document.querySelector(".copy-two").style.setProperty("--copy-opacity", progress > 0.42 && progress < 0.78 ? 1 : 0);
  document.querySelector(".copy-two").style.setProperty("--copy-y", `${Math.round((progress - 0.42) * -220)}`);
  document.querySelector(".copy-three").style.setProperty("--copy-opacity", progress > 0.72 ? 1 : 0);
}

function startMusic() {
  audioContext = audioContext || new AudioContext();
  const notes = [55, 82.41, 110, 123.47, 146.83, 164.81];
  let step = 0;
  musicTimer = setInterval(() => {
    const now = audioContext.currentTime;
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = step % 3 === 0 ? "sawtooth" : "triangle";
    osc.frequency.value = notes[step % notes.length];
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.035, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
    osc.connect(gain).connect(audioContext.destination);
    osc.start(now);
    osc.stop(now + 0.2);
    step += 1;
  }, 185);
}

function stopMusic() {
  clearInterval(musicTimer);
  musicTimer = undefined;
}

document.addEventListener("click", async (event) => {
  const selectorButton = event.target.closest("[data-kind]");
  if (selectorButton) {
    const kind = selectorButton.dataset.kind;
    const value = selectorButton.dataset.value;
    if (kind === "product") state.active = value;
    if (kind === "size") state.selections[state.active].size = value;
    if (kind === "color") state.selections[state.active].color = value;
    renderSelectors();
    return;
  }

  const pick = event.target.closest("[data-pick]");
  if (pick) {
    state.active = pick.dataset.pick;
    renderSelectors();
    scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  if (event.target.closest(".add-button") && event.target.closest(".buy-deck")) addToCart();
  if (event.target.closest(".cart-fab") || event.target.closest('.bottom-hud a[href="#cart-panel"]')) openCart();
  if (event.target.closest(".close-cart")) closeCart();

  const filter = event.target.closest(".filter");
  if (filter) {
    state.filter = filter.dataset.filter;
    document.querySelectorAll(".filter").forEach((button) => button.classList.toggle("active", button === filter));
    renderCatalog();
  }

  const qty = event.target.closest("[data-qty]");
  if (qty) {
    const item = state.cart[Number(qty.dataset.qty)];
    item.qty += Number(qty.dataset.delta);
    state.cart = state.cart.filter((cartItem) => cartItem.qty > 0);
    renderCart();
  }

  if (event.target.closest(".checkout-button")) {
    showToast(state.cart.length ? "Simulated checkout only. No payment, UPI, card, or address details collected." : "Add a shirt or T-shirt before simulating checkout.");
  }

  const sound = event.target.closest(".sound-toggle");
  if (sound) {
    const on = sound.getAttribute("aria-pressed") === "true";
    if (on) {
      stopMusic();
      sound.setAttribute("aria-pressed", "false");
      sound.textContent = "CLICK TO ENABLE SOUND";
    } else {
      startMusic();
      if (audioContext.state === "suspended") await audioContext.resume();
      sound.setAttribute("aria-pressed", "true");
      sound.textContent = "SOUND ON / MUTE";
    }
  }
});

addEventListener("scroll", updateScrollScene, { passive: true });
addEventListener("resize", updateScrollScene);
addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeCart();
});

renderSelectors();
renderCatalog();
renderCart();
updateScrollScene();
