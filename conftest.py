import os
from datetime import datetime, timezone

import pytest
from playwright.sync_api import Page

from pages.booking_page import BookingPage


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """CLI --base-url takes precedence over BASE_URL and the demo address."""
    return (
        pytestconfig.getoption("--base-url")
        or os.environ.get("BASE_URL")
        or "https://rcsi-science.github.io/demo-roomly/"
    )


@pytest.fixture
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        "timezone_id": "Europe/Moscow",
        "locale": "ru-RU",
        "viewport": {"width": 1350, "height": 805},
    }


@pytest.fixture
def booking(page: Page, base_url: str) -> BookingPage:
    booking_page = BookingPage(page)
    booking_page.open(base_url, now=datetime(2030, 1, 15, 9, tzinfo=timezone.utc))
    return booking_page
