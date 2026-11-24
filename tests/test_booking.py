from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import Page, expect

from pages.booking_page import BookingPage


DATE = "2030-01-16"
NAME = "Анна Тестова"
REJECTED = "Проверьте, пожалуйста, заполнение формы."
VALID_FIELDS = {
    "room": "small",
    "date": DATE,
    "start": "10:00",
    "name": NAME,
    "email": "qa@example.com",
}


def test_successful_booking(booking: BookingPage) -> None:
    booking.fill(**VALID_FIELDS, participants=4, end="10:30")
    booking.submit()

    expect(booking.success).to_be_visible()
    expect(booking.success).to_contain_text("Бронирование создано.")
    for detail in ("Малая", DATE, "10:00", "10:30", NAME):
        expect(booking.success).to_contain_text(detail)
    expect(booking.form.locator(".has-error")).to_have_count(0)


def test_invalid_booking(booking: BookingPage) -> None:
    booking.fill(**VALID_FIELDS, participants=5, end="10:30")
    booking.submit()

    expect(booking.error).to_have_text(REJECTED)
    expect(booking.participants_error).to_be_visible()
    expect(booking.participants_error).to_have_text("В комнате максимум 4 участника.")
    expect(booking.success).to_have_count(0)


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01: форма подтверждает бронирование длительностью 29 минут",
    raises=AssertionError,
)
def test_discovered_defect(booking: BookingPage) -> None:
    booking.fill(**VALID_FIELDS, participants=2, end="10:29")
    booking.submit()

    status = " ".join(booking.status.inner_text().split())
    field_errors = booking.visible_field_errors()
    rejected = (
        booking.error.is_visible()
        and not booking.success.is_visible()
        and bool(status)
        and field_errors <= {"startTime", "endTime"}
        and (bool(field_errors) or "30 минут" in status or REJECTED == status)
    )
    known_confirmation = (
        booking.success.is_visible()
        and all(detail in status for detail in (
            "Бронирование создано.", "Малая", DATE, "10:00", "10:29", NAME
        ))
        and not field_errors
    )
    if not (rejected or known_confirmation):
        raise RuntimeError(f"Unexpected booking result: {status!r}, {field_errors!r}")

    assert rejected, f"Бронирование на 29 минут должно быть отклонено: {status}"


@pytest.mark.parametrize(
    "name, injected_tag",
    [
        pytest.param("Анна <QA>", "qa", id="angle-brackets"),
        pytest.param("<b>Анна Тестова</b>", "b", id="html-tag"),
    ],
)
@pytest.mark.xfail(
    strict=True,
    reason="BUG-04: имя интерпретируется как HTML в подтверждении",
    raises=AssertionError,
)
def test_name_is_displayed_as_text(
    booking: BookingPage, name: str, injected_tag: str
) -> None:
    booking.fill(**(VALID_FIELDS | {"name": name}), participants=2, end="10:30")
    booking.submit()

    status = " ".join(booking.status.inner_text().split())
    field_errors = booking.visible_field_errors()
    if booking.error.is_visible():
        if field_errors == {"name"} and not booking.success.is_visible():
            return
        raise RuntimeError(f"Unexpected validation errors: {status!r}, {field_errors!r}")

    known_confirmation = (
        booking.success.is_visible()
        and not field_errors
        and all(detail in status for detail in (
            "Бронирование создано.", "Малая", DATE, "10:00", "10:30"
        ))
    )
    if not known_confirmation:
        raise RuntimeError(f"Unexpected booking result: {status!r}, {field_errors!r}")

    assert name in booking.success.inner_text() and not booking.success.locator(injected_tag).count(), (
        f"Имя должно отображаться как обычный текст: введено {name!r}, получено {status!r}"
    )


@pytest.mark.parametrize(
    "reload_after_midnight",
    [
        pytest.param(
            False,
            id="without-reload",
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-05: после полуночи открытая форма принимает вчерашнюю дату",
                raises=AssertionError,
            ),
        ),
        pytest.param(True, id="after-reload"),
    ],
)
def test_past_date_is_rejected_after_midnight(
    page: Page, base_url: str, reload_after_midnight: bool
) -> None:
    moscow = timezone(timedelta(hours=3))
    page.clock.install(time=datetime(2030, 1, 15, 23, 58, tzinfo=moscow))
    booking = BookingPage(page)
    booking.open(base_url)
    if booking.date.get_attribute("min") != "2030-01-15":
        raise RuntimeError("Roomly did not initialize the date before midnight")

    page.clock.pause_at(datetime(2030, 1, 15, 23, 59, tzinfo=moscow))
    page.clock.fast_forward(120_000)
    page.clock.resume()
    current_day = page.evaluate("""() => {
        const now = new Date();
        return [now.getFullYear(), now.getMonth() + 1, now.getDate()];
    }""")
    if current_day != [2030, 1, 16]:
        raise RuntimeError(f"The browser clock did not cross midnight: {current_day!r}")
    if reload_after_midnight:
        booking.reload()

    booking.fill(
        **(VALID_FIELDS | {"date": "2030-01-15", "start": "22:00"}),
        participants=4,
        end="22:30",
    )
    booking.submit()

    status = " ".join(booking.status.inner_text().split())
    field_errors = booking.visible_field_errors()
    rejected = (
        booking.error.is_visible()
        and not booking.success.is_visible()
        and field_errors == {"date"}
    )
    known_confirmation = (
        booking.success.is_visible()
        and not field_errors
        and all(detail in status for detail in (
            "Бронирование создано.", "Малая", "2030-01-15", "22:00", "22:30", NAME
        ))
    )
    if not (rejected or known_confirmation):
        raise RuntimeError(f"Unexpected booking result: {status!r}, {field_errors!r}")

    assert rejected, f"Вчерашняя дата должна быть отклонена после смены суток: {status}"
