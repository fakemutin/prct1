def get_stat_value(key, default=0):
    c = get_cursor()
    c.execute('SELECT value FROM stats WHERE key = ?', (key,))
    row = c.fetchone()
    if not row:
        return default
    try:
        return row['value']
    except Exception:
        try:
            return row[0]
        except Exception:
            return default


def send_mailing(msg, count, chat_id, user_id):
    c = get_cursor()
    if count == 0:
        c.execute('SELECT chatId FROM users')
    else:
        c.execute('SELECT chatId FROM users ORDER BY RANDOM() LIMIT ?', (count,))
    users = c.fetchall()
    sent = 0
    for row in users:
        try:
            bot.send_message(row['chatId'], msg, parse_mode='HTML')
            sent += 1
            time.sleep(0.05)
        except Exception:
            pass
    safe_send(chat_id, f"✅ Рассылка завершена! Отправлено {sent} пользователям.")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data

    if data == 'check_sub':
        if check_subscription(user_id):
            safe_send(
                chat_id,
                "✅ Подписка подтверждена! Теперь вы можете пользоваться ботом.",
                reply_markup=main_menu(user_id),
            )
        else:
            safe_answer(call.id, "❌ Вы ещё не подписались!", alert=True)
        return

    if data == 'check_extra_sub':
        if check_extra_subscriptions(user_id):
            safe_send(
                chat_id,
                "✅ Подписка подтверждена! Теперь вы можете пользоваться ботом.",
                reply_markup=main_menu(user_id),
            )
        else:
            safe_answer(call.id, "❌ Вы ещё не подписались на все каналы!", alert=True)
        return

    if data.startswith('claim_task_'):
        try:
            task_id = int(data.split('_')[2])
        except Exception:
            safe_answer(call.id, "❌ Некорректное задание.", alert=True)
            return
        success, msg = claim_daily_reward(user_id, task_id)
        safe_answer(call.id, msg, alert=True)
        tasks = get_daily_tasks(user_id)
        if tasks:
            text = "📋 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n"
            kb = InlineKeyboardMarkup()
            for task in tasks:
                if task['completed'] and task['claimed']:
                    status = "✅"
                elif task['completed'] and not task['claimed']:
                    status = "🔄 Готово!"
                else:
                    status = f"🔄 {task['progress']}/{task['target']}"
                text += (
                    f"{status} {task['text']}\n"
                    f"Награда: +{task['reward_money']:.2f} CRF, +{task['reward_exp']} опыта\n\n"
                )
                if task['completed'] and not task['claimed']:
                    kb.add(
                        InlineKeyboardButton(
                            f'🎁 Забрать награду #{task["id"]}',
                            callback_data=f'claim_task_{task["id"]}',
                        )
                    )
            safe_send(chat_id, text, parse_mode='HTML', reply_markup=kb if kb.keyboard else None)
        else:
            safe_send(chat_id, "📭 Сегодня заданий нет.")
        return

    if data.startswith('duel_accept_'):
        try:
            duel_id = int(data.split('_')[2])
        except Exception:
            safe_answer(call.id, "❌ Некорректная дуэль.", alert=True)
            return
        duel = get_duel(duel_id)
        if not duel or duel['status'] != 'waiting':
            safe_send(chat_id, "❌ Дуэль неактивна.")
            safe_answer(call.id)
            return
        if duel['creator_id'] == user_id:
            safe_send(chat_id, "❌ Нельзя принять свою дуэль.")
            safe_answer(call.id)
            return
        amount = duel['amount']
        if get_balance_rub(user_id) < amount:
            safe_send(chat_id, f"❌ Недостаточно средств. Нужно {amount:.2f} ₽")
            safe_answer(call.id)
            return
        limit_ok, limit_msg = check_duel_limit(user_id)
        if not limit_ok:
            safe_send(chat_id, limit_msg)
            safe_answer(call.id)
            return
        add_transaction_rub(user_id, -amount, 'duel_hold', f'Принятие дуэли #{duel_id}')
        c = get_cursor()
        c.execute(
            '''
            UPDATE duels
            SET opponent_id = ?, status = 'active', updated_at = CURRENT_TIMESTAMP,
                elo_opponent = (SELECT elo_rating FROM users WHERE chatId = ?)
            WHERE id = ?
            ''',
            (user_id, user_id, duel_id),
        )
        db.commit()
        if duel['mode'] == 'classic':
            success, msg = resolve_classic_duel(duel_id)
            safe_send(chat_id, msg, reply_markup=duel_kb())
            safe_answer(call.id)
            return
        rps_kb = InlineKeyboardMarkup(row_width=3)
        rps_kb.row(
            InlineKeyboardButton('✊', callback_data=f'rps_{duel_id}_rock'),
            InlineKeyboardButton('✌️', callback_data=f'rps_{duel_id}_scissors'),
            InlineKeyboardButton('✋', callback_data=f'rps_{duel_id}_paper'),
        )
        safe_send(duel['creator_id'], "✊ Сделайте выбор:", reply_markup=rps_kb)
        safe_send(user_id, "✊ Сделайте выбор:", reply_markup=rps_kb)
        safe_send(chat_id, "⚔️ Дуэль начата, ждите выбора.", reply_markup=duel_kb())
        safe_answer(call.id)
        return

    if data.startswith('rps_'):
        parts = data.split('_')
        if len(parts) < 3:
            safe_answer(call.id, "❌ Некорректный выбор.", alert=True)
            return
        try:
            duel_id = int(parts[1])
        except Exception:
            safe_answer(call.id, "❌ Некорректная дуэль.", alert=True)
            return
        choice = parts[2]
        success, msg = set_rps_choice(user_id, duel_id, choice)
        safe_send(chat_id, msg, reply_markup=duel_kb())
        safe_answer(call.id)
        return

    if data == 'duel_back_inline':
        safe_send(chat_id, "Дуэли", reply_markup=duel_kb())
        safe_answer(call.id)
        return

    is_admin_user = user_id in ADMIN_IDS
    is_moderator_user = user_id in MODERATOR_IDS or is_admin_user

    if data.startswith('admin_') and not is_admin_user:
        safe_answer(call.id, '⛔ Доступ запрещён!', alert=True)
        return

    if data.startswith('mod_') and not is_moderator_user:
        safe_answer(call.id, '⛔ Доступ запрещён!', alert=True)
        return

    if data == 'mod_ban':
        user_states[user_id] = {'state': 'mod_ban'}
        safe_send(chat_id, "🚫 Введите ID пользователя для блокировки:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_unban':
        user_states[user_id] = {'state': 'mod_unban'}
        safe_send(chat_id, "✅ Введите ID пользователя для разблокировки:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_balance_rub':
        user_states[user_id] = {'state': 'mod_balance_rub'}
        safe_send(chat_id, "💰 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_balance_crf':
        user_states[user_id] = {'state': 'mod_balance_crf'}
        safe_send(chat_id, "💎 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_level':
        user_states[user_id] = {'state': 'mod_level'}
        safe_send(chat_id, "📈 Введите: <user_id> <уровень>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_vip':
        user_states[user_id] = {'state': 'mod_vip'}
        safe_send(chat_id, "👑 Введите: <user_id> <дни>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_cancel_withdraw':
        user_states[user_id] = {'state': 'mod_cancel_withdraw'}
        safe_send(chat_id, "📛 Введите ID заявки на вывод:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_refresh':
        safe_send(chat_id, "👑 АДМИН-ПАНЕЛЬ\n\nВыберите действие:", parse_mode='HTML', reply_markup=admin_kb())
        safe_answer(call.id, '🔄 Обновлено!')
        return

    if data == 'admin_stats':
        c = get_cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0] or 0
        c.execute('SELECT SUM(balance) FROM crf_balances')
        total_crf = c.fetchone()[0] or 0
        c.execute('SELECT SUM(balance) FROM users')
        total_rub = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM crf_orders WHERE status = "active"')
        active_orders = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM duels WHERE status = "finished"')
        total_duels = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM investments WHERE is_active = 1')
        active_investments = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM crf_stakes WHERE is_active = 1')
        active_stakes = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM users WHERE vip_active = 1')
        vip_users = c.fetchone()[0] or 0
        commission_duel = get_stat_value('commission_duel_rub', 0)
        commission_market = get_stat_value('commission_market_rub', 0)
        commission_exchange_rub = get_stat_value('commission_exchange_rub', 0)
        commission_exchange_crf = get_stat_value('commission_exchange_crf', 0)
        commission_invest = get_stat_value('commission_invest_crf', 0)
        total_rub_volume = get_stat_value('total_rub_volume', 0)
        total_crf_volume = get_stat_value('total_crf_volume', 0)
        season = get_active_season()
        season_text = f"Активен: {season['name']}" if season else "Нет активного сезона"
        text = (
            "📊 ДЕТАЛЬНАЯ СТАТИСТИКА БОТА\n\n"
            "👥 Пользователи:\n"
            f"Всего игроков: {total_users}\n"
            f"VIP: {vip_users}\n\n"
            "💎 Криптовалюта CRF:\n"
            f"Всего CRF в обращении: {total_crf:.2f}\n"
            f"Оборот CRF: {total_crf_volume:.2f}\n"
            f"Курс CRF: {get_crf_rate():.4f} ₽\n\n"
            "💰 Финансы:\n"
            f"Всего ₽ в системе: {total_rub:.2f}\n"
            f"Оборот ₽: {total_rub_volume:.2f}\n\n"
            "💸 КОМИССИИ (доход бота):\n"
            f"• С дуэлей (8%): {commission_duel:.2f} ₽\n"
            f"• С рынка (покупка/продажа CRF): {commission_market:.2f} ₽\n"
            f"• С обмена валют (₽): {commission_exchange_rub:.2f} ₽\n"
            f"• С обмена валют (CRF): {commission_exchange_crf:.2f} CRF\n"
            f"• С инвестиций и стейкинга: {commission_invest:.2f} CRF\n\n"
            "🏷️ Рынок:\n"
            f"Активных ордеров: {active_orders}\n\n"
            "⚔️ Дуэли:\n"
            f"Всего проведено: {total_duels}\n\n"
            "📈 Инвестиции и стейкинг:\n"
            f"Активных инвестиций: {active_investments}\n"
            f"Активных стейков: {active_stakes}\n\n"
            "📅 Сезон:\n"
            f"{season_text}"
        )
        safe_send(chat_id, text, parse_mode='HTML')
        safe_answer(call.id)
        return

    if data == 'admin_withdraws':
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE status = 0 ORDER BY created_at ASC LIMIT 1')
        row = c.fetchone()
        if not row:
            safe_send(chat_id, "📭 Нет активных заявок.")
            safe_answer(call.id)
            return
        user = get_user(row['chatId'])
        name = user['firstName'] if user else str(row['chatId'])
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            InlineKeyboardButton('✅ Выплатить', callback_data=f'admin_withdraw_accept_{row["id"]}'),
            InlineKeyboardButton('❌ Отклонить', callback_data=f'admin_withdraw_reject_{row["id"]}'),
        )
        safe_send(
            chat_id,
            (
                "📛 ЗАЯВКА НА ВЫВОД\n\n"
                f"👤 {name} (ID: {row['chatId']})\n"
                f"💰 Сумма: {row['amount']:.2f} ₽\n"
                f"💳 Карта: {row['wallet']}"
            ),
            parse_mode='HTML',
            reply_markup=kb,
        )
        safe_answer(call.id)
        return

    if data.startswith('admin_withdraw_accept_'):
        try:
            withdraw_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE id = ? AND status = 0', (withdraw_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE withdraws SET status = 1 WHERE id = ?', (withdraw_id,))
        db.commit()
        try:
            add_exp(row['chatId'], CONFIG.get('exp_per_withdraw', 20))
        except Exception:
            pass
        try:
            update_task_progress(row['chatId'], 'withdraw', row['amount'])
        except Exception:
            pass
        safe_send(row['chatId'], f"✅ Выплата подтверждена! {row['amount']:.2f} ₽")
        safe_send(chat_id, f"✅ Заявка #{withdraw_id} выплачена.", reply_markup=admin_kb())
        safe_answer(call.id, "✅ Выплачена")
        return

    if data.startswith('admin_withdraw_reject_'):
        try:
            withdraw_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE id = ? AND status = 0', (withdraw_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE withdraws SET status = 2 WHERE id = ?', (withdraw_id,))
        db.commit()
        add_transaction_rub(row['chatId'], row['amount'], 'withdraw_reject', f'Возврат по заявке #{withdraw_id}')
        safe_send(row['chatId'], f"❌ Выплата отклонена. {row['amount']:.2f} ₽ возвращены")
        safe_send(chat_id, f"❌ Заявка #{withdraw_id} отклонена.", reply_markup=admin_kb())
        safe_answer(call.id, "❌ Отклонена")
        return

    if data == 'admin_deposits':
        c = get_cursor()
        c.execute('SELECT * FROM deposits WHERE status = 0 ORDER BY created_at ASC LIMIT 1')
        row = c.fetchone()
        if not row:
            safe_send(chat_id, "📭 Нет активных заявок.")
            safe_answer(call.id)
            return
        user = get_user(row['chatId'])
        name = user['firstName'] if user else str(row['chatId'])
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            InlineKeyboardButton('✅ Подтвердить', callback_data=f'admin_deposit_accept_{row["id"]}'),
            InlineKeyboardButton('❌ Отклонить', callback_data=f'admin_deposit_reject_{row["id"]}'),
        )
        safe_send(
            chat_id,
            (
                "📥 ЗАЯВКА НА ПОПОЛНЕНИЕ\n\n"
                f"👤 {name} (ID: {row['chatId']})\n"
                f"💰 Сумма: {row['amount']:.2f} ₽"
            ),
            parse_mode='HTML',
            reply_markup=kb,
        )
        safe_answer(call.id)
        return

    if data.startswith('admin_deposit_accept_'):
        try:
            deposit_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM deposits WHERE id = ? AND status = 0', (deposit_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE deposits SET status = 1 WHERE id = ?', (deposit_id,))
        db.commit()
        add_transaction_rub(row['chatId'], row['amount'], 'deposit', f'Пополнение по заявке #{deposit_id}')
        try:
            update_task_progress(row['chatId'], 'deposit', row['amount'])
        except Exception:
            pass
        safe_send(row['chatId'], f"✅ Пополнение подтверждено! На баланс зачислено {row['amount']:.2f} ₽")
        safe_send(chat_id, f"✅ Заявка #{deposit_id} подтверждена.", reply_markup=admin_kb())
        safe_answer(call.id, "✅ Подтверждено")
        return

    if data.startswith('admin_deposit_reject_'):
        try:
            deposit_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM deposits WHERE id = ? AND status = 0', (deposit_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE deposits SET status = 2 WHERE id = ?', (deposit_id,))
        db.commit()
        safe_send(row['chatId'], f"❌ Заявка на пополнение #{deposit_id} отклонена.")
        safe_send(chat_id, f"❌ Заявка #{deposit_id} отклонена.", reply_markup=admin_kb())
        safe_answer(call.id, "❌ Отклонено")
        return

    if data == 'admin_replenish_settings':
        c = get_cursor()
        c.execute("SELECT value FROM settings WHERE key = 'replenish_card'")
        card = c.fetchone()
        c.execute("SELECT value FROM settings WHERE key = 'replenish_holder'")
        holder = c.fetchone()
        c.execute("SELECT value FROM settings WHERE key = 'replenish_bank'")
        bank = c.fetchone()
        text = (
            "🏦 ТЕКУЩИЕ РЕКВИЗИТЫ ПОПОЛНЕНИЯ\n\n"
            f"💳 Карта: {card['value'] if card else 'Не указано'}\n"
            f"👤 Держатель: {holder['value'] if holder else 'Не указано'}\n"
            f"🏦 Банк: {bank['value'] if bank else 'Не указано'}\n\n"
            "Для изменения отправьте новую карту, держателя и банк через запятую:\n"
            "<номер карты>, <держатель>, <банк>"
        )
        user_states[user_id] = {'state': 'admin_replenish_update'}
        safe_send(chat_id, text, parse_mode='HTML', reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_broadcast':
        user_states[user_id] = {'state': 'admin_broadcast'}
        safe_send(chat_id, "📟 Введите количество пользователей для рассылки (0 - всем):", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_balance_rub':
        user_states[user_id] = {'state': 'admin_balance_rub'}
        safe_send(chat_id, "💰 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_balance_crf':
        user_states[user_id] = {'state': 'admin_balance_crf'}
        safe_send(chat_id, "💎 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_crf_rate':
        user_states[user_id] = {'state': 'admin_crf_rate'}
        safe_send(chat_id, "📈 Введите новый курс CRF в ₽:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_requests':
        c = get_cursor()
        c.execute(
            '''
            SELECT * FROM moderator_requests
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 20
            '''
        )
        rows = c.fetchall()
        if not rows:
            safe_send(chat_id, "📭 Нет активных запросов модераторов.")
            safe_answer(call.id)
            return
        text = "📋 ЗАПРОСЫ МОДЕРАТОРОВ\n\n"
        for row in rows:
            text += (
                f"🆔 #{row['id']}\n"
                f"👤 Модератор: {row['moderator_id']}\n"
                f"🎯 Цель: {row['target_user_id']}\n"
                f"⚙️ Действие: {row['action_type']}\n"
                f"📝 Данные: {row['data'] or '{}'}\n"
                f"🕒 {row['created_at']}\n\n"
            )
        safe_send(chat_id, text, parse_mode='HTML')
        safe_answer(call.id)
        return

    if data == 'admin_transactions':
        user_states[user_id] = {'state': 'admin_transactions'}
        safe_send(chat_id, "📊 Введите ID пользователя:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_give_level':
        user_states[user_id] = {'state': 'admin_give_level'}
        safe_send(chat_id, "📈 Введите: <user_id> <уровень>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_change_refs':
        user_states[user_id] = {'state': 'admin_change_refs'}
        safe_send(chat_id, "📊 Введите: <user_id> <реф. уровень>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_clear_stats':
        c = get_cursor()
        c.execute('UPDATE stats SET value = 0')
        db.commit()
        safe_send(chat_id, "🗑️ Статистика очищена.", reply_markup=admin_kb())
        safe_answer(call.id)
        return

    if data == 'admin_seasons':
        season = get_active_season()
        if season:
            text = (
                "📅 УПРАВЛЕНИЕ СЕЗОНАМИ\n\n"
                f"Сейчас активен сезон: {season['name']}\n"
                f"Призовой фонд: {season['prize_pool']:.2f} ₽\n\n"
                "Введите название нового сезона:"
            )
        else:
            text = "📅 Введите название нового сезона:"
        user_states[user_id] = {'state': 'admin_seasons_create_name'}
        safe_send(chat_id, text, reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_task_subscribe':
        user_states[user_id] = {'state': 'admin_task_subscribe_channel'}
        safe_send(chat_id, "📝 Введите username канала для задания (без @):", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_tasks_list':
        c = get_cursor()
        c.execute('SELECT * FROM tasks WHERE active = 1 ORDER BY id ASC')
        tasks = c.fetchall()
        if not tasks:
            safe_send(chat_id, "📭 Активных заданий нет.")
            safe_answer(call.id)
            return
        text = "📋 АКТИВНЫЕ ЗАДАНИЯ (подписка)\n\n"
        kb = InlineKeyboardMarkup(row_width=2)
        for task in tasks:
            text += f"🆔 {task['id']} | @{task['channel']} → {task['reward']:.2f} CRF\n"
            kb.add(
                InlineKeyboardButton(
                    f'❌ Удалить #{task["id"]}',
                    callback_data=f'admin_task_delete_{task["id"]}',
                )
            )
            kb.add(
                InlineKeyboardButton(
                    f'✏️ Изменить награду #{task["id"]}',
                    callback_data=f'admin_task_edit_{task["id"]}',
                )
            )
        kb.add(InlineKeyboardButton('🗑️ Удалить все', callback_data='admin_task_delete_all'))
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='admin_refresh'))
        safe_send(chat_id, text, parse_mode='HTML', reply_markup=kb)
        safe_answer(call.id)
        return

    if data == 'admin_task_delete_all':
        c = get_cursor()
        c.execute('DELETE FROM tasks WHERE active = 1')
        db.commit()
        safe_send(chat_id, "🗑️ Все задания удалены.", reply_markup=admin_kb())
        safe_answer(call.id)
        return

    if data.startswith('admin_task_delete_'):
        try:
            task_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректное задание.", alert=True)
            return
        c = get_cursor()
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        db.commit()
        safe_send(chat_id, f"✅ Задание #{task_id} удалено.", reply_markup=admin_kb())
        safe_answer(call.id)
        return

    if data.startswith('admin_task_edit_'):
        try:
            task_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректное задание.", alert=True)
            return
        user_states[user_id] = {'state': 'admin_task_edit_reward', 'task_id': task_id}
        safe_send(
            chat_id,
            f"✏️ Введите новую награду (в CRF) для задания #{task_id}:",
            reply_markup=cancel_kb(),
        )
        safe_answer(call.id)
        return

    safe_answer(call.id)


@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def handle_states(m):
    user_id = m.from_user.id
    if user_id not in user_states:
        return
    state = user_states[user_id].get('state')

    if m.text == '❌ Отменить':
        del user_states[user_id]
        safe_send(m.chat.id, '✅ Отменено.', reply_markup=main_menu(user_id))
        return

    if state == 'verification':
        code = m.text.strip()
        saved_code = user_states[user_id].get('code')
        saved_time = user_states[user_id].get('time')
        if saved_time and datetime.now() - saved_time > timedelta(minutes=10):
            del user_states[user_id]
            safe_send(m.chat.id, '❌ Код истёк. Начните заново.', reply_markup=main_menu(user_id))
        elif code == saved_code:
            update_field(user_id, 'is_verified', 1)
            del user_states[user_id]
            safe_send(m.chat.id, '✅ ВЕРИФИКАЦИЯ ПРОЙДЕНА!', reply_markup=main_menu(user_id))
        else:
            safe_send(m.chat.id, '❌ Неверный код. Попробуйте снова.', reply_markup=cancel_kb())

    elif state == 'exchange_rub_to_crf':
        try:
            amount_rub = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount_rub <= 0:
            safe_send(m.chat.id, "❌ Сумма должна быть > 0")
            return
        if get_balance_rub(user_id) < amount_rub:
            safe_send(m.chat.id, f"❌ Недостаточно ₽. У вас {get_balance_rub(user_id):.2f}")
            return
        rate = get_crf_rate()
        commission = amount_rub * (CONFIG.get('exchange_commission_percent', 10.0) / 100.0)
        amount_crf = (amount_rub - commission) / rate
        add_transaction_rub(
            user_id,
            -amount_rub,
            'exchange_rub_to_crf',
            f'Обмен {amount_rub:.2f} ₽ на CRF (комиссия {commission:.2f} ₽)',
        )
        add_transaction_rub(0, commission, 'exchange_commission_rub', f'Комиссия за обмен ₽→CRF от {user_id}')
        c = get_cursor()
        c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_exchange_rub"', (commission,))
        db.commit()
        add_transaction_crf(
            user_id,
            amount_crf,
            'exchange_rub_to_crf',
            f'Обмен {amount_rub:.2f} ₽ на CRF по курсу {rate:.4f}',
        )
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Обмен выполнен! Вы получили {amount_crf:.2f} CRF за "
                f"{amount_rub:.2f} ₽ (комиссия {commission:.2f} ₽)"
            ),
            reply_markup=exchange_kb(),
        )

    elif state == 'exchange_crf_to_rub':
        try:
            amount_crf = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount_crf <= 0:
            safe_send(m.chat.id, "❌ Сумма должна быть > 0")
            return
        if get_balance_crf(user_id) < amount_crf:
            safe_send(m.chat.id, f"❌ Недостаточно CRF. У вас {get_balance_crf(user_id):.2f}")
            return
        rate = get_crf_rate()
        commission = amount_crf * (CONFIG.get('exchange_commission_percent', 10.0) / 100.0)
        amount_rub = (amount_crf - commission) * rate
        add_transaction_crf(
            user_id,
            -amount_crf,
            'exchange_crf_to_rub',
            f'Обмен {amount_crf:.2f} CRF на ₽ (комиссия {commission:.2f} CRF)',
        )
        add_transaction_crf(0, commission, 'exchange_commission_crf', f'Комиссия за обмен CRF→₽ от {user_id}')
        c = get_cursor()
        c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_exchange_crf"', (commission,))
        db.commit()
        add_transaction_rub(
            user_id,
            amount_rub,
            'exchange_crf_to_rub',
            f'Обмен {amount_crf:.2f} CRF на ₽ по курсу {rate:.4f}',
        )
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Обмен выполнен! Вы получили {amount_rub:.2f} ₽ за "
                f"{amount_crf:.2f} CRF (комиссия {commission:.2f} CRF)"
            ),
            reply_markup=exchange_kb(),
        )

    elif state == 'withdraw_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        balance = user_states[user_id].get('balance', 0)
        if amount <= 0 or amount > balance:
            safe_send(m.chat.id, f"❌ Сумма должна быть от 0 до {balance:.2f}")
            return
        level, _ = get_user_level(user_id)
        if level < CONFIG.get('withdraw_min_level', 2):
            del user_states[user_id]
            safe_send(
                m.chat.id,
                f"❌ Вывод доступен с {CONFIG.get('withdraw_min_level', 2)} уровня.",
                reply_markup=main_menu(user_id),
            )
            return
        fee_percent = get_level_bonuses(level)['withdraw_fee']
        fee = amount * (fee_percent / 100.0)
        net = amount - fee
        if net <= 0:
            safe_send(m.chat.id, f"❌ Сумма слишком мала после комиссии ({fee_percent:.1f}%).")
            return
        user_states[user_id] = {'state': 'withdraw_wallet', 'amount': amount, 'net': net, 'fee': fee}
        safe_send(
            m.chat.id,
            f"💳 Введите номер карты или кошелёк Юмани для вывода {net:.2f} ₽ (комиссия {fee:.2f} ₽):",
            reply_markup=cancel_kb(),
        )

    elif state == 'withdraw_wallet':
        wallet = m.text.strip()
        if not wallet:
            safe_send(m.chat.id, "❌ Введите реквизиты.")
            return
        amount = user_states[user_id].get('amount')
        net = user_states[user_id].get('net')
        add_transaction_rub(user_id, -amount, 'withdraw_hold', f'Заявка на вывод {amount:.2f} ₽')
        c = get_cursor()
        c.execute('INSERT INTO withdraws (chatId, amount, wallet) VALUES (?, ?, ?)', (user_id, net, wallet))
        db.commit()
        for admin in ADMIN_IDS:
            try:
                bot.send_message(
                    admin,
                    f"📛 Новая заявка на вывод от {user_id}: {net:.2f} ₽ на {wallet}",
                    parse_mode='HTML',
                )
            except Exception:
                pass
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Заявка на вывод {net:.2f} ₽ создана. Ожидайте обработки.",
            reply_markup=cabinet_kb(),
        )

    elif state == 'deposit_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount <= 0:
            safe_send(m.chat.id, "❌ Сумма должна быть > 0")
            return
        c = get_cursor()
        c.execute('INSERT INTO deposits (chatId, amount) VALUES (?, ?)', (user_id, amount))
        db.commit()
        deposit_id = c.lastrowid
        for admin in ADMIN_IDS:
            try:
                bot.send_message(
                    admin,
                    f"📥 Новая заявка на пополнение #{deposit_id} от {user_id}: {amount:.2f} ₽",
                    parse_mode='HTML',
                )
            except Exception:
                pass
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Заявка на пополнение #{deposit_id} на {amount:.2f} ₽ создана. Ожидайте подтверждения администратором.",
            reply_markup=cabinet_kb(),
        )

    elif state == 'support':
        msg_text = m.text
        c = get_cursor()
        c.execute('INSERT INTO tickets (user_id, message, status) VALUES (?, ?, "open")', (user_id, msg_text))
        db.commit()
        ticket_id = c.lastrowid
        for admin in ADMIN_IDS:
            try:
                bot.send_message(
                    admin,
                    (
                        f"🆘 Новый тикет #{ticket_id} от {user_id}:\n{msg_text}\n\n"
                        f"Ответьте командой: /reply_ticket {ticket_id} <текст>"
                    ),
                    parse_mode='HTML',
                )
            except Exception:
                pass
        del user_states[user_id]
        safe_send(m.chat.id, '✅ Сообщение отправлено администраторам.', reply_markup=main_menu(user_id))

    elif state == 'duel_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, '❌ Введите число.')
            return
        if amount < 1:
            safe_send(m.chat.id, '❌ Минимальная ставка 1 ₽')
            return
        mode = user_states[user_id].get('mode', 'classic')
        success, msg = create_duel(user_id, amount, mode)
        del user_states[user_id]
        safe_send(m.chat.id, msg, reply_markup=duel_kb())

    elif state == 'promo_mailing_users':
        try:
            count = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите целое число.")
            return
        c = get_cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total = c.fetchone()[0] or 0
        if count < 0 or count > total:
            safe_send(m.chat.id, f"❌ Количество должно быть от 0 до {total}")
            return
        price = (
            count * CONFIG.get('promo_mailing_price_per_user', 0.3)
            if count > 0
            else total * CONFIG.get('promo_mailing_price_per_user', 0.3)
        )
        if get_balance_rub(user_id) < price:
            del user_states[user_id]
            safe_send(m.chat.id, f"❌ Недостаточно средств. Нужно {price:.2f} ₽. Пополните баланс.")
            return
        user_states[user_id] = {'state': 'promo_mailing_msg', 'count': count, 'price': price}
        safe_send(
            m.chat.id,
            (
                "📨 Отправьте сообщение для рассылки (текст или перешлите сообщение).\n"
                f"Будет отправлено {count if count > 0 else total} пользователям. "
                f"Стоимость: {price:.2f} ₽."
            ),
            reply_markup=cancel_kb(),
        )

    elif state == 'promo_mailing_msg':
        count = user_states[user_id].get('count', 0)
        price = user_states[user_id].get('price', 0)
        add_transaction_rub(user_id, -price, 'promo_mailing', f'Рассылка сообщения {count} пользователям')
        add_transaction_rub(0, price, 'promo_mailing_income', f'Доход от рассылки от {user_id}')
        c = get_cursor()
        c.execute(
            '''
            INSERT INTO promotions (user_id, type, message, price, status)
            VALUES (?, 'mailing', ?, ?, 'active')
            ''',
            (user_id, m.text, price),
        )
        db.commit()
        threading.Thread(target=send_mailing, args=(m.text, count, m.chat.id, user_id)).start()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Рассылка запущена! Стоимость: {price:.2f} ₽. "
                f"Сообщение будет доставлено {count if count > 0 else 'всем'} пользователям."
            ),
        )

    elif state == 'promo_channel_channel':
        channel = clean_channel(m.text)
        if not channel:
            safe_send(m.chat.id, "❌ Некорректный username")
            return
        user_states[user_id] = {'state': 'promo_channel_hours', 'channel': channel}
        safe_send(m.chat.id, "⏱️ Введите количество часов рекламы (цена 50₽/час):", reply_markup=cancel_kb())

    elif state == 'promo_channel_hours':
        try:
            hours = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите целое число часов.")
            return
        if hours <= 0:
            safe_send(m.chat.id, "❌ Количество часов должно быть > 0")
            return
        price = hours * CONFIG.get('promo_channel_price_per_hour', 50.0)
        channel = user_states[user_id].get('channel')
        if get_balance_rub(user_id) < price:
            del user_states[user_id]
            safe_send(m.chat.id, f"❌ Недостаточно средств. Нужно {price:.2f} ₽.")
            return
        add_transaction_rub(user_id, -price, 'promo_channel', f'Реклама канала @{channel} на {hours} ч')
        add_transaction_rub(0, price, 'promo_channel_income', f'Доход от рекламы канала @{channel}')
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=hours)
        c = get_cursor()
        c.execute(
            '''
            INSERT INTO promotions (user_id, type, channel, price, hours, start_time, end_time, status)
            VALUES (?, 'channel', ?, ?, ?, ?, ?, 'active')
            ''',
            (user_id, channel, price, hours, start_time.isoformat(), end_time.isoformat()),
        )
        db.commit()
        c.execute('INSERT OR IGNORE INTO promo_subscriptions (user_id, channel) VALUES (?, ?)', (user_id, channel))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Реклама канала @{channel} запущена на {hours} часов! "
                f"Стоимость: {price:.2f} ₽. Канал добавлен в обязательные подписки для всех пользователей."
            ),
        )

    elif state == 'invest_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount < CONFIG.get('investment_min', 10):
            safe_send(m.chat.id, f"❌ Минимальная сумма: {CONFIG.get('investment_min', 10)} CRF")
            return
        days = user_states[user_id].get('days', 1)
        success, msg = create_investment_crf(user_id, amount, days)
        del user_states[user_id]
        safe_send(m.chat.id, msg, reply_markup=invest_kb())

    elif state == 'stake_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount < 1:
            safe_send(m.chat.id, "❌ Минимальная сумма: 1 CRF")
            return
        days = user_states[user_id].get('days', 7)
        success, msg = stake_crf(user_id, amount, days)
        del user_states[user_id]
        safe_send(m.chat.id, msg, reply_markup=invest_kb())

    elif state == 'admin_replenish_update':
        parts = [part.strip() for part in m.text.split(',')]
        if len(parts) < 3:
            safe_send(m.chat.id, "❌ Неверный формат. Используйте: карта, держатель, банк")
            return
        c = get_cursor()
        c.execute('UPDATE settings SET value = ? WHERE key = "replenish_card"', (parts[0],))
        c.execute('UPDATE settings SET value = ? WHERE key = "replenish_holder"', (parts[1],))
        c.execute('UPDATE settings SET value = ? WHERE key = "replenish_bank"', (parts[2],))
        db.commit()
        del user_states[user_id]
        safe_send(m.chat.id, "✅ Реквизиты пополнения обновлены!", reply_markup=admin_kb())

    elif state == 'admin_task_edit_reward':
        try:
            new_reward = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if new_reward <= 0:
            safe_send(m.chat.id, "❌ Награда должна быть > 0")
            return
        task_id = user_states[user_id].get('task_id')
        c = get_cursor()
        c.execute('UPDATE tasks SET reward = ? WHERE id = ?', (new_reward, task_id))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Награда для задания #{task_id} изменена на {new_reward:.2f} CRF",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_balance_rub':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        add_transaction_rub(target, amount, 'admin_balance', 'Админ изменил баланс ₽')
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Баланс ₽ пользователя {target} изменён на {amount:.2f}",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_balance_crf':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        add_transaction_crf(target, amount, 'admin_balance_crf', 'Админ изменил баланс CRF')
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Баланс CRF пользователя {target} изменён на {amount:.2f}",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_crf_rate':
        try:
            new_rate = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if new_rate <= 0:
            safe_send(m.chat.id, "❌ Курс должен быть > 0")
            return
        update_crf_rate(new_rate)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Курс CRF обновлён: 1 CRF = {new_rate:.4f} ₽",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_transactions':
        try:
            target = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID")
            return
        user = get_user(target)
        if not user:
            del user_states[user_id]
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (target,))
        rub = c.fetchall()
        c.execute('SELECT * FROM crf_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (target,))
        crf = c.fetchall()
        text = f"📊 Транзакции пользователя {target}\n\n"
        text += "💰 ₽:\n"
        for row in rub:
            sign = '+' if row['amount'] > 0 else ''
            text += f"{row['type']}: {sign}{row['amount']:.2f} ₽ – {row['description']}\n"
        text += "\n💎 CRF:\n"
        for row in crf:
            sign = '+' if row['amount'] > 0 else ''
            text += f"{row['type']}: {sign}{row['amount']:.2f} CRF – {row['description']}\n"
        del user_states[user_id]
        safe_send(m.chat.id, text, parse_mode='HTML')

    elif state == 'admin_give_level':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <уровень>")
            return
        try:
            target = int(parts[0])
            level = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if level < 1:
            safe_send(m.chat.id, "❌ Уровень должен быть >= 1")
            return
        update_field(target, 'level', level)
        update_field(target, 'exp', 0)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Уровень пользователя {target} установлен на {level}, опыт сброшен",
            reply_markup=main_menu(user_id),
        )
        safe_send(target, f"👑 Администратор установил ваш уровень: {level}")

    elif state == 'admin_change_refs':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <реф. уровень>")
            return
        try:
            target = int(parts[0])
            ref_level = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if ref_level < 1 or ref_level > 3:
            safe_send(m.chat.id, "❌ Реф. уровень должен быть от 1 до 3")
            return
        update_field(target, 'ref_level', ref_level)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Реф. уровень пользователя {target} установлен на {ref_level}",
            reply_markup=main_menu(user_id),
        )
        safe_send(target, f"👑 Администратор изменил ваш реферальный уровень: {ref_level}")

    elif state == 'admin_seasons_create_name':
        name = m.text.strip()
        if not name:
            safe_send(m.chat.id, "❌ Название не может быть пустым.")
            return
        user_states[user_id] = {'state': 'admin_seasons_create_prize', 'name': name}
        safe_send(m.chat.id, "💰 Введите призовой фонд сезона (в ₽):", reply_markup=cancel_kb())

    elif state == 'admin_seasons_create_prize':
        try:
            prize = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if prize < 0:
            safe_send(m.chat.id, "❌ Сумма не может быть отрицательной.")
            return
        name = user_states[user_id].get('name')
        season_id = create_season(name, prize)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Сезон '{name}' создан! ID: {season_id}",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_task_subscribe_channel':
        channel = clean_channel(m.text)
        if not channel:
            safe_send(m.chat.id, "❌ Некорректный username")
            return
        user_states[user_id] = {'state': 'admin_task_subscribe_reward', 'channel': channel}
        safe_send(m.chat.id, f"💰 Введите награду в CRF за подписку на @{channel}:", reply_markup=cancel_kb())

    elif state == 'admin_task_subscribe_reward':
        try:
            reward = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if reward <= 0:
            safe_send(m.chat.id, "❌ Награда должна быть > 0")
            return
        channel = user_states[user_id].get('channel')
        c = get_cursor()
        c.execute('INSERT INTO tasks (channel, reward) VALUES (?, ?)', (channel, reward))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Задание создано! Подписка на @{channel} даёт {reward:.2f} CRF",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_broadcast':
        try:
            count = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        user_states[user_id] = {'state': 'admin_broadcast_msg', 'count': count}
        safe_send(m.chat.id, "📨 Отправьте сообщение:")

    elif state == 'admin_broadcast_msg':
        count = user_states[user_id].get('count', 0)
        c = get_cursor()
        if count == 0:
            c.execute('SELECT chatId FROM users')
        else:
            c.execute('SELECT chatId FROM users ORDER BY RANDOM() LIMIT ?', (count,))
        rows = c.fetchall()
        failed = 0
        for row in rows:
            try:
                try:
                    target_chat = row['chatId']
                except Exception:
                    target_chat = row[0]
                bot.copy_message(target_chat, m.chat.id, m.message_id)
                time.sleep(0.05)
            except Exception:
                failed += 1
        del user_states[user_id]
        safe_send(m.chat.id, f"✅ Рассылка завершена! Не доставлено: {failed}", reply_markup=main_menu(user_id))

    elif state == 'mod_ban':
        try:
            target = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'ban', target, '{}'),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на блокировку {target} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_unban':
        try:
            target = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'unban', target, '{}'),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на разблокировку {target} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_balance_rub':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'balance_rub', target, json.dumps({'amount': amount})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на изменение баланса ₽ {target} на {amount:.2f} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_balance_crf':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'balance_crf', target, json.dumps({'amount': amount})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на изменение баланса CRF {target} на {amount:.2f} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_level':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <уровень>")
            return
        try:
            target = int(parts[0])
            level = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if level < 1:
            safe_send(m.chat.id, "❌ Уровень должен быть >= 1")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'change_level', target, json.dumps({'level': level})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на изменение уровня {target} на {level} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_vip':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <дни>")
            return
        try:
            target = int(parts[0])
            days = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if days < 1:
            safe_send(m.chat.id, "❌ Дней должно быть >= 1")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'give_vip', target, json.dumps({'days': days})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на выдачу VIP на {days} дней пользователю {target} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_cancel_withdraw':
        try:
            withdraw_id = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID заявки")
            return
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE id = ? AND status = 0', (withdraw_id,))
        row = c.fetchone()
        if not row:
            safe_send(m.chat.id, "❌ Заявка не найдена или уже обработана")
            return
        add_transaction_rub(row['chatId'], row['amount'], 'withdraw_cancel', f'Отмена заявки модератором #{withdraw_id}')
        c.execute('UPDATE withdraws SET status = 2 WHERE id = ?', (withdraw_id,))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Заявка #{withdraw_id} отменена, средства возвращены.",
            reply_markup=main_menu(user_id),
        )

    else:
        del user_states[user_id]
        safe_send(m.chat.id, '✅ Отменено.', reply_markup=main_menu(user_id))


