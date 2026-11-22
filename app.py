from datetime import date
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
    {"id": 1, "name": "Wisha Wozzariter", "category": "Books",  "price": 1000,   "emoji": "📖", "colour": "lime",  "note": "A story worth keeping"},
    {"id": 2, "name": "Classic Toy Car",  "category": "Play",   "price": 5,      "emoji": "🚗", "colour": "peach", "note": "Pocket-sized adventure"},
    {"id": 3, "name": "Studio Pen Set",   "category": "Play",   "price": 94.50,  "emoji": "🖊️", "colour": "blue",  "note": "Ideas start here"},
    {"id": 4, "name": "Sunset Bouquet",   "category": "Home",   "price": 194,    "emoji": "💐", "colour": "pink",  "note": "Bring colour indoors"},
    {"id": 5, "name": "Electric Guitar",  "category": "Play",   "price": 5257,   "emoji": "🎸", "colour": "sand",  "note": "Make some noise"},
]


def rupees(amount: float) -> str:
    text = f"{amount:,.2f}".rstrip("0").rstrip(".")
    return f"₹{text}"


# ── Session-state defaults ───────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "page" not in st.session_state:
    st.session_state.page = "shop"   # "shop" | "profile"
if "view" not in st.session_state:
    st.session_state.view = "shop"   # "shop" | "profile"


# ── Helpers ──────────────────────────────────────────────────────
def add_to_cart(product_id: int) -> None:
    st.session_state.cart[product_id] = st.session_state.cart.get(product_id, 0) + 1
    set_cart(st.session_state.username, st.session_state.cart)


def remove_from_cart(product_id: int) -> None:
    qty = st.session_state.cart.get(product_id, 0)
    if qty <= 1:
        st.session_state.cart.pop(product_id, None)
    else:
        st.session_state.cart[product_id] = qty - 1
    set_cart(st.session_state.username, st.session_state.cart)


def checkout() -> None:
    if not st.session_state.cart:
        st.warning("Your cart is empty.")
        return
    order_items = [
        {
            "product_name": next(p["name"] for p in PRODUCTS if p["id"] == pid),
            "unit_price":   next(p["price"] for p in PRODUCTS if p["id"] == pid),
            "quantity": qty,
        }
        for pid, qty in st.session_state.cart.items()
    ]
    order_total = sum(i["unit_price"] * i["quantity"] for i in order_items)
    order_id = create_order(st.session_state.username, st.session_state.cart, PRODUCTS)
    notify_new_order(st.session_state.username, order_id, order_items, order_total)
    st.session_state.cart = {}
    set_cart(st.session_state.username, {})
    st.success(f"Order #{order_id} confirmed!")


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.cart = {}
    st.session_state.view = "shop"


def go_profile() -> None:
    st.session_state.page = "profile"


def go_shop() -> None:
    st.session_state.page = "shop"


