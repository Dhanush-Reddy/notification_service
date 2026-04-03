"""Unit tests for template rendering."""
import pytest
from app.services.template_service import render


def test_basic_substitution():
    assert render("Hello {{name}}", {"name": "Alex"}) == "Hello Alex"


def test_multiple_variables():
    result = render("{{greeting}} {{name}}, your order {{order_id}} shipped.", {
        "greeting": "Hi",
        "name": "Sam",
        "order_id": "ORD-99",
    })
    assert result == "Hi Sam, your order ORD-99 shipped."


def test_missing_variable_left_as_is():
    # unknown placeholders should be preserved, not removed or errored
    assert render("Hello {{name}}", {}) == "Hello {{name}}"


def test_extra_variables_are_ignored():
    result = render("Hello {{name}}", {"name": "Alex", "unused": "ignored"})
    assert result == "Hello Alex"


def test_no_placeholders():
    body = "This message has no placeholders."
    assert render(body, {"name": "Alex"}) == body


def test_empty_string():
    assert render("", {"name": "Alex"}) == ""


def test_variable_at_start_and_end():
    assert render("{{a}} middle {{b}}", {"a": "start", "b": "end"}) == "start middle end"


def test_numeric_value_substitution():
    result = render("Total: {{amount}}", {"amount": 42})
    assert result == "Total: 42"


def test_single_brace_not_replaced():
    # single braces are NOT the spec format — must be left alone
    body = "Hello {name}"
    assert render(body, {"name": "Alex"}) == "Hello {name}"
