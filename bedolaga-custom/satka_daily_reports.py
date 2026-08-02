"""SatkaVPN: дополняем ежедневный отчёт метриками оттока и email-пользователей."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql import false, true

logger = structlog.get_logger(__name__)
_PATCHED = False


async def _collect_churn_stats(session, start_utc: datetime, end_utc: datetime) -> dict[str, int]:
    from app.database.models import Subscription, SubscriptionStatus

    expired_paid = int(
        (
            await session.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.is_trial == false(),
                    Subscription.status == SubscriptionStatus.EXPIRED.value,
                    Subscription.end_date >= start_utc,
                    Subscription.end_date < end_utc,
                )
            )
        ).scalar()
        or 0
    )

    expired_trials = int(
        (
            await session.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.is_trial == true(),
                    Subscription.end_date >= start_utc,
                    Subscription.end_date < end_utc,
                )
            )
        ).scalar()
        or 0
    )

    return {
        'expired_paid_subscriptions': expired_paid,
        'expired_trials': expired_trials,
    }


async def _collect_email_user_stats(session, start_utc: datetime, end_utc: datetime) -> dict[str, int]:
    from app.database.models import User, UserStatus

    email_filter = and_(
        User.email.isnot(None),
        User.email != '',
        or_(
            User.auth_type == 'email',
            and_(User.password_hash.isnot(None), User.telegram_id.is_(None)),
        ),
        User.status != UserStatus.DELETED.value,
    )

    total = int((await session.execute(select(func.count(User.id)).where(email_filter))).scalar() or 0)
    verified = int(
        (
            await session.execute(
                select(func.count(User.id)).where(email_filter, User.email_verified == true())
            )
        ).scalar()
        or 0
    )
    new_in_period = int(
        (
            await session.execute(
                select(func.count(User.id)).where(
                    email_filter,
                    User.created_at >= start_utc,
                    User.created_at < end_utc,
                )
            )
        ).scalar()
        or 0
    )
    with_telegram = int(
        (
            await session.execute(
                select(func.count(User.id)).where(email_filter, User.telegram_id.isnot(None))
            )
        ).scalar()
        or 0
    )

    return {
        'email_users_total': total,
        'email_users_verified': verified,
        'email_users_new': new_in_period,
        'email_users_with_telegram': with_telegram,
    }


def _inject_churn_lines(report_text: str, churn: dict[str, int]) -> str:
    marker = '• Поступления всего (только пополнения):'
    churn_block = (
        f'• Истекло платных подписок (отток): {churn["expired_paid_subscriptions"]} \n'
        f'• Завершилось триалов: {churn["expired_trials"]} '
    )

    if marker not in report_text:
        return report_text + '\n\n📉 Отток \n' + churn_block

    before, after = report_text.split(marker, 1)
    line_end = after.find('\n')
    if line_end == -1:
        return report_text

    return before + marker + after[:line_end] + '\n' + churn_block + after[line_end:]


def _inject_email_lines(report_text: str, email_stats: dict[str, int]) -> str:
    block = (
        '\n\n📧 <b>Почтовики (email-регистрация)</b>\n'
        f'• Всего email-пользователей: <b>{email_stats["email_users_total"]}</b>\n'
        f'• Подтверждённых: <b>{email_stats["email_users_verified"]}</b>\n'
        f'• Новых за период: <b>{email_stats["email_users_new"]}</b>\n'
        f'• С привязанным Telegram: <b>{email_stats["email_users_with_telegram"]}</b>'
    )
    return report_text + block


def apply_satka_daily_reports_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return

    from app.database.database import AsyncSessionLocal
    from app.services.reporting_service import ReportPeriod, ReportingService

    _orig_build_report = ReportingService._build_report

    async def _build_report(self, period, report_date=None):
        report_text = await _orig_build_report(self, period, report_date)
        if period != ReportPeriod.DAILY:
            return report_text

        period_range = self._get_period_range(period, report_date)
        start_utc = period_range.start_msk.astimezone(UTC)
        end_utc = period_range.end_msk.astimezone(UTC)

        async with AsyncSessionLocal() as session:
            churn = await _collect_churn_stats(session, start_utc, end_utc)
            email_stats = await _collect_email_user_stats(session, start_utc, end_utc)

        report_text = _inject_churn_lines(report_text, churn)
        return _inject_email_lines(report_text, email_stats)

    ReportingService._build_report = _build_report

    _PATCHED = True
    logger.info('satka_daily_reports: applied (churn + email users)')
