from pyrogram.types import InlineKeyboardButton
from pyrogram.enums import ButtonStyle

import config
from AloneMusic import app


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHAT,
                style=ButtonStyle.SUCCESS,
            ),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style=ButtonStyle.PRIMARY,
            )
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                callback_data="settings_back_helper",
                style=ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_2"],
                callback_data="Alone_Music",
                style=ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                text="⌯ ꜱᴏᴜʀᴄᴇ ⌯",
                callback_data="gib_source",
                style=ButtonStyle.PRIMARY,
            ),
        ],
        [
            InlineKeyboardButton(
                text="⌯ ʙᴏᴛꜱ ꜱᴛᴀᴛs ⌯",
                url="https://t.me/ll_ROYAL_ABOUT_ll",
                style=ButtonStyle.DANGER,
            ),
        ],
    ]

    return buttons
