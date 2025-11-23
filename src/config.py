from functools import cache

from pydantic import EmailStr, SecretStr
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    sazka_email: EmailStr
    sazka_password: SecretStr

    pushover_user_key: SecretStr
    pushover_api_token: SecretStr

    metadata_filepath: str = "metadata.txt"


@cache
def get_instance() -> Config:
    return Config()
