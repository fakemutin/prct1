"""Keep trial/gift flag on subscriptions that were never actually paid for."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)
_PATCHED = False


async def _tariff_is_free(db, tariff_id: int | None) -> bool:
    if not tariff_id:
        return False
    try:
        from app.database.crud.tariff import get_tariff_by_id

        tariff = await get_tariff_by_id(db, tariff_id)
        return bool(tariff and tariff.is_free)
    except Exception as error:
        logger.warning('subscription_trial_fix: tariff lookup failed', tariff_id=tariff_id, error=error)
        return False


def apply_subscription_trial_fix() -> None:
    global _PATCHED
    if _PATCHED:
        return

    from app.database.crud import subscription as sub_crud

    _orig_extend = sub_crud.extend_subscription
    _orig_create_paid = sub_crud.create_paid_subscription

    async def extend_subscription(db, subscription, days, *args, convert_trial: bool = True, tariff_id=None, **kwargs):
        skip_policy = kwargs.pop('satka_skip_subscription_policy', False)
        if convert_trial and subscription and getattr(subscription, 'is_trial', False):
            if await _tariff_is_free(db, tariff_id or getattr(subscription, 'tariff_id', None)):
                convert_trial = False
            # Do NOT check prior subscription_payment here: balance is already deducted
            # and the transaction is created after extend. That race left is_trial=True
            # and subscriptions expired at trial end despite payment.
        result = await _orig_extend(
            db,
            subscription,
            days,
            *args,
            convert_trial=convert_trial,
            tariff_id=tariff_id,
            **kwargs,
        )
        if result and not skip_policy and getattr(result, 'id', None):
            from app.utils.satka_subscription_policy import after_successful_tariff_purchase

            try:
                await after_successful_tariff_purchase(
                    db,
                    result.user_id,
                    tariff_id or getattr(result, 'tariff_id', None),
                    result.id,
                )
            except Exception as error:
                logger.warning('satka_policy extend cleanup failed', error=error)
        return result

    async def create_paid_subscription(
        db,
        user_id: int,
        duration_days: int,
        *args,
        is_trial: bool = False,
        tariff_id=None,
        **kwargs,
    ):
        skip_policy = kwargs.pop('satka_skip_subscription_policy', False)
        if not is_trial and await _tariff_is_free(db, tariff_id):
            is_trial = True
        elif is_trial and tariff_id and not await _tariff_is_free(db, tariff_id):
            # Paid tariff purchase must not stay trial (same class of bug as extend).
            is_trial = False
        result = await _orig_create_paid(
            db,
            user_id,
            duration_days,
            *args,
            is_trial=is_trial,
            tariff_id=tariff_id,
            **kwargs,
        )
        if result and not is_trial and getattr(result, 'is_trial', False) and tariff_id:
            if not await _tariff_is_free(db, tariff_id):
                result.is_trial = False
        if result and not skip_policy and getattr(result, 'id', None):
            from app.utils.satka_subscription_policy import after_successful_tariff_purchase

            try:
                await after_successful_tariff_purchase(
                    db,
                    user_id,
                    tariff_id,
                    result.id,
                )
            except Exception as error:
                logger.warning('satka_policy create cleanup failed', error=error)
        return result

    sub_crud.extend_subscription = extend_subscription
    sub_crud.create_paid_subscription = create_paid_subscription
    _PATCHED = True
    logger.info('subscription_trial_fix: patched extend_subscription and create_paid_subscription')
