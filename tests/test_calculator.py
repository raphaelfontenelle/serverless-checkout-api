"""
Tests for the order total calculation logic.

These tests focus on the business rules and edge cases. They do not
touch the API, authentication or persistence, so they run fast and
point directly at problems in the calculation itself.
"""

from decimal import Decimal

from app.calculator import compute_order_totals


def test_single_item_no_discount():
    # subtotal is 50, below the 100 threshold, so no discount applies.
    line_items = [{"name": "Book", "unit_price": 50, "quantity": 1}]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("50.00")
    assert summary["taxes"] == Decimal("6.50")  # 13% of 50
    assert summary["discount"] == Decimal("0.00")
    assert summary["total"] == Decimal("56.50")  # 50 + 6.50 - 0


def test_multiple_items_sum_correctly():
    # subtotal is (10 * 2) + (5 * 3) = 35.
    line_items = [
        {"name": "Pen", "unit_price": 10, "quantity": 2},
        {"name": "Notebook", "unit_price": 5, "quantity": 3},
    ]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("35.00")
    assert summary["taxes"] == Decimal("4.55")  # 13% of 35


def test_discount_applies_above_threshold():
    # subtotal is 200, above 100, so a 10% discount applies.
    line_items = [{"name": "Monitor", "unit_price": 200, "quantity": 1}]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("200.00")
    assert summary["taxes"] == Decimal("26.00")  # 13% of 200
    assert summary["discount"] == Decimal("20.00")  # 10% of 200
    assert summary["total"] == Decimal("206.00")  # 200 + 26 - 20


def test_no_discount_at_exactly_threshold():
    # subtotal is exactly 100. The rule is "> 100", so discount is 0.
    line_items = [{"name": "Item", "unit_price": 100, "quantity": 1}]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("100.00")
    assert summary["discount"] == Decimal("0.00")


def test_discount_just_above_threshold():
    # subtotal is 100.01, just above the threshold, so discount applies.
    line_items = [{"name": "Item", "unit_price": 100.01, "quantity": 1}]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("100.01")
    assert summary["discount"] == Decimal("10.00")  # 10% of 100.01, rounded


def test_decimal_precision_is_correct():
    # With floats this calculation would drift. Decimal keeps it exact.
    line_items = [{"name": "Item", "unit_price": 39.99, "quantity": 3}]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("119.97")  # 39.99 * 3
    assert summary["discount"] == Decimal("12.00")  # 10% of 119.97, rounded


def test_free_item_does_not_add_to_subtotal():
    # A gift with unit_price 0 is allowed and adds nothing to the total.
    line_items = [
        {"name": "Book", "unit_price": 20, "quantity": 1},
        {"name": "Free Gift", "unit_price": 0, "quantity": 1},
    ]
    summary = compute_order_totals(line_items)

    assert summary["subtotal"] == Decimal("20.00")
    assert summary["total"] == Decimal("22.60")  # 20 + 2.60 tax


def test_empty_list_returns_zeros():
    # An empty list is handled by the calculator as all zeros. The API
    # layer rejects empty requests; this just documents that the math
    # itself does not break.
    summary = compute_order_totals([])

    assert summary["subtotal"] == Decimal("0.00")
    assert summary["taxes"] == Decimal("0.00")
    assert summary["discount"] == Decimal("0.00")
    assert summary["total"] == Decimal("0.00")