@bot.message_handler(func=lambda m: m.text == '💸 Вывести ₽')
def withdraw_btn(m):
    user_id = m.from_user.id
    balance = get_balance_rub(user_id)
    level, _ = get_user_level(user_id)
    fee_percent = get_level_bonuses(level)['withdraw_fee']
    user_states[user_id] = {'state': 'withdraw_amount', 'balance': balance}
    safe_send(
        m.chat.id,
        (
            f"💸 Ваш баланс: {balance:.2f} ₽\n"
            f"Комиссия вывода для вашего уровня: {fee_percent:.1f}%\n"
            "Введите сумму для вывода:"
        ),
        reply_markup=cancel_kb(),
    )


@bot.message_handler(func=lambda m: m.text == '💳 Пополнить')
def deposit_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute("SELECT value FROM settings WHERE key = 'replenish_card'")
    card = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key = 'replenish_holder'")
    holder = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key = 'replenish_bank'")
    bank = c.fetchone()
    text = (
        "💳 ПОПОЛНЕНИЕ БАЛАНСА\n\n"
        f"Карта: {card['value'] if card else CONFIG.get('replenish_card', 'Не указано')}\n"
        f"Держатель: {holder['value'] if holder else CONFIG.get('replenish_holder', 'Не указано')}\n"
        f"Банк: {bank['value'] if bank else CONFIG.get('replenish_bank', 'Не указано')}\n\n"
        "После оплаты введите сумму пополнения в ₽:"
    )
    user_states[user_id] = {'state': 'deposit_amount'}
    safe_send(m.chat.id, text, reply_markup=cancel_kb())


