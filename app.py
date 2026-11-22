from pathlib import Path

import streamlit as st

from database import (
    authenticate,
    create_order,
    create_user,
    get_orders,
    get_user,
    initialize_database,
    load_cart,
    recover_password,
    set_cart,
    update_profile,
)
from telegram_notify import notify_login, notify_new_order, notify_new_user


initialize_database()

st.set_page_config(
    page_title="PatelKart — Curious Goods",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_css() -> None:
    css_path = Path(__file__).with_name("styles_streamlit.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


load_css()

PRODUCTS = [
    {"id": 1, "name": "Wisha Wozzariter", "category": "Books", "price": 1000, "emoji": "📖", "colour": "lime", "note": "A story worth keeping"},
    {"id": 2, "name": "Classic Toy Car", "category": "Play", "price": 5, "emoji": "🚗", "colour": "peach", "note": "Pocket-sized adventure"},
    {"id": 3, "name": "Studio Pen Set", "category": "Play", "price": 94.50, "emoji": "🖊️", "colour": "blue", "note": "Ideas start here"},
    {"id": 4, "name": "Sunset Bouquet", "category": "Home", "price": 194, "emoji": "💐", "colour": "pink", "note": "Bring colour indoors"},
    {"id": 5, "name": "Electric Guitar", "category": "Play", "price": 5257, "emoji": "🎸", "colour": "sand", "note": "Make some noise"},
]


def rupees(amount: float) -> str:
    text = f"{amount:,.2f}".rstrip("0").rstrip(".")
    return f"₹{text}"


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "cart" not in st.session_state:
    st.session_state.cart = {}


def add_to_cart(product_id: int) -> None:
    st.session_state.cart[product_id] = st.session_state.cart.get(product_id, 0) + 1
    set_cart(st.session_state.username, st.session_state.cart)


def remove_from_cart(product_id: int) -> None:
    quantity = st.session_state.cart.get(product_id, 0)
    if quantity <= 1:
        st.session_state.cart.pop(product_id, None)
    else:
        st.session_state.cart[product_id] = quantity - 1
    set_cart(st.session_state.username, st.session_state.cart)


def checkout() -> None:
    if not st.session_state.cart:
        st.warning("Your cart is empty.")
        return
    # Snapshot items before the cart is cleared
    order_items = [
        {
            "product_name": next(p["name"] for p in PRODUCTS if p["id"] == pid),
            "unit_price": next(p["price"] for p in PRODUCTS if p["id"] == pid),
            "quantity": qty,
        }
        for pid, qty in st.session_state.cart.items()
    ]
    order_total = sum(item["unit_price"] * item["quantity"] for item in order_items)
    order_id = create_order(st.session_state.username, st.session_state.cart, PRODUCTS)
    notify_new_order(st.session_state.username, order_id, order_items, order_total)
    st.session_state.cart = {}
    set_cart(st.session_state.username, {})
    st.success(f"Order #{order_id} confirmed!")


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.cart = {}


st.markdown('<div class="grain"></div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    st.markdown('<div class="login-heading">PatelKart</div>', unsafe_allow_html=True)
    story_column, panel_column = st.columns([1.35, 1], gap="large", vertical_alignment="center")

    with story_column:
        st.markdown("""
            <section class="login-story">
              <p class="eyebrow">Welcome to the collection</p>
              <h1>Small finds.<br><em>Big character.</em></h1>
              <p>Sign in to explore five wonderfully useful things for curious homes and creative lives.</p>
              <div class="login-guitar">🎸</div>
            </section>
        """, unsafe_allow_html=True)

    with panel_column:
        st.markdown('<section class="login-panel"><p class="section-kicker">Member access</p><h2>Sign in</h2></section>', unsafe_allow_html=True)

        login_tab, register_tab, recovery_tab = st.tabs(["Login", "Create account", "Forgot password"])

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Enter PatelKart", width="stretch")

            if submitted:
                user = authenticate(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.cart = load_cart(user["username"])
                    notify_login(user["username"])
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")

        with register_tab:
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("Choose a username")
                full_name = st.text_input("Full name")
                phone = st.text_input("Phone number")
                address = st.text_area("Address")
                birthday = st.date_input("Birthday", value=None)
                new_password = st.text_input("Choose a password", type="password")
                repeat_password = st.text_input("Repeat password", type="password")
                registered = st.form_submit_button("Create account", width="stretch")

            if registered:
                if new_password != repeat_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = create_user(
                        new_username,
                        new_password,
                        full_name,
                        phone,
                        address,
                        birthday.isoformat() if birthday else "",
                    )
                    if success:
                        notify_new_user(new_username, full_name, phone)
                        st.success(message)
                    else:
                        st.error(message)

        with recovery_tab:
            with st.form("recovery_form", clear_on_submit=True):
                recovery_username = st.text_input("Username")
                recovery_phone = st.text_input("Phone number")
                recovery_password = st.text_input("New password", type="password")
                recovered = st.form_submit_button("Reset password", width="stretch")

            if recovered:
                success, message = recover_password(recovery_username, recovery_phone, recovery_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

        st.markdown('<div class="demo-note">Demo login: <strong>customer</strong> / <strong>patel123</strong></div>', unsafe_allow_html=True)

    st.stop()


cart_count = sum(st.session_state.cart.values())
cart_total = sum(
    next(product["price"] for product in PRODUCTS if product["id"] == product_id) * quantity
    for product_id, quantity in st.session_state.cart.items()
)

st.markdown("""
    <header class="topbar">
      <a class="brand" href="#"><span class="brand-mark">P</span><span>PatelKart</span></a>
      <nav class="nav-links"><a class="active" href="#shop">Shop</a><a href="#story">Our story</a></nav>
    </header>
""", unsafe_allow_html=True)

header_left, header_right = st.columns([7, 1])
with header_left:
    st.markdown(f'<div class="welcome">Hello, <strong>{st.session_state.username}</strong></div>', unsafe_allow_html=True)
with header_right:
    st.button("Logout", key="logout", on_click=logout, width="stretch")

customer = get_user(st.session_state.username)
profile_tab, orders_tab = st.tabs(["My profile", "Order history"])

with profile_tab:
    picture_col, details_col = st.columns([1, 3], vertical_alignment="top")
    with picture_col:
        if customer and customer.get("profile_picture"):
            st.image(customer["profile_picture"], alt="Customer profile picture", width=180)
        else:
            st.markdown('<div class="profile-placeholder">P</div>', unsafe_allow_html=True)

    with details_col:
        birthday_value = None
        if customer and customer.get("birthday"):
            try:
                from datetime import date
                birthday_value = date.fromisoformat(customer["birthday"])
            except ValueError:
                birthday_value = None

        with st.form("profile_form"):
            profile_name = st.text_input("Name", value=customer.get("name", "") if customer else "")
            profile_phone = st.text_input("Phone number", value=customer.get("phone", "") if customer else "")
            profile_address = st.text_area("Address", value=customer.get("address", "") if customer else "")
            profile_birthday = st.date_input("Birthday", value=birthday_value)
            profile_picture = st.file_uploader("Profile picture", type=["png", "jpg", "jpeg", "webp"])
            saved = st.form_submit_button("Save profile", width="stretch")

        if saved:
            update_profile(
                st.session_state.username,
                profile_name,
                profile_phone,
                profile_address,
                profile_birthday.isoformat() if profile_birthday else "",
                profile_picture.getvalue() if profile_picture else None,
                profile_picture.name if profile_picture else "",
            )
            st.success("Profile saved.")
            st.rerun()

with orders_tab:
    orders = get_orders(st.session_state.username)
    if not orders:
        st.info("No orders yet. Your checkout history will appear here.")
    else:
        for order in orders:
            with st.container(border=True):
                st.markdown(f"### Order #{order['id']} — {rupees(order['total'])}")
                st.caption(f"{order['created_at']} · {order['status']}")
                for item in order["items"]:
                    st.write(f"{item['quantity']} × {item['product_name']} — {rupees(item['unit_price'] * item['quantity'])}")

st.markdown("""
    <section class="hero" id="story">
      <div class="hero-copy">
        <p class="eyebrow"><span></span> The everyday edit</p>
        <h1>Small finds.<br><em>Big character.</em></h1>
        <p class="hero-description">Five wonderfully useful things, handpicked for curious homes and creative lives.</p>
      </div>
      <div class="hero-art">
        <div class="sun"></div>
        <div class="guitar"><div class="guitar-neck"></div><div class="guitar-head"></div><div class="guitar-body"><i></i></div></div>
        <p>Made to stand out</p>
      </div>
    </section>
""", unsafe_allow_html=True)

st.markdown('<section class="shop-section" id="shop"><div class="section-heading"><div><p class="section-kicker">Curated collection</p><h2>The oddball five</h2></div></div></section>', unsafe_allow_html=True)

controls_left, controls_right = st.columns([3, 1])
with controls_left:
    search = st.text_input("Search products", placeholder="Search the collection…", label_visibility="collapsed")
with controls_right:
    category = st.selectbox("Filter", ["All", "Books", "Play", "Home"], label_visibility="collapsed")

visible_products = [
    product for product in PRODUCTS
    if (category == "All" or product["category"] == category)
    and (not search or search.lower() in product["name"].lower())
]

for start in range(0, len(visible_products), 3):
    row = st.columns(3)
    for column, product in zip(row, visible_products[start:start + 3]):
        with column:
            st.markdown(f"""
                <article class="product-card">
                  <div class="product-image {product['colour']}">
                    <span class="product-number">0{product['id']}</span>
                    <div class="emoji-art">{product['emoji']}</div>
                  </div>
                  <div class="product-info">
                    <p>{product['note']}</p>
                    <h3>{product['name']}</h3>
                    <strong>{rupees(product['price'])}</strong>
                  </div>
                </article>
            """, unsafe_allow_html=True)
            st.button("Add to cart  +", key=f"add_{product['id']}", on_click=add_to_cart, args=(product["id"],), width="stretch")

if not visible_products:
    st.markdown('<div class="no-results">No curious finds match that search.</div>', unsafe_allow_html=True)

cart_count = sum(st.session_state.cart.values())
cart_total = sum(
    next(product["price"] for product in PRODUCTS if product["id"] == product_id) * quantity
    for product_id, quantity in st.session_state.cart.items()
)

with st.expander(f"Shopping cart — {cart_count} item{'s' if cart_count != 1 else ''} | {rupees(cart_total)}", expanded=False):
    if not st.session_state.cart:
        st.info("Your cart is empty. Add a few curious finds.")
    else:
        for product_id, quantity in list(st.session_state.cart.items()):
            product = next(item for item in PRODUCTS if item["id"] == product_id)
            item_col, minus_col, count_col, plus_col = st.columns([5, 1, 1, 1])
            with item_col:
                st.markdown(f"**{product['emoji']} {product['name']}**  \\n{rupees(product['price'])}")
            with minus_col:
                st.button("−", key=f"minus_{product_id}", on_click=remove_from_cart, args=(product_id,))
            with count_col:
                st.markdown(f'<div class="quantity-count">{quantity}</div>', unsafe_allow_html=True)
            with plus_col:
                st.button("+", key=f"plus_{product_id}", on_click=add_to_cart, args=(product_id,))

        st.markdown(f'<div class="subtotal"><span>Subtotal</span><strong>{rupees(cart_total)}</strong></div>', unsafe_allow_html=True)
        st.button("Checkout", key="checkout", on_click=checkout, width="stretch", type="primary")

st.markdown("""
    <footer>
      <a class="brand footer-brand" href="#"><span class="brand-mark">P</span><span>PatelKart</span></a>
      <p>Good things, thoughtfully gathered.</p>
      <span>© 2026 PatelKart</span>
    </footer>
""", unsafe_allow_html=True)
