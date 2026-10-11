const products = [
  {
    id: "monsoon-box-tee",
    name: "Monsoon Box Tee",
    type: "tee",
    fit: "oversized",
    price: 1890,
    tag: "Heavy GSM",
    detail: "240 GSM cotton jersey, drop shoulder, rib neck, street fit.",
    image: "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=900&q=80",
    sizes: ["XS", "S", "M", "L", "XL", "XXL"],
    colors: ["Ink", "Chilli", "Ivory"]
  },
  {
    id: "bandra-camp-shirt",
    name: "Bandra Camp Shirt",
    type: "shirt",
    fit: "relaxed",
    price: 3290,
    tag: "Resort collar",
    detail: "Open collar cotton shirt with coconut buttons and relaxed sleeves.",
    image: "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80",
    sizes: ["S", "M", "L", "XL", "XXL"],
    colors: ["Palm", "Sand", "Black"]
  },
  {
    id: "metro-oxford-shirt",
    name: "Metro Oxford Shirt",
    type: "shirt",
    fit: "regular",
    price: 2790,
    tag: "Office to evening",
    detail: "Crisp oxford weave, button-down collar, clean everyday shape.",
    image: "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=900&q=80",
    sizes: ["S", "M", "L", "XL", "XXL"],
    colors: ["White", "Sky", "Graphite"]
  },
  {
    id: "raasta-graphic-tee",
    name: "Raasta Graphic Tee",
    type: "tee",
    fit: "oversized",
    price: 2190,
    tag: "Limited demo",
    detail: "Soft cotton tee with original abstract placement print language.",
    image: "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=80",
    sizes: ["XS", "S", "M", "L", "XL"],
    colors: ["Black", "Cobalt", "Milk"]
  },
  {
    id: "linen-stand-shirt",
    name: "Linen Stand Shirt",
    type: "shirt",
    fit: "relaxed",
    price: 3690,
    tag: "Warm weather",
    detail: "Breathable cotton-linen blend with stand collar and curved hem.",
    image: "https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=900&q=80",
    sizes: ["S", "M", "L", "XL"],
    colors: ["Ecru", "Olive", "Indigo"]
  },
  {
    id: "training-rib-tee",
    name: "Training Rib Tee",
    type: "tee",
    fit: "regular",
    price: 1490,
    tag: "Everyday base",
    detail: "Ribbed neck, compact cotton, made for layering under shirts.",
    image: "https://images.unsplash.com/photo-1562157873-818bc0726f68?auto=format&fit=crop&w=900&q=80",
    sizes: ["XS", "S", "M", "L", "XL", "XXL"],
    colors: ["White", "Charcoal", "Red"]
  }
];

const rupee = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0
});

const state = {
  filter: "all",
  selections: Object.fromEntries(products.map((product) => [
    product.id,
    { size: product.sizes[1] || product.sizes[0], color: product.colors[0] }
  ])),
  cart: []
};

const grid = document.querySelector(".product-grid");
const cartPanel = document.querySelector(".cart-panel");
const cartItems = document.querySelector(".cart-items");
const cartEmpty = document.querySelector(".cart-empty");
const scrim = document.querySelector(".scrim");
const toast = document.querySelector(".toast");
const cartToggle = document.querySelector(".cart-toggle");
const soundToggle = document.querySelector(".sound-toggle");
let audioContext;
let musicTimer;

function renderProducts() {
  const filtered = products.filter((product) => {
    if (state.filter === "all") return true;
    if (state.filter === "oversized") return product.fit === "oversized";
    return product.type === state.filter;
  });

  grid.innerHTML = filtered.map((product) => {
    const selection = state.selections[product.id];
    return `
      <article class="product-card" data-product="${product.id}">
        <div class="product-media">
          <img src="${product.image}" alt="${product.name}">
          <span class="product-tag">${product.tag}</span>
        </div>
        <div class="product-body">
          <div class="product-topline">
            <h3 class="product-title">${product.name}</h3>
            <span class="price">${rupee.format(product.price)}</span>
          </div>
          <p class="product-details">${product.detail}</p>
          ${variantGroup(product, "size", product.sizes, selection.size)}
          ${variantGroup(product, "color", product.colors, selection.color)}
          <button class="add-button" type="button" data-add="${product.id}">Add to cart</button>
        </div>
      </article>
    `;
  }).join("");
}

