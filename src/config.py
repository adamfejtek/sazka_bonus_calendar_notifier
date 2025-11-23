from functools import cache
from pydantic import Field, EmailStr, SecretStr
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    sazka_email: EmailStr
    sazka_password: SecretStr

    pushover_user_key: SecretStr
    pushover_api_token: SecretStr

@cache
def get_config() -> Config:
    return Config()
