import json
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, EmailStr

LOGIN_URL = "https://www.sazka.cz/api/authentication/login"
BONUSES_URL = "https://www.sazka.cz/bonusy-a-souteze"
BONUS_POPUPS_URL = "https://www.sazka.cz/api/landing-page/bonus-popups"


class SazkaError(Exception):
    pass


class ConnectionError(SazkaError):
    pass


class AuthError(SazkaError):
    pass


class DataError(SazkaError):
    pass


class CalendarBonusButton(BaseModel):
    type: str | None = None
    text: str | None = None
    link: str | None = None
    bonus: str | None = None


class CalendarBonus(BaseModel):
    id: int
    title: str
    text: str
    image_url: str
    left_button: CalendarBonusButton | None = None
    right_button: CalendarBonusButton | None = None
    start_datetime: datetime
    end_datetime: datetime
    state: int


class Calendar(BaseModel):
    title: str
    subtitle: str
    text: str
    url: str
    bonuses: list[CalendarBonus]
    start_datetime: datetime
    end_datetime: datetime


class SazkaClient:
    def __init__(self, email: str, password: str):
        self._login(email, password)

    def _login(self, email:str, password: str):
        class Login(BaseModel):
            email: EmailStr
            password: str

        login = Login(email=email, password=password)

        try:
            response = requests.post(LOGIN_URL, headers={"Content-Type": "application/json"}, data=login.model_dump_json())
            response.raise_for_status()
            response_data = json.loads(response.content)
            if response_data.keys() & {"playerId", "sessionToken"}:
                self._player_id = response_data.get("playerId")
                self._session_token = response_data.get("sessionToken")
            else:
                raise DataError("The login API response did not include expected values")
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code
            if status_code >= 400 and status_code < 500:
                raise AuthError(e.response.content)
            raise ConnectionError from e
        
    def _get_url_content(self, url: str) -> str:
        if not hasattr(self, "_player_id") or not hasattr(self, "_session_token"):
            raise AuthError("The client is not authenticated")

        try:
            response = requests.get(url, cookies={"PlayerID": self._player_id, "SessionToken": self._session_token})
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise ConnectionError from e

    def _get_bonus_urls(self) -> list[str]:
        content = self._get_url_content(BONUSES_URL)
        soup = BeautifulSoup(content, "lxml")
        relative_urls = soup.find_all(href=re.compile(r"/bonusy/"))
        return [urljoin(BONUSES_URL, url["href"]) for url in relative_urls]

    def _is_website_calendar(self, soup: BeautifulSoup) -> bool:
        return bool(soup.find("section", class_="bonuses-calendar"))

    def _fix_text(self, text: str) -> str:
        text = text.replace("\n", " ").strip()
        return re.sub(" +", " ", text)

    def _get_calendar_bonuses(self, soup: BeautifulSoup) -> list[CalendarBonus]:
        bonuses_json_data = soup.find("div", id="bonuses-grid")["data-json-bonuses"]
        bonuses_data = json.loads(bonuses_json_data)

        bonuses_json_popup_data = self._get_url_content(BONUS_POPUPS_URL)
        bonuses_popup_data = json.loads(bonuses_json_popup_data)

        bonuses: list[CalendarBonus] = []
        for bonus_data in bonuses_data:
            bonus_popup = next((x for x in bonuses_popup_data if x.get("id") == bonus_data.get("id")), None)
            if not bonus_data:
                raise DataError("Could not fidn a matching bonus popup.")

            if bonus_popup.get("leftButtonType"):
                left_button = CalendarBonusButton()
                left_button.type = bonus_popup.get("leftButtonType")
                left_button.text = bonus_popup.get("leftButtonText")
                left_button.link = bonus_popup.get("leftButtonLink")
                left_button.bonus = bonus_popup.get("leftButtonBonus")
            else:
                left_button = None

            if bonus_popup.get("rightButtonType"):
                right_button = CalendarBonusButton()
                right_button.type = bonus_popup.get("rightButtonType")
                right_button.text = bonus_popup.get("rightButtonText")
                right_button.link = bonus_popup.get("rightButtonLink")
                right_button.bonus = bonus_popup.get("rightButtonBonus")
            else:
                right_button = None

            end_datetime = datetime.fromisoformat(bonus_data.get("endDateTime"))
            start_datetime = end_datetime.replace(hour=12, minute=0, second=0, microsecond=0)

            bonus = CalendarBonus(
                id = bonus_data.get("id"),
                title = bonus_popup.get("title"),
                text = bonus_popup.get("text"),
                image_url = bonus_data.get("image"),
                state = bonus_data.get("state"),
                end_datetime = end_datetime,
                start_datetime = start_datetime,
                left_button=left_button,
                right_button=right_button
            )

            bonuses.append(bonus)

        return bonuses

    def _get_calendar(self, soup: BeautifulSoup) -> Calendar:
        calendar = Calendar()
        caledar_section = soup.find("section", class_="bonuses-calendar")
        calendar.title = " ".join(self._fix_text(div.text) for div in caledar_section.find("h2", class_="bonuses-calendar__header").find_all("div"))
        calendar.subtitle = self._fix_text(soup.find("h2", class_="lp-cta-visual__header").text)
        calendar.text = self._fix_text(soup.find("div", class_="lp-cta-visual__text").text)
        calendar.bonuses = self._get_calendar_bonuses(soup)
        calendar.start_datetime = calendar.bonuses[0].start_datetime
        calendar.end_datetime = calendar.bonuses[-1].end_datetime
        return calendar

    def get_calendars(self) -> list[Calendar]:
        bonus_urls = self._get_bonus_urls()
        calendars: list[Calendar] = []
        for url in bonus_urls:
            content = self._get_url_content(url)
            soup = BeautifulSoup(content, "lxml")
            if not self._is_website_calendar(soup):
                continue
            calendar = self._get_calendar(soup)
            calendar.url = url
            calendars.append(calendar)
        return calendars
