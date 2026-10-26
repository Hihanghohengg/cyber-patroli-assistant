from telegram import InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore


def get_validation_keyboard(report_id: str) -> InlineKeyboardMarkup:
    """Three-button validation keyboard sent with the finding card.

    Buttons:
    - [ ✓ Validasi (Setuju) ]
    - [ ✏ Ubah Kategori / Risiko ]
    - [ ✕ Bukan Pelanggaran ]
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "✓ Validasi (Setuju)",
                callback_data=f"val:approve:{report_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "✏ Ubah Kategori / Risiko",
                callback_data=f"val:edit:{report_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "✕ Bukan Pelanggaran",
                callback_data=f"val:reject:{report_id}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_category_correction_keyboard(report_id: str) -> InlineKeyboardMarkup:
    """Follow-up keyboard when the analyst wants to override the AI category."""
    keyboard = [
        [
            InlineKeyboardButton(
                "HOAKS",
                callback_data=f"setcat:HOAKS:{report_id}",
            ),
            InlineKeyboardButton(
                "UJARAN KEBENCIAN",
                callback_data=f"setcat:UJARAN_KEBENCIAN:{report_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "PROVOKASI SARA",
                callback_data=f"setcat:PROVOKASI_SARA:{report_id}",
            ),
            InlineKeyboardButton(
                "PENIPUAN FINANSIAL",
                callback_data=f"setcat:PENIPUAN_FINANSIAL:{report_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "DI LUAR KONTEKS",
                callback_data=f"setcat:DI_LUAR_KONTEKS:{report_id}",
            ),
            InlineKeyboardButton(
                "NETRAL / AMAN",
                callback_data=f"setcat:NETRAL:{report_id}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_risk_correction_keyboard(report_id: str) -> InlineKeyboardMarkup:
    """Follow-up keyboard for risk level override."""
    keyboard = [
        [
            InlineKeyboardButton(
                "🟢 RENDAH",
                callback_data=f"setrisk:RENDAH:{report_id}",
            ),
            InlineKeyboardButton(
                "🟡 SEDANG",
                callback_data=f"setrisk:SEDANG:{report_id}",
            ),
            InlineKeyboardButton(
                "🔴 TINGGI",
                callback_data=f"setrisk:TINGGI:{report_id}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
