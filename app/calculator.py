"""
Order total calculation logic.

This module holds the core business rules for the checkout service.
It is kept free of framework or infrastructure code so it can be tested
in isolation and reused if the delivery mechanism changes later.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List

# Business rule constants. Naming them and keeping them in one place
# makes the rules easy to locate and adjust as requirements change.
TAX_PERCENTAGE = Decimal("0.13")
DISCOUNT_PERCENTAGE = Decimal("0.10")
DISCOUNT_MIN_SUBTOTAL = Decimal("100")


def _to_currency(amount: Decimal) -> Decimal:
    """Round a monetary amount to two decimal places.

    ROUND_HALF_UP is used because it matches the rounding people expect
    for money (0.005 becomes 0.01), unlike Python's default banker's
    rounding.
    """
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_order_totals(line_items: List[dict]) -> dict:
    """Compute the order totals from a list of line items.

    Each line item is expected to carry unit_price and quantity that the
    API layer has already validated as non-negative. Returns a dict with
    subtotal, taxes, discount and total, each rounded to two decimals.
    """
    # subtotal is the sum of unit_price times quantity across all items.
    running_subtotal = Decimal("0")
    for line_item in line_items:
        unit_price = Decimal(str(line_item["unit_price"]))
        quantity = Decimal(str(line_item["quantity"]))
        running_subtotal += unit_price * quantity

    # taxes are a flat percentage of the subtotal.
    tax_amount = running_subtotal * TAX_PERCENTAGE

    # the discount only applies when the subtotal is strictly above the
    # threshold. At exactly the threshold no discount is given.
    if running_subtotal > DISCOUNT_MIN_SUBTOTAL:
        discount_amount = running_subtotal * DISCOUNT_PERCENTAGE
    else:
        discount_amount = Decimal("0")

    # total adds taxes to the subtotal and then subtracts the discount.
    final_total = running_subtotal + tax_amount - discount_amount

    return {
        "subtotal": _to_currency(running_subtotal),
        "taxes": _to_currency(tax_amount),
        "discount": _to_currency(discount_amount),
        "total": _to_currency(final_total),
    }
