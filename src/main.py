import config
from sazka import SazkaClient
from pushover import PushoverClient, Message

config = config.get_config()
sazka_client = SazkaClient(config.sazka_email, config.sazka_password.get_secret_value())
pushover_client = PushoverClient(config.pushover_api_token.get_secret_value(), config.pushover_user_key.get_secret_value())

def main() -> None:
    calendars = sazka_client.get_calendars()
    for calendar in calendars:
        active_bonuses = [bonus for bonus in calendar.bonuses if bonus.state == 1]
        for bonus in active_bonuses:
            message = Message(
                title=f"Sazka: {calendar.title}",
                message=f"<h2>{bonus.title}</h2>{bonus.text}",
                html=True,
                url=calendar.url
            )
            pushover_client.send_message(message)


if __name__ == "__main__":
    main()
