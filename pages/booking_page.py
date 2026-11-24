import re
from datetime import datetime

from playwright.sync_api import Locator, Page, Response


class BookingPage:
    def __init__(self, page: Page):
        self.page = page
        self.form = page.locator("#booking-form")
        self.date = self.field("Дата")
        self.book_button = self.form.get_by_role("button", name="Забронировать")
        self.status = self.form.get_by_role("status")
        self.success = self.form.locator("#form-status.success")
        self.error = self.form.locator("#form-status.error")
        self.participants_error = self.form.locator('[data-error-for="participants"]')

    def field(self, label: str) -> Locator:
        return self.form.get_by_label(re.compile(rf"^\s*{re.escape(label)}"))

    def open(self, url: str, *, now: datetime | None = None) -> None:
        if now is not None:
            self.page.clock.set_fixed_time(now)
        self._wait_for_form(self.page.goto(url, wait_until="domcontentloaded"))
        if now is not None and self.date.get_attribute("min") != now.date().isoformat():
            raise RuntimeError("Roomly did not initialize today's minimum date")

    def reload(self) -> None:
        self._wait_for_form(self.page.reload(wait_until="domcontentloaded"))

    def _wait_for_form(self, response: Response | None) -> None:
        if response is None or not response.ok:
            status = response.status if response else "no HTTP response"
            raise RuntimeError(f"Roomly did not load successfully: {status}")
        self.form.wait_for(state="visible")
        self.book_button.wait_for(state="visible")

    def fill(
        self,
        *,
        room: str,
        date: str,
        start: str,
        end: str,
        participants: int,
        name: str,
        email: str,
    ) -> None:
        self.field("Переговорная").select_option(room)
        self.date.fill(date)
        self.field("Начало").fill(start)
        self.field("Окончание").fill(end)
        self.field("Участники").fill(str(participants))
        self.field("Ваше имя").fill(name)
        self.field("Рабочая почта").fill(email)

    def submit(self) -> None:
        self.book_button.click()
        self.status.wait_for(state="visible")

    def visible_field_errors(self) -> set[str | None]:
        return {
            error.get_attribute("data-error-for")
            for error in self.form.locator("[data-error-for]").all()
            if error.is_visible() and error.inner_text().strip()
        }
