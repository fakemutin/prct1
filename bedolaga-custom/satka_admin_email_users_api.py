"""Satka: API управления пользователями, зарегистрированными по email."""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cabinet.auth.email_verification import generate_verification_token, get_verification_expires_at
from app.cabinet.auth.password_utils import hash_password
from app.cabinet.dependencies import get_cabinet_db, require_permission
from app.cabinet.services.email_service import email_service
from app.config import settings
from app.database.models import Subscription, SubscriptionStatus, User, UserStatus

logger = structlog.get_logger(__name__)
_API_PATCHED = False


class EmailUserItem(BaseModel):
    id: int
    email: str | None
    email_verified: bool
    first_name: str | None
    status: str
    balance_rubles: float
    created_at: datetime | None
    last_activity: datetime | None
    has_subscription: bool
    subscription_status: str | None
    subscription_end_date: datetime | None
    telegram_id: int | None
    auth_type: str | None


class EmailUsersListResponse(BaseModel):
    items: list[EmailUserItem]
    total: int
    page: int
    page_size: int
    pages: int


class EmailUsersStatsResponse(BaseModel):
    total: int
    verified: int
    unverified: int
    with_active_subscription: int
    registered_today: int
    registered_week: int
    with_telegram_linked: int


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class BroadcastEmailRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body_html: str = Field(min_length=1)
    user_ids: list[int] | None = None
    only_verified: bool = True


class SendEmailRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body_html: str = Field(min_length=1)


class ActionResponse(BaseModel):
    success: bool
    message: str


class BroadcastResultResponse(BaseModel):
    sent: int
    failed: int
    skipped: int


def _email_users_filter():
    return and_(
        User.email.isnot(None),
        User.email != '',
        or_(
            User.auth_type == 'email',
            and_(User.password_hash.isnot(None), User.telegram_id.is_(None)),
        ),
        User.status != UserStatus.DELETED.value,
    )


def _build_item(user: User) -> EmailUserItem:
    subscription = user.subscription
    has_subscription = False
    subscription_status = None
    subscription_end_date = None
    if subscription:
        has_subscription = True
        subscription_status = subscription.status
        subscription_end_date = subscription.end_date

    return EmailUserItem(
        id=user.id,
        email=user.email,
        email_verified=bool(user.email_verified),
        first_name=user.first_name,
        status=user.status,
        balance_rubles=user.balance_rubles,
        created_at=user.created_at,
        last_activity=user.last_activity,
        has_subscription=has_subscription,
        subscription_status=subscription_status,
        subscription_end_date=subscription_end_date,
        telegram_id=user.telegram_id,
        auth_type=user.auth_type,
    )


async def _get_email_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscriptions))
        .where(User.id == user_id, _email_users_filter())
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Email user not found')
    return user