function variantGroup(product, key, values, active) {
  return `
    <div class="variant-group">
      <span class="variant-label">${key}</span>
      <div class="variant-row">
        ${values.map((value) => `
          <button class="variant-button ${value === active ? "active" : ""}" type="button" data-product="${product.id}" data-variant="${key}" data-value="${value}" aria-pressed="${value === active}">
            ${value}
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function renderCart() {
  cartItems.innerHTML = state.cart.map((item, index) => `
    <article class="cart-item">
      <img src="${item.image}" alt="${item.name}">
      <div>
        <h3>${item.name}</h3>
        <p>${item.size} / ${item.color}</p>
        <p>${rupee.format(item.price)}</p>
      </div>
      <div class="qty">
        <button type="button" data-qty="${index}" data-delta="-1" aria-label="Decrease ${item.name} quantity">-</button>
        <span>${item.qty}</span>
        <button type="button" data-qty="${index}" data-delta="1" aria-label="Increase ${item.name} quantity">+</button>
      </div>
    </article>
  `).join("");

  const count = state.cart.reduce((sum, item) => sum + item.qty, 0);
  const subtotal = state.cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  document.querySelector(".cart-count").textContent = count;
  document.querySelector(".subtotal").textContent = rupee.format(subtotal);
  cartEmpty.classList.toggle("visible", count === 0);
}

function addToCart(productId) {
  const product = products.find((item) => item.id === productId);
  const selection = state.selections[productId];
  const existing = state.cart.find((item) => item.id === productId && item.size === selection.size && item.color === selection.color);
  if (existing) {
    existing.qty += 1;
  } else {
    state.cart.push({ ...product, ...selection, qty: 1 });
  }
  renderCart();
  openCart();
  showToast(`${product.name} added in ${selection.size}, ${selection.color}.`);
}

function openCart() {
  cartPanel.classList.add("open");
  cartPanel.setAttribute("aria-hidden", "false");
  cartToggle.setAttribute("aria-expanded", "true");
  scrim.hidden = false;
}

function closeCart() {
  cartPanel.classList.remove("open");
  cartPanel.setAttribute("aria-hidden", "true");
  cartToggle.setAttribute("aria-expanded", "false");
  scrim.hidden = true;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
}

function startMusic() {
  audioContext = audioContext || new AudioContext();
  const notes = [110, 146.83, 164.81, 220, 246.94, 293.66];
  let step = 0;
  musicTimer = window.setInterval(() => {
    const now = audioContext.currentTime;
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = step % 4 === 0 ? "triangle" : "sine";
    osc.frequency.value = notes[step % notes.length];
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.045, now + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
    osc.connect(gain).connect(audioContext.destination);
    osc.start(now);
    osc.stop(now + 0.24);
    step += 1;
  }, 220);
}

function stopMusic() {
  window.clearInterval(musicTimer);
  musicTimer = undefined;
}

document.querySelector(".filters").addEventListener("click", (event) => {
  const button = event.target.closest(".filter");
  if (!button) return;
  state.filter = button.dataset.filter;
  document.querySelectorAll(".filter").forEach((filter) => filter.classList.toggle("active", filter === button));
  renderProducts();
});

grid.addEventListener("click", (event) => {
  const variant = event.target.closest("[data-variant]");
  if (variant) {
    state.selections[variant.dataset.product][variant.dataset.variant] = variant.dataset.value;
    renderProducts();
    return;
  }
  const add = event.target.closest("[data-add]");
  if (add) addToCart(add.dataset.add);
});

cartItems.addEventListener("click", (event) => {
  const button = event.target.closest("[data-qty]");
  if (!button) return;
  const item = state.cart[Number(button.dataset.qty)];
  item.qty += Number(button.dataset.delta);
  state.cart = state.cart.filter((cartItem) => cartItem.qty > 0);
  renderCart();
});

cartToggle.addEventListener("click", openCart);
document.querySelector(".close-cart").addEventListener("click", closeCart);
scrim.addEventListener("click", closeCart);

document.querySelector(".checkout-button").addEventListener("click", () => {
  if (state.cart.length === 0) {
    showToast("Add a shirt or T-shirt before simulating checkout.");
    return;
  }
  showToast("Simulated checkout only: no payment, UPI, card, or address details collected.");
});

soundToggle.addEventListener("click", async () => {
  const enabled = soundToggle.getAttribute("aria-pressed") === "true";
  if (enabled) {
    stopMusic();
    soundToggle.setAttribute("aria-pressed", "false");
    document.querySelector(".sound-label").textContent = "Sound off";
  } else {
    startMusic();
    if (audioContext.state === "suspended") await audioContext.resume();
    soundToggle.setAttribute("aria-pressed", "true");
    document.querySelector(".sound-label").textContent = "Sound on";
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeCart();
});

renderProducts();
renderCart();
