"""Satka: кнопка «Отчёты» на главной админ-панели + отчёт за сегодня (МСК)."""

from __future__ import annotations

from datetime import datetime

import structlog
from aiogram import Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.localization.texts import get_texts
from app.services.reporting_service import ReportPeriod, ReportingServiceError, reporting_service
from app.utils.decorators import admin_required, error_handler

logger = structlog.get_logger(__name__)
_PATCHED = False


def _patch_admin_main_keyboard() -> None:
    import app.keyboards.admin as admin_kb

    if getattr(admin_kb, '_satka_reports_main_patched', False):
        return

    original = admin_kb.get_admin_main_keyboard

    def get_admin_main_keyboard(language: str = 'ru') -> InlineKeyboardMarkup:
        kb = original(language)
        rows = list(kb.inline_keyboard)

        reports_btn = InlineKeyboardButton(
            text='📊 Отчёты',
            callback_data='admin_reports',
        )

        inserted = False
        for i, row in enumerate(rows):
            if any(getattr(btn, 'callback_data', None) == 'back_to_menu' for btn in row):
                rows.insert(i, [reports_btn])
                inserted = True
                break
        if not inserted:
            rows.append([reports_btn])

        return InlineKeyboardMarkup(inline_keyboard=rows)

    get_admin_main_keyboard._satka_reports_main_patched = True
    admin_kb.get_admin_main_keyboard = get_admin_main_keyboard
    admin_kb._satka_reports_main_patched = True
    logger.info('satka_admin_keyboard: Reports button added to main admin panel')


def _satka_reports_keyboard(language: str = 'ru') -> InlineKeyboardMarkup:
    texts = get_texts(language)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='📅 За сегодня (МСК)',
                    callback_data='admin_reports_today',
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts.t('ADMIN_REPORTS_PREVIOUS_DAY', '📆 За вчера'),
                    callback_data='admin_reports_daily',
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts.t('ADMIN_REPORTS_LAST_WEEK', '🗓️ За неделю'),
                    callback_data='admin_reports_weekly',
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts.t('ADMIN_REPORTS_LAST_MONTH', '📅 За месяц'),
                    callback_data='admin_reports_monthly',
                )
            ],
            [InlineKeyboardButton(text=texts.BACK, callback_data='admin_panel')],
        ]
    )


def _patch_reports_keyboard() -> None:
    import app.handlers.admin.reports as reports_mod
    import app.keyboards.admin as admin_kb

    if getattr(admin_kb, '_satka_reports_today_patched', False):
        return

    admin_kb.get_admin_reports_keyboard = _satka_reports_keyboard
    reports_mod.get_admin_reports_keyboard = _satka_reports_keyboard
    admin_kb._satka_reports_today_patched = True
    reports_mod._satka_reports_today_patched = True
    logger.info('satka_admin_keyboard: today report option added')


def _register_today_report_handler() -> None:
    from app.handlers.admin import reports as reports_mod
    from app.keyboards.admin import get_admin_report_result_keyboard

    if getattr(reports_mod, '_satka_today_report_patched', False):
        return

    @admin_required
    @error_handler
    async def send_today_report(
        callback: types.CallbackQuery,
        db_user,
        db,
    ) -> None:
        try:
            from zoneinfo import ZoneInfo

            msk = ZoneInfo('Europe/Moscow')
            today_msk = datetime.now(msk).date()
            report_text = await reporting_service.send_report(
                ReportPeriod.DAILY,
                report_date=today_msk,
                send_to_topic=True,
            )
        except ReportingServiceError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except Exception as exc:
            logger.error('satka_admin_keyboard: today report failed', error=str(exc))
            await callback.answer('Не удалось отправить отчёт.', show_alert=True)
            return

        await callback.message.answer(
            report_text,
            reply_markup=get_admin_report_result_keyboard(db_user.language),
        )
        await callback.answer('Отчёт за сегодня отправлен')

    original_register = reports_mod.register_handlers

    def register_handlers(dp: Dispatcher) -> None:
        original_register(dp)
        dp.callback_query.register(send_today_report, F.data == 'admin_reports_today')

    reports_mod.register_handlers = register_handlers
    reports_mod._satka_today_report_patched = True
    logger.info('satka_admin_keyboard: today report handler registered')


def apply_satka_admin_keyboard_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _patch_admin_main_keyboard()
    _patch_reports_keyboard()
    _register_today_report_handler()
    _PATCHED = True
    logger.info('satka_admin_keyboard: applied')
