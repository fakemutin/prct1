#!/usr/bin/env python3
"""Restore subscriptions for users who paid but stayed is_trial (bug #subscription_trial_fix).

Safe: keeps subscription_url, remnawave_uuid, remnawave_short_id unchanged.
Only updates end_date, is_trial, status and syncs expiry to Remnawave panel.
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select

logger = structlog.get_logger(__name__)

PERIOD_RE = re.compile(r'(\d+)\s*дн', re.IGNORECASE)

# emeraIday: extend added 60d to in-memory trial end (2026-10-08 UTC per bot logs)
_HARDCODED_ENDS: dict[int, datetime] = {
    173: datetime(2026, 10, 8, 22, 57, 8, 267911, tzinfo=UTC),
}


def _parse_period_days(description: str) -> int | None:
    match = PERIOD_RE.search(description or '')
    return int(match.group(1)) if match else None


def _calc_target_end(
    *,
    sub_id: int,
    paid_at: datetime,
    period_days: int,
    description: str,
    now: datetime,
) -> datetime:
    if sub_id in _HARDCODED_ENDS:
        hardcoded = _HARDCODED_ENDS[sub_id]
        return hardcoded if hardcoded > now else now + timedelta(days=period_days)

    paid_at_utc = paid_at.astimezone(UTC) if paid_at.tzinfo else paid_at.replace(tzinfo=UTC)
    target = paid_at_utc + timedelta(days=period_days)

    if target <= now:
        return now + timedelta(days=period_days)
    return target


async def compensate(*, dry_run: bool = False) -> list[dict]:
    from app.database.database import AsyncSessionLocal
    from app.database.models import Subscription, Transaction, User
    from app.services.subscription_service import SubscriptionService

    now = datetime.now(UTC)
    results: list[dict] = []

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Subscription, Transaction, User)
            .join(User, User.id == Subscription.user_id)
            .join(
                Transaction,
                (Transaction.user_id == Subscription.user_id)
                & (Transaction.type == 'subscription_payment')
                & (Transaction.amount_kopeks < 0)
                & Transaction.is_completed.is_(True),
            )
            .where(Subscription.is_trial.is_(True))
            .order_by(Transaction.created_at)
        )

        seen_subs: set[int] = set()
        service = SubscriptionService()

        for subscription, tx, user in rows.all():
            if subscription.id in seen_subs:
                continue
            seen_subs.add(subscription.id)

            period = _parse_period_days(tx.description)
            if not period:
                logger.warning('skip: cannot parse period', sub_id=subscription.id, description=tx.description)
                continue

            old_end = subscription.end_date
            old_url = subscription.subscription_url
            target_end = _calc_target_end(
                sub_id=subscription.id,
                paid_at=tx.created_at,
                period_days=period,
                description=tx.description,
                now=now,
            )

            entry = {
                'user_id': user.id,
                'username': user.username,
                'sub_id': subscription.id,
                'period_days': period,
                'old_end': str(old_end),
                'new_end': str(target_end),
                'old_status': subscription.status,
                'url': old_url,
            }
            results.append(entry)

            if dry_run:
                logger.info('dry-run compensate', **entry)
                continue

            subscription.is_trial = False
            subscription.status = 'active'
            subscription.end_date = target_end
            subscription.updated_at = now

            if hasattr(user, 'has_had_paid_subscription'):
                user.has_had_paid_subscription = True

            await db.commit()
            await db.refresh(subscription)

            if subscription.subscription_url != old_url:
                raise RuntimeError(f'subscription_url changed for {subscription.id}')

            try:
                await service.update_remnawave_user(db, subscription, reset_traffic=False)
            except Exception as error:
                logger.warning('remnawave sync failed', sub_id=subscription.id, error=error)
                entry['remnawave_error'] = str(error)

            logger.info('compensated subscription', **entry)

    return results


def main() -> int:
    dry_run = '--dry-run' in sys.argv
    rows = asyncio.run(compensate(dry_run=dry_run))
    print(f'{"DRY RUN: " if dry_run else ""}Processed {len(rows)} subscriptions')
    for row in rows:
        print(
            f"  @{row.get('username') or row['user_id']} sub={row['sub_id']} "
            f"{row['old_end']} -> {row['new_end']} ({row['period_days']}d)"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
