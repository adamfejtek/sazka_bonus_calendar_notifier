import os
import logging
from datetime import datetime
from typing import TypeAlias

from pydantic import BaseModel, TypeAdapter

import config
from pushover import Message, PushoverClient
from sazka import SazkaClient

logger = logging.getLogger("sazka_bonus_calendar_notifier")
logger.setLevel(logging.INFO)
logger_handler = logging.StreamHandler()
logger_handler.setLevel(logging.INFO)
logger_formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

config = config.get_instance()
sazka_client = SazkaClient(config.SAZKA_EMAIL, config.SAZKA_PASSWORD.get_secret_value())
pushover_client = PushoverClient(
    config.pushover_api_token.get_secret_value(),
    config.pushover_user_key.get_secret_value(),
)

metadata_directory = os.path.dirname(config.METADATA_FILEPATH)
if metadata_directory:
    os.makedirs(metadata_directory, parents=True, exist_ok=True)


class BonusNotification(BaseModel):
    bonus_id: int
    notified_at: datetime


NotificationList: TypeAlias = list[BonusNotification]
NotificationListModel = TypeAdapter(NotificationList)


def get_notification_list() -> list[BonusNotification]:
    if not os.path.exists(config.METADATA_FILEPATH):
        return []
    with open(config.metadata_filepath, "rb") as file:
        return NotificationListModel.validate_json(file.read())


def set_notification_list(notification_list: list[BonusNotification]) -> None:
    with open(config.metadata_filepath, "wb") as file:
        file.write(NotificationListModel.dump_json(notification_list))


def main() -> None:
    notification_list = get_notification_list()
    calendars = sazka_client.get_calendars()

    if calendars:
        logger.info(f"Found {len(calendars)} active bonus calendars")
    else:
        logger.info("There are currently no active bonus calendars")

    for calendar in calendars:
        active_bonuses = [bonus for bonus in calendar.bonuses if bonus.state == 1]

        if not active_bonuses:
            logger.info(f"{calendar.title} -> There are currently no active bonuses")

        for bonus in active_bonuses:
            if any(notification.bonus_id == bonus.id for notification in notification_list):
                logger.info(f"{calendar.title} -> {bonus.title} -> Already notified about this bonus")
                continue

            notified_at = datetime.now()
            message = Message(
                title=f"Sazka: {calendar.title}",
                message=f"<h2>{bonus.title}</h2>{bonus.text}",
                html=True,
                url=calendar.url,
                timestamp=int(notified_at.timestamp()),
            )
            pushover_client.send_message(message)
            notification_list.append(BonusNotification(bonus_id=bonus.id, notified_at=notified_at))

            logger.info(f"{calendar.title} -> {bonus.title} -> Sent a notification")
    set_notification_list(notification_list)


if __name__ == "__main__":
    main()
