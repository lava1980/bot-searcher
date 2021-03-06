import os

from telegram.error import BadRequest
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from config import *
from messages import *
from google_utils import get_list_of_rows, search
from utils import *






# Итого:

# TODO 5. Сделать так, чтобы список всех операторов открывался сразу по нажатию на квадратик.





# СДЕЛАЛ: 

# 1. Закрывать диалог (с обеих сторон) с юзером при одобрении доступа.
# 2. Дать админу тоже фичу пробивки.
# 3. Внести в меню операторов пользователя оператор add.
# 4. При пробивке без операторов показывать сообщение: "Для проверки ФИО..."

# 7. Удалить значит удалить полностью из списка. Если админ использует delete, то пусть пользователь удаляется из него.
# 6. Блокировка и поиск по ID.





def start(update, context):    
    user_id = update.message.from_user.id
    data = get_initial_data(update)
    write_initial_data_to_base(data)
    
    if user_id == TG_ADMIN_ID:
        update.message.reply_text(msg_start_admin, reply_markup=ReplyKeyboardRemove())
    else:
        update.message.reply_text(msg_start, reply_markup=ReplyKeyboardRemove())
    write_entry_to_base('conv_status', 'started', user_id)


def send_all_user_messages_to_admin(update, context):       
    text = update.message.text        
    user_id = update.message.from_user.id    

    if is_conv_closed(update, context):
        update.message.reply_text(msg_to_user_conv_closed)
        return

    if 'conv_started' not in context.user_data:
        context.user_data['conv_started'] = 'yes'
        context.bot.send_message(
            chat_id=TG_ADMIN_ID,
            text=text,
            reply_markup=get_start_conv_keyboard(update, context)
        )
    else:
        user_name = update.message.from_user.first_name
        text = f'<b>{user_name} (id {str(user_id)}) пишет:</b> {text}'
        context.bot.send_message(
            chat_id=TG_ADMIN_ID,
            text=text, 
            parse_mode=ParseMode.HTML
        )
    
    
        

def send_admin_message_to_user(update, context):   
    if 'target_user_id' in context.user_data:
        text = update.message.text    
        target_user_id = context.user_data['target_user_id']
        if is_conv_closed(update, context):
            update.message.reply_text(msg_to_admin_conv_closed)
            return

        context.bot.send_message(
            chat_id=target_user_id, 
            text=text
        )
    else:        
        update.message.reply_text(msg_to_admin_conv_closed)



def query_handler(update, context):
    query = update.callback_query    
    if 'start_conv' in query.data:
        save_target_user_data_to_context(update, context)
        target_user_id = context.user_data['target_user_id']        
        query.message.reply_text('Режим диалога включен. Теперь можно писать пользователю')


def send_invitation(update, context):
    user_id = update.message.from_user.id

    if user_id != TG_ADMIN_ID:
        update.message.reply_text(msg_access_amin_only)
        return

    try:
        target_user_id = context.user_data['target_user_id']
            
    except KeyError:
        update.message.reply_text('Пока не кому слать — команда работает только в режиме диалога с пользователем')
        return
    context.bot.send_message(
        chat_id=target_user_id,
        text=msg_send_invitation
    )


def user_request_add_to_bot(update, context):
    user_id = update.message.from_user.id
    if is_subscriber(user_id):
        update.message.reply_text(msg_already_subscribed)
    else:
        admin_notification(update, context)
        update.message.reply_text('Ваш запрос отправлен админу')


'''ОТКРЫТИЕ ДОСТУПА ЮЗЕРУ'''

def add_or_not_user_access(update, context):
    query = update.callback_query
    if 'yes' in query.data:
        save_target_user_data_to_context(update, context)
        write_entry_to_base('access', 'yes', context.user_data['target_user_id'])
        context.bot.send_message(
            chat_id=TG_ADMIN_ID, 
            # text=f'Пользователю {target_username} разрешён доступ к боту'
            text=f'Введите реальное имя пользователя или пропустите этот шаг, если имя уже есть',
            reply_markup=get_pass_inline_keyboard()
        )
        return '1'

    if 'no' in query.data:
        save_target_user_data_to_context(update, context)
        write_entry_to_base('access', 'no', context.user_data['target_user_id'])
        context.bot.send_message(
            chat_id=TG_ADMIN_ID, 
            text=f'Пользователю {context.user_data["target_user_id"]} запрещён доступ к боту'
        )
        return ConversationHandler.END
    

