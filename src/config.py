from functools import cache
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    sazka_email: str
    sazka_password: str

    pushover_user_key: str
    pushover_api_key: str

@cache
def get_config() -> Config:
    return Config()
