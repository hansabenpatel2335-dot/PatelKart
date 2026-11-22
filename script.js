const products = [
  { id: 1, name: "Wisha Wozzariter", type: "book", category: "books", price: 1000, icon: "book", label: "01", note: "A story worth keeping" },
  { id: 2, name: "Classic Toy Car", type: "toy", category: "play", price: 5, icon: "car", label: "02", note: "Pocket-sized adventure" },
  { id: 3, name: "Studio Pen Set", type: "pens", category: "play", price: 94.50, icon: "pens", label: "03", note: "Ideas start here" },
  { id: 4, name: "Sunset Bouquet", type: "flowers", category: "home", price: 194, icon: "flowers", label: "04", note: "Bring colour indoors" },
  { id: 5, name: "Electric Guitar", type: "guitar", category: "play", price: 5257, icon: "guitar", label: "05", note: "Make some noise" }
];

let cart = JSON.parse(localStorage.getItem("patelkart-cart") || "[]");

const formatPrice = (price) => `₹${price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

function productIllustration(product) {
  if (product.icon === "book") return `<div class="art art-book"><div class="book-cover"><span>Wisha</span><strong>Wozza-<br>riter</strong><i>By PatelKart</i></div></div>`;
  if (product.icon === "car") return `<div class="art art-car"><div class="car"><div class="car-top"></div><div class="car-body"><i></i><i></i></div><span class="wheel left"></span><span class="wheel right"></span></div></div>`;
  if (product.icon === "pens") return `<div class="art art-pens"><div class="pen p1"><i></i></div><div class="pen p2"><i></i></div><div class="pen p3"><i></i></div><div class="pen p4"><i></i></div></div>`;
  if (product.icon === "flowers") return `<div class="art art-flowers"><div class="vase"><i></i><i></i><i></i></div><div class="stem s-a"></div><div class="stem s-b"></div><div class="stem s-c"></div><div class="bloom b-a">✿</div><div class="bloom b-b">✿</div><div class="bloom b-c">✿</div></div>`;
  return `<div class="art art-guitar"><div class="mini-guitar"><div class="mini-neck"></div><div class="mini-head"></div><div class="mini-body"><i></i></div></div></div>`;
}

function renderProducts(filter = "all") {
  const grid = document.getElementById("productGrid");
  const visible = filter === "all" ? products : products.filter((product) => product.category === filter);
  grid.innerHTML = visible.map((product) => `
    <article class="product-card">
      <div class="product-image">
        <span class="product-number">${product.label}</span>
        ${productIllustration(product)}
      </div>
      <div class="product-info">
        <p>${product.note}</p>
        <h3>${product.name}</h3>
        <div class="product-bottom">
          <strong>${formatPrice(product.price)}</strong>
          <button class="add-button" data-id="${product.id}" aria-label="Add ${product.name} to cart">
            <span>Add</span><span class="plus">+</span>
          </button>
        </div>
      </div>
    </article>
  `).join("");

  document.querySelectorAll(".add-button").forEach((button) => {
    button.addEventListener("click", () => addToCart(Number(button.dataset.id)));
  });
}

function saveCart() {
  localStorage.setItem("patelkart-cart", JSON.stringify(cart));
  updateCart();
}

function addToCart(id) {
  const existing = cart.find((item) => item.id === id);
  if (existing) existing.quantity += 1;
  else cart.push({ id, quantity: 1 });
  saveCart();

  const toast = document.getElementById("toast");
  const product = products.find((item) => item.id === id);
  toast.textContent = `${product.name} added to cart`;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 1800);
}

function updateCart() {
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  document.getElementById("cartCount").textContent = count;

  const cartItems = document.getElementById("cartItems");
  if (!cart.length) {
    cartItems.innerHTML = `<div class="empty-cart"><span>0</span><h3>Your cart is empty</h3><p>Add a few curious finds.</p></div>`;
  } else {
    cartItems.innerHTML = cart.map((item) => {
      const product = products.find((entry) => entry.id === item.id);
      return `<div class="cart-row">
        <div class="cart-thumb">${product.icon === "book" ? "📖" : product.icon === "car" ? "🚗" : product.icon === "pens" ? "🖊️" : product.icon === "flowers" ? "💐" : "🎸"}</div>
        <div class="cart-details"><h3>${product.name}</h3><p>${formatPrice(product.price)}</p></div>
        <div class="quantity"><button data-action="minus" data-id="${product.id}" aria-label="Decrease quantity">−</button><span>${item.quantity}</span><button data-action="plus" data-id="${product.id}" aria-label="Increase quantity">+</button></div>
      </div>`;
    }).join("");
  }

  const subtotal = cart.reduce((sum, item) => {
    const product = products.find((entry) => entry.id === item.id);
    return sum + product.price * item.quantity;
  }, 0);
  document.getElementById("subtotal").textContent = formatPrice(subtotal);

  document.querySelectorAll(".quantity button").forEach((button) => {
    button.addEventListener("click", () => {
      const id = Number(button.dataset.id);
      const item = cart.find((entry) => entry.id === id);
      if (button.dataset.action === "plus") item.quantity += 1;
      else item.quantity -= 1;
      if (item.quantity <= 0) cart = cart.filter((entry) => entry.id !== id);
      saveCart();
    });
  });
}

const drawer = document.getElementById("cartDrawer");
const overlay = document.getElementById("overlay");

function openCart() {
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  overlay.classList.add("show");
  document.body.classList.add("locked");
}

function closeCart() {
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  overlay.classList.remove("show");
  document.body.classList.remove("locked");
}

document.getElementById("cartButton").addEventListener("click", openCart);
document.getElementById("closeCart").addEventListener("click", closeCart);
overlay.addEventListener("click", closeCart);

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".filter.active").classList.remove("active");
    button.classList.add("active");
    renderProducts(button.dataset.filter);
  });
});

document.getElementById("checkoutButton").addEventListener("click", () => {
  if (!cart.length) return;
  document.getElementById("toast").textContent = "Checkout ready — thanks for visiting!";
  document.getElementById("toast").classList.add("show");
  setTimeout(() => document.getElementById("toast").classList.remove("show"), 2200);
});

renderProducts();
updateCart();
