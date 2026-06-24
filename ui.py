"""
Streamlit interface for the checkout service.

A small front end that demonstrates the full flow end to end: it logs in
to obtain a token, lets the user build a list of items, and calls the
checkout endpoint to display the calculated totals. It talks to the API
over HTTP, so it works the same against a local server or a deployed one.
"""

import os

import requests
import streamlit as st

# The API base URL comes from the environment so the same UI can point at
# a local server or a deployed endpoint without code changes.
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def login(username: str, password: str) -> str:
    """Call the login endpoint and return the access token."""
    response = requests.post(
        f"{API_BASE_URL}/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def submit_checkout(token: str, cart_items: list) -> dict:
    """Call the checkout endpoint with the given items."""
    response = requests.post(
        f"{API_BASE_URL}/checkout",
        json={"items": cart_items},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


# Streamlit reruns this script top to bottom on every interaction, so we
# keep state that must survive across reruns in st.session_state. The key
# is named cart_items rather than items to avoid clashing with the
# built-in items method on the session state mapping.
if "token" not in st.session_state:
    st.session_state.token = None
if "cart_items" not in st.session_state:
    st.session_state.cart_items = []

st.title("Checkout Service")

# --- Authentication section -------------------------------------------
if st.session_state.token is None:
    st.subheader("Sign in")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        try:
            st.session_state.token = login(username, password)
            st.rerun()
        except requests.HTTPError:
            st.error("Incorrect username or password.")
        except requests.RequestException:
            st.error("Could not reach the API. Is the server running?")

# --- Checkout section -------------------------------------------------
else:
    st.success("Signed in")

    st.subheader("Add an item")
    with st.form("item_form", clear_on_submit=True):
        name = st.text_input("Name")
        unit_price = st.number_input("Unit price", min_value=0.0, step=1.0)
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        add_clicked = st.form_submit_button("Add item")

    if add_clicked:
        if not name.strip():
            st.warning("Item name cannot be empty.")
        else:
            st.session_state.cart_items.append(
                {
                    "name": name,
                    "unit_price": unit_price,
                    "quantity": int(quantity),
                }
            )

    # Show the current list of items the user has added.
    if st.session_state.cart_items:
        st.subheader("Items")
        st.table(st.session_state.cart_items)

        if st.button("Calculate checkout"):
            try:
                summary = submit_checkout(
                    st.session_state.token, st.session_state.cart_items
                )
                st.subheader("Order summary")
                col1, col2 = st.columns(2)
                col1.metric("Subtotal", f"${summary['subtotal']}")
                col1.metric("Taxes", f"${summary['taxes']}")
                col2.metric("Discount", f"-${summary['discount']}")
                col2.metric("Total", f"${summary['total']}")
            except requests.HTTPError:
                st.error("The server rejected the request.")
            except requests.RequestException:
                st.error("Could not reach the API. Is the server running?")

        if st.button("Clear items"):
            st.session_state.cart_items = []
            st.rerun()
    else:
        st.info("No items yet. Add one above to get started.")