# ── Grain overlay ────────────────────────────────────────────────
st.markdown('<div class="grain"></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# LOGIN / REGISTER WALL
# ════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.markdown('<div class="login-heading">PatelKart</div>', unsafe_allow_html=True)
    story_col, panel_col = st.columns([1.35, 1], gap="large", vertical_alignment="center")

    with story_col:
        st.markdown("""
            <section class="login-story">
              <p class="eyebrow">Welcome to the collection</p>
              <h1>Small finds.<br><em>Big character.</em></h1>
              <p>Sign in to explore five wonderfully useful things for curious homes and creative lives.</p>
              <div class="login-guitar">🎸</div>
            </section>
        """, unsafe_allow_html=True)

    with panel_col:
        st.markdown('<section class="login-panel"><p class="section-kicker">Member access</p><h2>Sign in</h2></section>', unsafe_allow_html=True)
        login_tab, register_tab, recovery_tab = st.tabs(["Login", "Create account", "Forgot password"])

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input("Username", placeholder="Enter your username")
                password_input = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Enter PatelKart", width="stretch")
            if submitted:
                user = authenticate(username_input, password_input)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.cart = load_cart(user["username"])
                    st.session_state.page = "shop"
                    notify_login(user["username"])
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")

        with register_tab:
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("Choose a username")
                full_name    = st.text_input("Full name")
                phone        = st.text_input("Phone number")
                address      = st.text_area("Address")
                birthday     = st.date_input("Birthday", value=None)
                new_password = st.text_input("Choose a password", type="password")
                repeat_pw    = st.text_input("Repeat password", type="password")
                registered   = st.form_submit_button("Create account", width="stretch")
            if registered:
                if new_password != repeat_pw:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(
                        new_username, new_password, full_name, phone, address,
                        birthday.isoformat() if birthday else "",
                    )
                    if ok:
                        notify_new_user(new_username, full_name, phone)
                        st.success(msg)
                    else:
                        st.error(msg)

        with recovery_tab:
            with st.form("recovery_form", clear_on_submit=True):
                rec_username = st.text_input("Username")
                rec_phone    = st.text_input("Phone number")
                rec_password = st.text_input("New password", type="password")
                recovered    = st.form_submit_button("Reset password", width="stretch")
            if recovered:
                ok, msg = recover_password(rec_username, rec_phone, rec_password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown('<div class="demo-note">Demo login: <strong>customer</strong> / <strong>patel123</strong></div>', unsafe_allow_html=True)

    st.stop()


# ════════════════════════════════════════════════════════════════
# SHARED TOPBAR  (shown on every authenticated page)
# ════════════════════════════════════════════════════════════════
on_profile = st.session_state.page == "profile"

st.markdown(f"""
    <header class="topbar">
      <a class="brand" href="#"><span class="brand-mark">P</span><span>PatelKart</span></a>
      <nav class="nav-links">
        <a class="{'active' if not on_profile else ''}" href="#">Shop</a>
        <a class="{'active' if on_profile else ''}" href="#">Profile</a>
      </nav>
      <div class="topbar-right">
        <span class="topbar-welcome">Hello, <strong>{st.session_state.username}</strong></span>
      </div>
    </header>
""", unsafe_allow_html=True)

nav_l, nav_mid, nav_r = st.columns([5, 1, 1])
with nav_mid:
    if on_profile:
        st.button("← Shop", key="go_shop_btn", on_click=go_shop, width="stretch")
    else:
        if st.button("👤 Profile", key="go_profile", width="stretch"):
            st.session_state.view = "profile"
            st.rerun()
with nav_r:
    st.button("Logout", key="logout_btn", on_click=logout, width="stretch")

st.markdown("<div class='shop-divider'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# SHOP PAGE
# ════════════════════════════════════════════════════════════════
if st.session_state.page == "shop":
    st.markdown("""
        <div class="shop-header">
          <p class="section-kicker">Curated collection</p>
          <h2 class="shop-title">The oddball five</h2>
        </div>
    """, unsafe_allow_html=True)

    ctrl_l, ctrl_r = st.columns([3, 1])
    with ctrl_l:
        search = st.text_input("Search", placeholder="Search the collection…", label_visibility="collapsed")
    with ctrl_r:
        category = st.selectbox("Filter", ["All", "Books", "Play", "Home"], label_visibility="collapsed")

    visible = [
        p for p in PRODUCTS
        if (category == "All" or p["category"] == category)
        and (not search or search.lower() in p["name"].lower())
    ]

    for start in range(0, len(visible), 3):
        row = st.columns(3)
        for col, product in zip(row, visible[start:start + 3]):
            with col:
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
                st.button("Add to cart  +", key=f"add_{product['id']}",
                          on_click=add_to_cart, args=(product["id"],), width="stretch")

    if not visible:
        st.markdown('<div class="no-results">No curious finds match that search.</div>', unsafe_allow_html=True)

    # Cart expander
    cart_count = sum(st.session_state.cart.values())
    cart_total = sum(
        next(p["price"] for p in PRODUCTS if p["id"] == pid) * qty
        for pid, qty in st.session_state.cart.items()
    )
    with st.expander(f"🛒 Shopping cart — {cart_count} item{'s' if cart_count != 1 else ''} · {rupees(cart_total)}", expanded=False):
        if not st.session_state.cart:
            st.info("Your cart is empty. Add a few curious finds.")
        else:
            for pid, qty in list(st.session_state.cart.items()):
                prod = next(p for p in PRODUCTS if p["id"] == pid)
                ic, mc, cc, pc = st.columns([5, 1, 1, 1])
                with ic:
                    st.markdown(f"**{prod['emoji']} {prod['name']}**  \n{rupees(prod['price'])}")
                with mc:
                    st.button("−", key=f"minus_{pid}", on_click=remove_from_cart, args=(pid,))
                with cc:
                    st.markdown(f'<div class="quantity-count">{qty}</div>', unsafe_allow_html=True)
                with pc:
                    st.button("+", key=f"plus_{pid}", on_click=add_to_cart, args=(pid,))

            cart_total = sum(
                next(p["price"] for p in PRODUCTS if p["id"] == pid) * qty
                for pid, qty in st.session_state.cart.items()
            )
            st.markdown(f'<div class="subtotal"><span>Subtotal</span><strong>{rupees(cart_total)}</strong></div>', unsafe_allow_html=True)
            st.button("Checkout", key="checkout_btn", on_click=checkout, width="stretch", type="primary")


# ════════════════════════════════════════════════════════════════
# PROFILE PAGE
# ════════════════════════════════════════════════════════════════
elif st.session_state.view == "profile":
    st.markdown("""
        <div class="shop-header">
          <p class="section-kicker">Your account</p>
          <h2 class="shop-title">My Profile</h2>
        </div>
    """, unsafe_allow_html=True)

    back_left, back_right = st.columns([5, 1])
    with back_right:
        if st.button("← Shop", key="back_to_shop", width="stretch"):
            st.session_state.view = "shop"
            st.rerun()

    customer = get_user(st.session_state.username)
    profile_tab, orders_tab = st.tabs(["Edit profile", "Order history"])

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
                    birthday_value = date.fromisoformat(customer["birthday"])
                except ValueError:
                    birthday_value = None

            with st.form("profile_form"):
                name_col, phone_col = st.columns(2)
                with name_col:
                    profile_name = st.text_input("Full name", value=customer.get("name", "") if customer else "")
                with phone_col:
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
                st.success("Profile saved successfully!")
                st.rerun()

    with orders_tab:
        orders = get_orders(st.session_state.username)
        if not orders:
            st.info("No orders yet. Head back to the shop and pick something nice!")
        else:
            for order in orders:
                with st.container(border=True):
                    st.markdown(f"**Order #{order['id']}** · {order['status']}")
                    st.caption(order["created_at"])
                    st.markdown(f"### {rupees(order['total'])}")
                    for item in order["items"]:
                        st.write(f"{item['quantity']} × {item['product_name']} — {rupees(item['unit_price'] * item['quantity'])}")

    st.markdown("""
        <footer>
          <a class="brand footer-brand" href="#"><span class="brand-mark">P</span><span>PatelKart</span></a>
          <p>Good things, thoughtfully gathered.</p>
          <span>© 2026 PatelKart</span>
        </footer>
    """, unsafe_allow_html=True)
    st.stop()