def apply_satka_admin_email_users_api_patch() -> None:
    global _API_PATCHED
    if _API_PATCHED:
        return

    router = APIRouter(prefix='/satka/admin/email-users', tags=['Satka Admin Email Users'])

    @router.get('/stats', response_model=EmailUsersStatsResponse)
    async def email_users_stats(
        admin: User = Depends(require_permission('users:read')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        base = _email_users_filter()
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        total = int((await db.execute(select(func.count(User.id)).where(base))).scalar() or 0)
        verified = int(
            (await db.execute(select(func.count(User.id)).where(base, User.email_verified == True))).scalar() or 0
        )
        unverified = total - verified

        active_sub_q = (
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                base,
                Subscription.status.in_(
                    [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIAL.value]
                ),
                Subscription.end_date > now,
            )
        )
        with_active_subscription = int((await db.execute(active_sub_q)).scalar() or 0)

        registered_today = int(
            (
                await db.execute(
                    select(func.count(User.id)).where(base, User.created_at >= today_start)
                )
            ).scalar()
            or 0
        )
        registered_week = int(
            (
                await db.execute(
                    select(func.count(User.id)).where(base, User.created_at >= week_start)
                )
            ).scalar()
            or 0
        )
        with_telegram_linked = int(
            (
                await db.execute(
                    select(func.count(User.id)).where(base, User.telegram_id.isnot(None))
                )
            ).scalar()
            or 0
        )

        return EmailUsersStatsResponse(
            total=total,
            verified=verified,
            unverified=unverified,
            with_active_subscription=with_active_subscription,
            registered_today=registered_today,
            registered_week=registered_week,
            with_telegram_linked=with_telegram_linked,
        )

    @router.get('', response_model=EmailUsersListResponse)
    async def list_email_users(
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=100),
        search: str | None = Query(None, max_length=255),
        verified: bool | None = None,
        has_subscription: bool | None = None,
        admin: User = Depends(require_permission('users:read')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        filters = [_email_users_filter()]
        if search:
            term = f'%{search.strip()}%'
            filters.append(
                or_(
                    User.email.ilike(term),
                    User.first_name.ilike(term),
                )
            )
        if verified is not None:
            filters.append(User.email_verified == verified)

        where_clause = and_(*filters)
        total = int((await db.execute(select(func.count(User.id)).where(where_clause))).scalar() or 0)
        pages = max(1, math.ceil(total / page_size)) if total else 1
        offset = (page - 1) * page_size

        query = (
            select(User)
            .options(selectinload(User.subscriptions))
            .where(where_clause)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        users = list(result.scalars().all())

        if has_subscription is not None:
            now = datetime.now(UTC)
            filtered = []
            for user in users:
                sub = user.subscription
                active = bool(
                    sub
                    and sub.status in (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIAL.value)
                    and sub.end_date
                    and sub.end_date > now
                )
                if active == has_subscription:
                    filtered.append(user)
            users = filtered

        return EmailUsersListResponse(
            items=[_build_item(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    @router.post('/{user_id}/set-password', response_model=ActionResponse)
    async def set_password(
        user_id: int,
        request: SetPasswordRequest,
        admin: User = Depends(require_permission('users:edit')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        user = await _get_email_user(db, user_id)
        user.password_hash = hash_password(request.password)
        user.password_reset_token = None
        user.password_reset_expires = None
        await db.commit()
        logger.info('satka_admin_email: password set', user_id=user_id, admin_id=admin.id)
        return ActionResponse(success=True, message='Пароль обновлён')

    @router.post('/{user_id}/verify', response_model=ActionResponse)
    async def force_verify(
        user_id: int,
        admin: User = Depends(require_permission('users:edit')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        user = await _get_email_user(db, user_id)
        user.email_verified = True
        user.email_verified_at = datetime.now(UTC)
        user.email_verification_token = None
        user.email_verification_expires = None
        if not user.email_verification_source:
            user.email_verification_source = 'cabinet'
        await db.commit()
        return ActionResponse(success=True, message='Email подтверждён вручную')

    @router.post('/{user_id}/resend-verification', response_model=ActionResponse)
    async def resend_verification(
        user_id: int,
        admin: User = Depends(require_permission('users:edit')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        user = await _get_email_user(db, user_id)
        if user.email_verified:
            raise HTTPException(status_code=400, detail='Email уже подтверждён')
        if not email_service.is_configured():
            raise HTTPException(status_code=503, detail='SMTP не настроен')

        token = generate_verification_token()
        user.email_verification_token = token
        user.email_verification_expires = get_verification_expires_at()
        await db.commit()

        cabinet_url = (settings.CABINET_URL or '').strip().rstrip('/')
        verification_url = f'{cabinet_url}/verify-email'
        lang = user.language or 'ru'

        ok = await asyncio.to_thread(
            email_service.send_verification_email,
            to_email=user.email,
            verification_token=token,
            verification_url=verification_url,
            username=user.first_name,
            language=lang,
        )
        if not ok:
            raise HTTPException(status_code=500, detail='Не удалось отправить письмо')
        return ActionResponse(success=True, message=f'Письмо отправлено на {user.email}')

    @router.post('/{user_id}/block', response_model=ActionResponse)
    async def block_user(
        user_id: int,
        reason: str | None = Query(None, max_length=500),
        admin: User = Depends(require_permission('users:block')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        user = await _get_email_user(db, user_id)
        user.status = UserStatus.BLOCKED.value
        if reason:
            user.restriction_reason = reason
        await db.commit()
        return ActionResponse(success=True, message='Пользователь заблокирован')

    @router.post('/{user_id}/unblock', response_model=ActionResponse)
    async def unblock_user(
        user_id: int,
        admin: User = Depends(require_permission('users:block')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        user = await _get_email_user(db, user_id)
        user.status = UserStatus.ACTIVE.value
        await db.commit()
        return ActionResponse(success=True, message='Пользователь разблокирован')

    @router.post('/{user_id}/send-email', response_model=ActionResponse)
    async def send_single_email(
        user_id: int,
        request: SendEmailRequest,
        admin: User = Depends(require_permission('users:edit')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        user = await _get_email_user(db, user_id)
        if not user.email:
            raise HTTPException(status_code=400, detail='У пользователя нет email')
        if not email_service.is_configured():
            raise HTTPException(status_code=503, detail='SMTP не настроен')

        ok = await asyncio.to_thread(
            email_service.send_email,
            user.email,
            request.subject,
            request.body_html,
        )
        if not ok:
            raise HTTPException(status_code=500, detail='Не удалось отправить письмо')
        return ActionResponse(success=True, message=f'Письмо отправлено на {user.email}')

    @router.post('/broadcast', response_model=BroadcastResultResponse)
    async def broadcast_email(
        request: BroadcastEmailRequest,
        admin: User = Depends(require_permission('users:edit')),
        db: AsyncSession = Depends(get_cabinet_db),
    ):
        if not email_service.is_configured():
            raise HTTPException(status_code=503, detail='SMTP не настроен')

        if request.user_ids:
            query = (
                select(User)
                .where(_email_users_filter(), User.id.in_(request.user_ids))
            )
        else:
            query = select(User).where(_email_users_filter())
            if request.only_verified:
                query = query.where(User.email_verified == True)

        result = await db.execute(query)
        users = list(result.scalars().all())

        sent = failed = skipped = 0
        for user in users:
            if not user.email:
                skipped += 1
                continue
            if request.only_verified and not user.email_verified:
                skipped += 1
                continue
            ok = await asyncio.to_thread(
                email_service.send_email,
                user.email,
                request.subject,
                request.body_html,
            )
            if ok:
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(0.15)

        logger.info(
            'satka_admin_email: broadcast',
            admin_id=admin.id,
            sent=sent,
            failed=failed,
            skipped=skipped,
        )
        return BroadcastResultResponse(sent=sent, failed=failed, skipped=skipped)

    try:
        from app.cabinet.routes import router as cabinet_router

        cabinet_router.include_router(router)
    except Exception as exc:
        logger.warning('satka_admin_email_users_api: router not mounted', error=str(exc))
        return

    _API_PATCHED = True
    logger.info('satka_admin_email_users_api: applied')