def get_real_name(update, context):
    real_name = update.message.text
    target_user_id = context.user_data['target_user_id']
    write_entry_to_base('real_name', real_name, target_user_id)
    update.message.reply_text(f'Пользователь {real_name} добавлен')

    context.bot.send_message(
        chat_id=target_user_id,
        text=msg_approved_start_message
    )
    close_conv(update, context)
    return ConversationHandler.END


def pass_get_real_name(update, context):
    target_user_id = context.user_data['target_user_id']
    if 'real_name' in context.user_data:
        real_name = context.user_data['real_name']
    else:
        real_name = get_data_cell('real_name', target_user_id)
    query = update.callback_query
    query.message.reply_text(f'Пользователь {real_name} добавлен')
    context.bot.send_message(
        chat_id=target_user_id,
        text=msg_approved_start_message
    )
    close_conv(update, context)
    return ConversationHandler.END


def admin_notification(update, context):
    user_name = update.message.from_user.username
    user_id = update.message.from_user.id

    name = get_kb_real_name(update, context)
    context.bot.send_message(
        chat_id=TG_ADMIN_ID, 
        text=f'Пользователь {name} (id {user_id}) хочет подписаться на бот. Одобрить?',
        reply_markup=get_inline_keyboard(update, context)
    )


'''ПОЛЬЗОВАТЕЛЬ ИЩЕТ В БАЗЕ '''

def user_search(update, context):
    user_id = update.message.from_user.id
    if is_subscriber(user_id) == True or user_id == TG_ADMIN_ID:
        update.message.reply_text('Введите ФИО для поиска в базе')
        return '1'

    else:
        update.message.reply_text(
            'Вы не подписаны. Чтобы подписаться, обратитесь к админу',
            reply_markup=get_reply_kb(user_id))
        return ConversationHandler.END
    

def send_search_result(update, context):
    all_list = get_list_of_rows(SPREADSHEET_URL)
    result_list = search(all_list, update.message.text)
    if len(result_list) == 0:
        update.message.reply_text(msg_no_result)
        return '1'    

    for result in result_list:
        text = msg_search_result(result)        
        update.message.reply_text(text)
    return ConversationHandler.END
    

'''БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ'''

def block_user_start(update, context):    
    user_id = update.message.from_user.id

    if user_id != TG_ADMIN_ID:
        update.message.reply_text(msg_access_amin_only)
        return ConversationHandler.END

    update.message.reply_text(
        msg_enter_user_real_name,
        reply_markup=get_reply_kb(user_id))
    return '1'


def send_matched_users(update, context):    
    user_id = update.message.from_user.id
    entry = update.message.text
    if entry.isdigit():
        block_user(update, context)
        return ConversationHandler.END
    
    msg = msg_searched_users_to_block(entry)

    if len(msg) == 0:
        update.message.reply_text(msg_delete_users_no_result)
        update.message.reply_text(msg_delete_users_no_result_2)
        return '1'

    else:
        update.message.reply_text(msg)
        update.message.reply_text(
            msg_user_id_to_delete,
            reply_markup=get_reply_kb(user_id))
        return '2'


def block_user(update, context):
    user_id = update.message.from_user.id
    target_user_id = update.message.text
    # write_entry_to_base('access', 'no', target_user_id)
    delete_string(target_user_id)
    update.message.reply_text(
        f'Пользователь с id {target_user_id} больше не имеет доступа к боту',
        reply_markup=get_reply_kb(user_id))
    return ConversationHandler.END


def cancel_block_user(update, context):
    update.message.reply_text('Вышли из режима блокировки пользователя')
    return ConversationHandler.END


def fallback_block_user(update, context):
    update.message.reply_text(msg_fallback_block_user)


def cancel_conv(update, context):
    update.message.reply_text('Вышли из текущего режима')
    return ConversationHandler.END


def help_message(update, context):
    user_id = update.message.from_user.id
    if user_id == TG_ADMIN_ID:
        update.message.reply_text(msg_help_admin)
    else:
        update.message.reply_text(msg_help_user)


def get_all_users(update, context):
    user_id = update.message.from_user.id
    if user_id != TG_ADMIN_ID:
        update.message.reply_text(msg_access_amin_only)
        return

    text, count = text_all_users()    
    if count < 20:
        update.message.reply_text(text)

    else:
        file_path = os.path.join(os.getcwd(), 'users.txt')
        write_users_to_file(file_path, text)
        context.bot.send_document(
            chat_id=update.message.chat_id, 
            document=open(file_path, 'rb')            
        )
        os.remove(file_path)
    

def user_add_in_blocklist(update, context):
    update.message.reply_text(msg_user_add_in_blocklist)




if __name__ == "__main__":
    pass