@bot.message_handler(func=lambda m: m.text == '📊 История')
def cabinet_history_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute('SELECT * FROM withdraws WHERE chatId = ? ORDER BY created_at DESC LIMIT 10', (user_id,))
    withdraws = c.fetchall()
    c.execute('SELECT * FROM deposits WHERE chatId = ? ORDER BY created_at DESC LIMIT 10', (user_id,))
    deposits = c.fetchall()
    status_map = {0: '⏳ В обработке', 1: '✅ Подтверждено', 2: '❌ Отклонено'}
    text = "📊 ИСТОРИЯ ЗАЯВОК\n\n"
    if deposits:
        text += "📥 Пополнения:\n"
        for row in deposits:
            text += (
                f"#{row['id']} • {row['amount']:.2f} ₽ • "
                f"{status_map.get(row['status'], '❓')} • {row['created_at']}\n"
            )
        text += "\n"
    if withdraws:
        text += "📛 Выводы:\n"
        for row in withdraws:
            text += (
                f"#{row['id']} • {row['amount']:.2f} ₽ • "
                f"{status_map.get(row['status'], '❓')} • {row['created_at']}\n"
            )
        text += "\n"
    if not deposits and not withdraws:
        text += "Нет заявок."
    safe_send(m.chat.id, text, reply_markup=cabinet_kb())


