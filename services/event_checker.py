import asyncio
import logging
from datetime import datetime, time, timedelta
from config import MOSCOW_TZ
from database.events_db import get_all_events, get_greeting_status, set_greeting_status, clear_old_greeting_statuses, get_greeting_time, get_event_chats, get_user_chats, get_chat_display_info, set_event_last_check_time
from services.date_utils import get_days_until

logger = logging.getLogger(__name__)

async def check_and_send_greetings(bot):
    """
    Проверяет события и отправляет поздравления если:
    1. Событие происходит сегодня (для периодических событий)
    2. Сейчас после указанного времени для каждого события (по умолчанию 9 утра)
    3. Еще не поздравляли с этим событием сегодня
    
    Возвращает список событий, которые были проверены и обработаны
    """
    now = datetime.now(MOSCOW_TZ)
    current_time = now.time()
    current_date_str = now.strftime("%d.%m")
    current_datetime_str = now.strftime("%d.%m %H:%M")
    
    logger.info(f"Начинаю проверку событий на {current_date_str} в {current_time}")
    
    events = await get_all_events()
    today_events = []
    checked_event_ids = []
    
    for event in events:
        date_str = event.get('date_str', '')
        recurrence = event.get('recurrence', 'нет') or 'нет'
        user_id = event.get('user_id', '')
        event_id = str(event.get('_id', ''))
        
        # Получаем время отправки поздравления для этого события
        greeting_time_str = event.get('greeting_time', '09:00')
        try:
            greeting_hour, greeting_minute = map(int, greeting_time_str.split(':'))
            greeting_time = time(hour=greeting_hour, minute=greeting_minute)
        except:
            greeting_time = time(hour=9, minute=0)
        
        # Проверяем, является ли событие "сегодняшним"
        days_info = get_days_until(date_str, recurrence)
        
        if days_info == "сегодня!":
            # Проверяем, наступило ли время отправки
            if current_time < greeting_time:
                logger.info(f"Событие {event.get('description')} еще не наступило время отправки ({greeting_time_str})")
                continue
            
            # Проверяем, поздравляли ли уже с этим событием сегодня
            already_greeted = await get_greeting_status(user_id, event_id, current_date_str)
            
            if not already_greeted:
                today_events.append({
                    'event': event,
                    'user_id': user_id,
                    'event_id': event_id
                })
                checked_event_ids.append((event_id, current_datetime_str))
                logger.info(f"Найдено событие для поздравления: {event.get('description')} ({date_str}, {recurrence})")
            else:
                logger.info(f"Событие уже поздравлено сегодня: {event.get('description')}")
        else:
            # Событие не сегодня, но всё равно проверяем - возможно нужно обновить время проверки
            # Не сохраняем время проверки для событий не сегодня
            pass
    
    # Отправляем поздравления
    for item in today_events:
        event = item['event']
        user_id = item['user_id']
        event_id = item['event_id']
        
        try:
            description = event.get('description', 'Событие')
            date_str = event.get('date_str', '')
            recurrence = event.get('recurrence', 'нет') or 'нет'
            
            rec_text_map = {
                'yearly': 'Ежегодное',
                'monthly': 'Ежемесячное',
                'weekly': 'Еженедельное',
                'нет': '',
                None: ''
            }
            rec_text = rec_text_map.get(recurrence, '')
            
            greeting_text = f"🎉 <b>Событие сегодня!</b>\n\n"
            greeting_text += f"{description}\n"
            if rec_text:
                greeting_text += f"({rec_text} событие)\n"
            greeting_text += f"\nДата: {date_str}"
            
            # Получаем список чатов для этого события
            event_chats = await get_event_chats(event_id)
            
            # Определяем куда отправлять уведомления
            chat_ids_to_send = []
            if event_chats:
                # Если есть выбранные чаты, отправляем в них
                chat_ids_to_send = event_chats
            else:
                # Если чаты не выбраны, отправляем только пользователю
                chat_ids_to_send = [user_id]
            
            # Отправляем уведомления во все выбранные чаты
            sent_count = 0
            for chat_id in chat_ids_to_send:
                try:
                    # Проверяем, является ли chat_id числом (ID чата) или строкой (имя пользователя)
                    # Если это ID чата, используем его напрямую
                    # Если это имя пользователя, нужно получить реальный ID из БД
                    target_chat_id = None
                    
                    # Пытаемся преобразовать в int - если получится, это ID чата
                    try:
                        target_chat_id = int(chat_id)
                    except (ValueError, TypeError):
                        # Это не число, значит это может быть username или другой идентификатор
                        # В этом случае ищем чат в БД по chat_id
                        user_chats = await get_user_chats(int(user_id) if user_id.isdigit() else user_id)
                        for chat in user_chats:
                            if str(chat.get('chat_id', '')) == chat_id:
                                target_chat_id = int(chat_id) if chat_id.isdigit() else chat_id
                                break
                        
                        if target_chat_id is None:
                            # Не нашли чат, пробуем использовать как есть
                            target_chat_id = chat_id
                    
                    # Если target_chat_id всё ещё строка и не начинается с @, пытаемся преобразовать
                    if isinstance(target_chat_id, str) and not target_chat_id.startswith('@'):
                        try:
                            target_chat_id = int(target_chat_id)
                        except (ValueError, TypeError):
                            pass
                    
                    await bot.send_message(
                        chat_id=target_chat_id,
                        text=greeting_text,
                        parse_mode="HTML"
                    )
                    sent_count += 1
                except Exception as chat_error:
                    logger.warning(f"Не удалось отправить уведомление в чат {chat_id}: {chat_error}")
            
            # Отмечаем что поздравление отправлено
            await set_greeting_status(user_id, event_id, current_date_str)
            logger.info(f"Поздравление отправлено в {sent_count} чат(ов) для события {event_id}")
            
        except Exception as e:
            error_msg = str(e)
            # Проверяем, является ли ошибкой то, что бот не может начать диалог
            if "bot can't initiate conversation" in error_msg or "Forbidden" in error_msg:
                logger.warning(f"Не удалось отправить поздравление пользователю {user_id}: бот не может начать диалог. Пользователь должен первым написать боту.")
                # Всё равно отмечаем как поздравлённое, чтобы не пытаться снова
                try:
                    await set_greeting_status(user_id, event_id, current_date_str)
                except:
                    pass
            else:
                logger.error(f"Ошибка при отправке поздравления пользователю {user_id}: {e}")
            # Логируем ошибку но не прерываем обработку других событий
    
    # Сохраняем время проверки только для тех событий, которые были проверены сегодня
    for event_id, check_time in checked_event_ids:
        await set_event_last_check_time(event_id, check_time)
    
    # Очищаем старые записи о поздравлениях
    if today_events:
        user_ids = set(item['user_id'] for item in today_events)
        for uid in user_ids:
            await clear_old_greeting_statuses(uid, current_date_str)
    
    logger.info(f"Проверка событий завершена. Найдено и обработано {len(today_events)} событий.")
    return len(today_events)

async def check_events_loop(bot):
    """
    Фоновый цикл проверки событий.
    Проверяет события каждую минуту и отправляет поздравления только когда:
    1. Наступило время поздравления для события
    2. Событие происходит сегодня
    3. Еще не поздравляли с этим событием сегодня
    """
    logger.info("Запуск цикла проверки событий...")
    
    while True:
        try:
            await check_and_send_greetings(bot)
        except Exception as e:
            logger.error(f"Ошибка в цикле проверки событий: {e}")
        
        # Проверяем каждую минуту
        await asyncio.sleep(60)
