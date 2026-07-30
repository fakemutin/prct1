"""SatkaVPN: одна бесплатная подписка, платные без free, корректные ссылки."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Subscription, Transaction

logger = structlog.get_logger(__name__)

TARIFF_FREE_ID = 6
ACTIVE_STATUSES = ('active', 'trial', 'limited')

FREE_TARIFF_DENIED_MESSAGE = (
    'Бесплатный тариф нельзя продлить повторно.\n\n'
    'Выберите платный тариф — например, Базовый (50 ₽/мес).'
)
FREE_TARIFF_ALREADY_USED_MESSAGE = (
    'Бесплатный тариф можно оформить только один раз.\n\n'
    'Выберите платный тариф — например, Базовый (50 ₽/мес).'
)


async def user_has_real_paid_purchase(db: AsyncSession, user_id: int) -> bool:
    from app.database.crud.user import get_user_by_id

    user = await get_user_by_id(db, user_id)
    if user and getattr(user, 'has_had_paid_subscription', False):
        return True

    result = await db.execute(
        select(
            exists().where(
                Transaction.user_id == user_id,
                Transaction.type == 'subscription_payment',
                Transaction.is_completed.is_(True),
                Transaction.amount_kopeks != 0,
            )
        )
    )
    return bool(result.scalar())


async def get_active_subscriptions(db: AsyncSession, user_id: int) -> list[Subscription]:
    from app.database.crud.subscription import get_active_subscriptions_by_user_id

    return list(await get_active_subscriptions_by_user_id(db, user_id))


def is_free_tariff(tariff_id: int | None) -> bool:
    return tariff_id == TARIFF_FREE_ID


def is_paid_tariff(tariff_id: int | None) -> bool:
    return bool(tariff_id) and tariff_id != TARIFF_FREE_ID


def tariff_is_free(tariff_id: int | None, tariff=None) -> bool:
    if is_free_tariff(tariff_id):
        return True
    if tariff is not None and bool(getattr(tariff, 'is_free', False)):
        return True
    return False


async def user_had_free_tariff(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(
        select(
            exists().where(
                Subscription.user_id == user_id,
                Subscription.tariff_id == TARIFF_FREE_ID,
            )
        )
    )
    return bool(result.scalar())


async def ensure_tariff_extend_allowed(
    db: AsyncSession,
    user_id: int,
    tariff_id: int,
    *,
    tariff=None,
) -> tuple[bool, str]:
    del db, user_id
    if tariff_is_free(tariff_id, tariff):
        return False, FREE_TARIFF_DENIED_MESSAGE
    return True, ''


def pick_primary_subscription(subscriptions: list[Subscription]) -> Subscription | None:
    """Для меню/подключения: платная важнее бесплатной."""
    if not subscriptions:
        return None
    paid = [s for s in subscriptions if is_paid_tariff(s.tariff_id)]
    if paid:
        return paid[0]
    free = [s for s in subscriptions if is_free_tariff(s.tariff_id)]
    if free:
        return free[0]
    return subscriptions[0]


async def _disable_subscription(db: AsyncSession, sub: Subscription) -> None:
    sub.status = 'disabled'
    sub.is_trial = False
    sub.autopay_enabled = False
    sub.updated_at = datetime.now(UTC)


async def deactivate_other_subscriptions(
    db: AsyncSession,
    user_id: int,
    *,
    keep_subscription_id: int,
    purchased_tariff_id: int | None,
) -> int:
    """Не ломаем мульти-тариф: платные живут параллельно, чистим только лишние free/trial."""
    from app.database.crud.subscription import get_active_subscriptions_by_user_id

    active = await get_active_subscriptions_by_user_id(db, user_id)
    disabled = 0
    for sub in active:
        if sub.id == keep_subscription_id:
            continue

        should_disable = False
        if is_paid_tariff(purchased_tariff_id):
            # Новая/продлённая платная — убираем только бесплатные и триалы.
            if is_free_tariff(sub.tariff_id) or bool(getattr(sub, 'is_trial', False)):
                should_disable = True
        elif is_free_tariff(purchased_tariff_id):
            # Бесплатная — убираем только другие бесплатные (платные не трогаем).
            if is_free_tariff(sub.tariff_id) and sub.id != keep_subscription_id:
                should_disable = True

        if should_disable:
            await _disable_subscription(db, sub)
            disabled += 1
            logger.info(
                'satka_policy: disabled extra subscription',
                user_id=user_id,
                disabled_sub_id=sub.id,
                tariff_id=sub.tariff_id,
                purchased_tariff_id=purchased_tariff_id,
            )
    if disabled:
        await db.flush()
    return disabled


async def ensure_tariff_purchase_allowed(
    db: AsyncSession, user_id: int, tariff_id: int
) -> tuple[bool, str]:
    active = await get_active_subscriptions(db, user_id)
    if is_free_tariff(tariff_id):
        if await user_has_real_paid_purchase(db, user_id):
            return False, 'У вас уже есть платная подписка. Бесплатный тариф недоступен.'
        if any(is_paid_tariff(s.tariff_id) for s in active):
            return False, 'Сначала используйте платную подписку. Бесплатный тариф недоступен.'
        if any(is_free_tariff(s.tariff_id) for s in active):
            return False, FREE_TARIFF_DENIED_MESSAGE
        if await user_had_free_tariff(db, user_id):
            return False, FREE_TARIFF_ALREADY_USED_MESSAGE
        return True, ''
    return True, ''


def filter_purchase_tariffs(tariffs: list, *, hide_free: bool) -> list:
    if not hide_free:
        return tariffs
    return [t for t in tariffs if getattr(t, 'id', None) != TARIFF_FREE_ID]


async def should_hide_free_tariff(db: AsyncSession, user_id: int) -> bool:
    if await user_has_real_paid_purchase(db, user_id):
        return True
    active = await get_active_subscriptions(db, user_id)
    return any(is_paid_tariff(s.tariff_id) for s in active)


async def after_successful_tariff_purchase(
    db: AsyncSession,
    user_id: int,
    tariff_id: int | None,
    subscription_id: int,
) -> None:
    await deactivate_other_subscriptions(
        db,
        user_id,
        keep_subscription_id=subscription_id,
        purchased_tariff_id=tariff_id,
    )
