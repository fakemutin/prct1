"""Apply all SatkaVPN monkey-patches once at bot startup."""

from __future__ import annotations

import asyncio
import os

import structlog

logger = structlog.get_logger(__name__)
_APPLIED = False



async def _ensure_telegram_menu_button_for_chat(chat_id: int) -> None:
    cabinet_url = (os.environ.get('MINIAPP_CUSTOM_URL') or os.environ.get('CABINET_URL') or '').strip().rstrip('/')
    token = (os.environ.get('BOT_TOKEN') or '').strip()
    if not cabinet_url or not token or not chat_id:
        return
    try:
        from aiogram import Bot
        from aiogram.types import MenuButtonWebApp, WebAppInfo
        bot = Bot(token=token)
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(
                text='📱 Кабинет',
                web_app=WebAppInfo(url=f'{cabinet_url}/'),
            ),
        )
        await bot.session.close()
    except Exception as exc:
        logger.warning('satka_bootstrap: per-chat menu button failed', chat_id=chat_id, error=str(exc))


def _patch_start_menu_button() -> None:
    try:
        import app.handlers.start as start_mod
        if getattr(start_mod.cmd_start, '_satka_menu_patched', False):
            return
        original = start_mod.cmd_start

        async def cmd_start_with_menu(message, state, db, db_user=None):
            try:
                if message and message.chat:
                    await _ensure_telegram_menu_button_for_chat(message.chat.id)
            except Exception:
                pass
            return await original(message, state, db, db_user=db_user)

        cmd_start_with_menu._satka_menu_patched = True
        start_mod.cmd_start = cmd_start_with_menu
        logger.info('satka_bootstrap: patched cmd_start for per-chat menu button')
    except Exception as exc:
        logger.warning('satka_bootstrap: start patch skipped', error=str(exc))


async def _ensure_telegram_menu_button() -> None:
    cabinet_url = (os.environ.get('MINIAPP_CUSTOM_URL') or os.environ.get('CABINET_URL') or '').strip().rstrip('/')
    token = (os.environ.get('BOT_TOKEN') or '').strip()
    if not cabinet_url or not token:
        return

    try:
        from aiogram import Bot
        from aiogram.types import MenuButtonWebApp, WebAppInfo

        bot = Bot(token=token)
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text='📱 Кабинет',
                web_app=WebAppInfo(url=f'{cabinet_url}/'),
            )
        )
        await bot.session.close()
        logger.info('satka_bootstrap: Telegram menu button set', url=cabinet_url)
    except Exception as exc:
        logger.warning('satka_bootstrap: failed to set menu button', error=str(exc))


def apply_satka_patches() -> None:
    global _APPLIED
    if _APPLIED:
        return

    from app.utils.satka_admin_email_users_api import apply_satka_admin_email_users_api_patch
    from app.utils.satka_admin_keyboard import apply_satka_admin_keyboard_patch
    from app.utils.satka_balance_topup import apply_satka_balance_topup_patch
    from app.utils.satka_daily_reports import apply_satka_daily_reports_patch
    from app.utils.satka_free_trial_patches import apply_satka_free_trial_patches
    from app.utils.satka_menu_button_styles import apply_satka_menu_button_styles
    from app.utils.satka_referral_wheel import apply_satka_referral_wheel_patch
    from app.utils.satka_referral_wheel_cabinet_api import apply_satka_referral_wheel_cabinet_api_patch
    from app.utils.satka_cabinet_subscription_domain import apply_satka_cabinet_subscription_domain_patch
    from app.utils.satka_subscription_reminders import apply_satka_subscription_reminders_patch
    from app.utils.satka_vpn_logo import apply_vpn_logo_no_resize
    from app.utils.subscription_trial_fix import apply_subscription_trial_fix

    apply_subscription_trial_fix()
    apply_satka_free_trial_patches()
    apply_satka_menu_button_styles()
    apply_satka_balance_topup_patch()
    apply_vpn_logo_no_resize()
    apply_satka_daily_reports_patch()
    apply_satka_admin_keyboard_patch()
    apply_satka_subscription_reminders_patch()
    apply_satka_referral_wheel_patch()
    apply_satka_referral_wheel_cabinet_api_patch()
    apply_satka_admin_email_users_api_patch()
    apply_satka_cabinet_subscription_domain_patch()
    _patch_start_menu_button()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_ensure_telegram_menu_button())
        else:
            loop.run_until_complete(_ensure_telegram_menu_button())
    except Exception as exc:
        logger.warning('satka_bootstrap: menu button task skipped', error=str(exc))

    _APPLIED = True
    logger.info('satka_bootstrap: all patches applied')