@bot.message_handler(func=lambda m: m.text == '📋 Задания')
def tasks_btn(m):
    user_id = m.from_user.id
    tasks = get_daily_tasks(user_id)
    if not tasks:
        safe_send(m.chat.id, "📭 Сегодня заданий нет.", reply_markup=main_menu(user_id))
        return
    text = "📋 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n"
    kb = InlineKeyboardMarkup()
    for task in tasks:
        if task['completed'] and task['claimed']:
            status = "✅"
        elif task['completed'] and not task['claimed']:
            status = "🔄 Готово!"
        else:
            status = f"🔄 {task['progress']}/{task['target']}"
        text += (
            f"{status} {task['text']}\n"
            f"Награда: +{task['reward_money']:.2f} CRF, +{task['reward_exp']} опыта\n\n"
        )
        if task['completed'] and not task['claimed']:
            kb.add(
                InlineKeyboardButton(
                    f'🎁 Забрать награду #{task["id"]}',
                    callback_data=f'claim_task_{task["id"]}',
                )
            )
    safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=kb if kb.keyboard else None)


@bot.message_handler(func=lambda m: m.text == '🎁 Бонус')
def bonus_btn(m):
    user_id = m.from_user.id
    today = datetime.now().date().isoformat()
    last = get_field(user_id, 'lastDailyBonus', '')
    if last == today:
        safe_send(m.chat.id, "🎁 Вы уже получали бонус сегодня. Приходите завтра!")
        return
    level, _ = get_user_level(user_id)
    bonus_max = get_level_bonuses(level)['bonus_max_crf']
    bonus = round(random.uniform(CONFIG.get('bonus_min_crf', 0.1), bonus_max), 2)
    add_transaction_crf(user_id, bonus, 'daily_bonus', f'Ежедневный бонус (уровень {level})')
    add_exp(user_id, CONFIG.get('exp_per_bonus', 5))
    update_field(user_id, 'lastDailyBonus', today)
    if is_vip(user_id):
        add_transaction_crf(user_id, bonus, 'vip_bonus_double', 'Удвоение VIP бонуса')
        bonus *= 2
    safe_send(
        m.chat.id,
        f"🎁 Вы получили ежедневный бонус: {bonus:.2f} CRF\n+{CONFIG.get('exp_per_bonus', 5)} опыта",
        parse_mode='HTML',
    )


@bot.message_handler(func=lambda m: m.text == '🎲 Колесо удачи')
def wheel_btn(m):
    user_id = m.from_user.id
    today = datetime.now().date().isoformat()
    last = get_field(user_id, 'lastSpin', '')
    if last == today:
        safe_send(m.chat.id, "🎲 Вы уже крутили колесо сегодня. Приходите завтра!")
        return
    level, _ = get_user_level(user_id)
    spin_max = get_level_bonuses(level)['spin_max_crf']
    reward = random.choice(CONFIG.get('spin_rewards_crf', [0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0]))
    reward = min(reward, spin_max)
    add_transaction_crf(user_id, reward, 'spin_win', 'Колесо удачи (выигрыш CRF)')
    add_exp(user_id, CONFIG.get('exp_per_spin', 3))
    update_field(user_id, 'lastSpin', today)
    safe_send(
        m.chat.id,
        f"🎲 Колесо удачи!\n\nВы выиграли {reward:.2f} CRF!\n+{CONFIG.get('exp_per_spin', 3)} опыта",
        parse_mode='HTML',
    )


if __name__ == '__main__':
    bot.infinity_polling(timeout=60)
