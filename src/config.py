from functools import cache

from pydantic import EmailStr, SecretStr
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    SAZKA_EMAIL: EmailStr
    SAZKA_PASSWORD: SecretStr

    PUSHOVER_USER_KEY: SecretStr
    PUSHOVER_API_TOKEN: SecretStr

    METADATA_FILEPATH: str = "metadata.txt"


@cache
def get_instance() -> Config:
    return Config()
