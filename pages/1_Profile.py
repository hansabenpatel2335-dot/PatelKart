"""Profile & Orders page — only accessible when logged in."""
from datetime import date
from pathlib import Path

import streamlit as st

from database import get_orders, get_user, initialize_database, update_profile

initialize_database()

st.set_page_config(
    page_title="My Profile — PatelKart",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_css() -> None:
    css_path = Path(__file__).resolve().parent.parent / "styles_streamlit.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


load_css()


def rupees(amount: float) -> str:
    text = f"{amount:,.2f}".rstrip("0").rstrip(".")
    return f"₹{text}"


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.cart = {}


# ── Guard: redirect to shop if not logged in ─────────────────────
st.markdown('<div class="grain"></div>', unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    st.warning("Please log in first.")
    if st.button("← Go to Shop"):
        st.switch_page("app.py")
    st.stop()

username = st.session_state.username
customer = get_user(username)

# ── Top bar ──────────────────────────────────────────────────────
st.markdown(f"""
    <header class="topbar">
      <a class="brand" href="#">
        <span class="brand-mark">P</span><span>PatelKart</span>
      </a>
      <nav class="nav-links">
        <a href="#">Shop</a>
        <a class="active" href="#">Profile</a>
      </nav>
      <div class="topbar-right">
        <span class="topbar-welcome">Hello, <strong>{username}</strong></span>
      </div>
    </header>
""", unsafe_allow_html=True)

action_left, action_mid, action_right = st.columns([5, 1, 1])
with action_mid:
    if st.button("← Shop", key="go_shop", width="stretch"):
        st.switch_page("app.py")
with action_right:
    st.button("Logout", key="logout_btn", on_click=logout, width="stretch")

st.markdown("<div class='shop-divider'></div>", unsafe_allow_html=True)

# ── Page heading ─────────────────────────────────────────────────
st.markdown("""
    <div class="shop-header">
      <p class="section-kicker">Your account</p>
      <h2 class="shop-title">My Profile</h2>
    </div>
""", unsafe_allow_html=True)

profile_tab, orders_tab = st.tabs(["✏️  Edit profile", "📦  Order history"])

# ── Profile tab ──────────────────────────────────────────────────
with profile_tab:
    picture_col, details_col = st.columns([1, 3], vertical_alignment="top")

    with picture_col:
        if customer and customer.get("profile_picture"):
            st.image(customer["profile_picture"], width=180)
        else:
            st.markdown('<div class="profile-placeholder">P</div>', unsafe_allow_html=True)

        st.markdown(f'<p class="profile-username">@{username}</p>', unsafe_allow_html=True)

    with details_col:
        birthday_value = None
        if customer and customer.get("birthday"):
            try:
                birthday_value = date.fromisoformat(customer["birthday"])
            except ValueError:
                birthday_value = None

        st.markdown('<div class="profile-form-wrap">', unsafe_allow_html=True)
        with st.form("profile_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                profile_name = st.text_input("Full name", value=customer.get("name", "") if customer else "")
            with col_b:
                profile_phone = st.text_input("Phone number", value=customer.get("phone", "") if customer else "")

            profile_address = st.text_area("Address", value=customer.get("address", "") if customer else "", height=90)
            profile_birthday = st.date_input("Birthday", value=birthday_value)
            profile_picture = st.file_uploader("Profile picture", type=["png", "jpg", "jpeg", "webp"])
            saved = st.form_submit_button("💾  Save profile", width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

        if saved:
            update_profile(
                username,
                profile_name,
                profile_phone,
                profile_address,
                profile_birthday.isoformat() if profile_birthday else "",
                profile_picture.getvalue() if profile_picture else None,
                profile_picture.name if profile_picture else "",
            )
            st.success("Profile saved successfully!")
            st.rerun()

# ── Orders tab ───────────────────────────────────────────────────
with orders_tab:
    orders = get_orders(username)
    if not orders:
        st.info("No orders yet. Head back to the shop and pick something nice!")
        if st.button("Browse the shop →"):
            st.switch_page("app.py")
    else:
        for order in orders:
            with st.container(border=True):
                o_left, o_right = st.columns([3, 1])
                with o_left:
                    st.markdown(f"**Order #{order['id']}** · {order['status']}")
                    st.caption(order["created_at"])
                with o_right:
                    st.markdown(f'<div class="order-total">{rupees(order["total"])}</div>', unsafe_allow_html=True)
                for item in order["items"]:
                    st.write(f"  {item['quantity']} × {item['product_name']} — {rupees(item['unit_price'] * item['quantity'])}")

# ── Footer ────────────────────────────────────────────────────────
st.markdown("""
    <footer>
      <a class="brand footer-brand" href="#"><span class="brand-mark">P</span><span>PatelKart</span></a>
      <p>Good things, thoughtfully gathered.</p>
      <span>© 2026 PatelKart</span>
    </footer>
""", unsafe_allow_html=True)
