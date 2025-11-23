import json
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

import requests
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator, field_serializer

BASE_URL = "https://api.pushover.net/1/"
VALIDATION_URL = BASE_URL + "users/validate.json"
MESSAGES_URL = BASE_URL + "messages.json"


class PushoverError(Exception):
    pass


class ConnectionError(PushoverError):
    pass


class AuthError(PushoverError):
    pass


class ApiError(PushoverError):
    pass


class Message(BaseModel):
    class MessageSound(StrEnum):
        pushover = "pushover"
        bike = "bike"
        bugle = "bugle"
        cashregister = "cashregister"
        classical = "classical"
        cosmic = "cosmic"
        falling = "falling"
        gamelan = "gamelan"
        incoming = "incoming"
        intermission = "intermission"
        magic = "magic"
        mechanical = "mechanical"
        pianobar = "pianobar"
        siren = "siren"
        spacealarm = "spacealarm"
        tugboat = "tugboat"
        alien = "alien"
        climb = "climb"
        persistent = "persistent"
        echo = "echo"
        updown = "updown"
        vibrate = "vibrate"
        none = "none"

    token: SecretStr | None = Field(
        default=None,
        min_length=30,
        max_length=30,
        description="Your application's API token (required)",
    )

    user: SecretStr | None = Field(
        default=None,
        min_length=30,
        max_length=30,
        description="Your user/group key (or that of your target user), viewable when logged into Pushover dashboard; often referred to as USER_KEY in Pushover documentation and code examples (required)",
    )

    message: str = Field(max_length=1024, description="Your message (required)")

    attachment: bytes | None = Field(
        default=None, description="A binary image attachment to send with the message"
    )

    attachment_base64: str | None = Field(
        default=None,
        description="A Base64-encoded image attachment to send with the message",
    )

    attachment_type: str | None = Field(
        default=None,
        pattern=r"(application|audio|font|example|image|message|model|multipart|text|video|x-(?:[0-9A-Za-z!#$%&'*+.^_`|~-]+))/([0-9A-Za-z!#$%&'*+.^_`|~-]+)((?:[ \t]*;[ \t]*[0-9A-Za-z!#$%&'*+.^_`|~-]+=(?:[0-9A-Za-z!#$%&'*+.^_`|~-]+|\"(?:[^\"\\\\]|\\.)*\"))*)",
        description="The MIME type of the included attachment or attachment_base64",
    )

    device: str | None = Field(
        default=None,
        description="The name of one of your devices to send just to that device instead of all devices",
    )

    html: bool = Field(default=False, description="Set to true to enable HTML parsing")

    monospace: bool = Field(
        default=False, description="Set to true to enable monospace messages"
    )

    priority: Literal[-2, -1, 0, 1, 2] = Field(
        default=0, description="A value of -2, -1, 0 (default), 1, or 2"
    )

    sound: MessageSound = Field(
        default=MessageSound.pushover,
        description="The name of a supported sound to override your default sound choice",
    )

    timestamp: int | None = Field(
        default=None,
        ge=0,
        description="A Unix timestamp of a time to display instead of when our API received it",
    )

    title: str | None = Field(
        default=None,
        max_length=250,
        description="Your message's title, otherwise your app's name is used",
    )

    ttl: int | None = Field(
        default=None,
        gt=0,
        description="A number of seconds that the message will live, before being deleted automatically",
    )

    url: str | None = Field(
        default=None, description="A supplementary URL to show with your message"
    )

    url_title: str | None = Field(
        default=None,
        description="A title for the URL specified as the url parameter, otherwise just the URL is shown",
    )

    @model_validator(mode="after")
    def check_html_and_monospace(self) -> Self:
        if self.html and self.monospace:
            raise ValueError("Parameters HTML and monospace cannot be both set to true")
        return self
    
    @field_serializer("html")
    def serialize_html(self, value: bool) -> int:
        return 1 if value else 0

    @field_serializer("monospace")
    def serialize_monospace(self, value: bool) -> int:
        return 1 if value else 0


class Limits(BaseModel):
    limit: int
    remaining: int
    reset: datetime

    @field_validator("reset", mode="before")
    @classmethod
    def parse_reset(cls, reset_timestamp) -> datetime:
        if isinstance(reset_timestamp, str):
            reset_timestamp = int(reset_timestamp)
        return datetime.fromtimestamp(reset_timestamp)


class PushoverClient:
    def __init__(self, api_token: str, user_key: str):
        self._api_token = api_token
        self._user_key = user_key
        self._validate_secrets()

    def _validate_response(self, response: requests.Response) -> None:
        content = json.loads(response.content)
        if content.get("status", 0) == 0:
            error_message = next(
                iter(content.get("errors", [])), "Failed to get the error message"
            )
            raise ApiError(error_message.capitalize())

    def _validate_secrets(self) -> None:
        class Validate(BaseModel):
            token: str = Field(min_length=30, max_length=30)
            user: str = Field(min_length=30, max_length=30)

        validate = Validate(token=self._api_token, user=self._user_key)

        try:
            response = requests.post(VALIDATION_URL, data=validate.model_dump())
            self._validate_response(response)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError from e
        except ApiError as e:
            raise AuthError(str(e))

    def _extract_limits(self, response: requests.Response) -> Limits:
        limit = response.headers.get("x-limit-app-limit", 0)
        remaining = response.headers.get("x-limit-app-remaining", 0)
        reset = response.headers.get("x-limit-app-reset", 0)
        return Limits(limit=limit, remaining=remaining, reset=reset)

    def send_message(self, message: Message) -> Limits:
        message.token = self._api_token
        message.user = self._user_key

        try:
            response = requests.post(MESSAGES_URL, data=message.model_dump())
            self._validate_response(response)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError from e

        return self._extract_limits(response)
