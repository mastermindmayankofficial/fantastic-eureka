from __future__ import annotations

import os
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import ADMIN_IDS, BOT_TOKEN, DB_PATH
from app.db import (
    add_indexed_file,
    apply_referral,
    apply_successful_request_quota,
    apply_successful_search_quota,
    ensure_default_settings,
    ensure_user,
    get_all_chats,
    get_all_users,
    get_setting,
    get_template,
    get_user,
    init_db,
    is_admin_user,
    is_banned,
    is_owner,
    list_requests,
    list_templates,
    log_action,
    resolve_user_id,
    save_chat,
    save_request,
    save_template,
    search_indexed_files,
    set_banned,
    set_setting,
    set_user_role,
    build_admin_help_text,
    build_user_help_text,
    render_placeholders,
    seed_demo_templates,
    update_request_status,
)


SUPPORTED_MEDIA = (filters.PHOTO | filters.VIDEO | filters.DOCUMENT)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    ensure_user(user.id, user.username, user.first_name)
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user.id:
            apply_referral(referrer_id, user.id)
            await update.message.reply_text("Referral bonus applied! +10 search quota and +10 request quota for both users.")
    row = get_user(user.id)
    if row:
        conn = __import__('app.db', fromlist=['get_conn']).get_conn()
        conn.execute("UPDATE users SET started=1 WHERE user_id=?", (user.id,))
        conn.commit()
        conn.close()
    await update.message.reply_text(build_user_help_text())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_user_help_text())


async def adminhelp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    ensure_user(user.id, user.username, user.first_name)
    if not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    await update.message.reply_text(build_admin_help_text())


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    ensure_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        await update.message.reply_text("Your account is banned.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /search <keyword>")
        return
    query = " ".join(context.args)
    results = search_indexed_files(query)
    if not results:
        await update.message.reply_text("No matching files found.")
        return
    keyboard_rows = []
    for item in results[:10]:
        title = item.get("title") or item.get("caption") or f"File {item['id']}"
        keyboard_rows.append([InlineKeyboardButton(title, callback_data=f"search_file:{item['id']}")])
    markup = InlineKeyboardMarkup(keyboard_rows)
    await update.message.reply_text(f"Search results for: {query}", reply_markup=markup)


async def request_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    ensure_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        await update.message.reply_text("Your account is banned.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /request <title> <author>")
        return
    title = context.args[0]
    author = " ".join(context.args[1:])
    save_request(user.id, title, author)
    request_log_chat = get_setting("request_log_chat_id", "")
    if request_log_chat:
        try:
            await context.bot.send_message(
                chat_id=int(request_log_chat),
                text=f"New request\nTitle: {title}\nAuthor: {author}\nUser: @{user.username or user.id}",
            )
            apply_successful_request_quota(user.id)
            await update.message.reply_text("Request submitted successfully.")
        except Exception as exc:
            await update.message.reply_text(f"Request saved locally but could not be posted to the log chat: {exc}")
    else:
        await update.message.reply_text("Request saved locally. No request log chat configured.")
    log_action(user.id, "request", f"{title}|{author}")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    if not is_admin_user(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    conn = __import__('app.db', fromlist=['get_conn']).get_conn()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    banned_users = conn.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
    total_groups = conn.execute("SELECT COUNT(*) FROM chats WHERE chat_type IN ('group', 'supergroup')").fetchone()[0]
    total_channels = conn.execute("SELECT COUNT(*) FROM chats WHERE chat_type='channel'").fetchone()[0]
    total_ebooks = conn.execute("SELECT COUNT(*) FROM indexed_files").fetchone()[0]
    total_requests = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    pending_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0]
    completed_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status IN ('completed','done','approved')").fetchone()[0]
    conn.close()
    msg = (
        "Bot Stats\n"
        f"Groups: {total_groups}\n"
        f"Channels: {total_channels}\n"
        f"Users: {total_users}\n"
        f"Banned users: {banned_users}\n"
        f"Ebooks: {total_ebooks}\n"
        f"Requests: {total_requests}\n"
        f"Pending requests: {pending_requests}\n"
        f"Completed requests: {completed_requests}\n"
        f"Ping: N/A\n"
        f"Storage usage: N/A\n"
        f"Code size: N/A"
    )
    await update.message.reply_text(msg)
    log_action(user_id, "stats", "viewed")


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    if not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /ban <user_id or username>")
        return
    target = context.args[0]
    target_id = resolve_user_id(target)
    if not target_id:
        await update.message.reply_text("User not found.")
        return
    set_banned(target_id, True)
    conn = __import__('app.db', fromlist=['get_conn']).get_conn()
    conn.execute("UPDATE users SET role='banned', search_quota=0, request_quota=0 WHERE user_id=?", (target_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"User {target_id} has been banned.")
    log_action(user.id, "ban", f"target={target_id}")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    if not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /unban <user_id or username>")
        return
    target = context.args[0]
    target_id = resolve_user_id(target)
    if not target_id:
        await update.message.reply_text("User not found.")
        return
    set_banned(target_id, False)
    conn = __import__('app.db', fromlist=['get_conn']).get_conn()
    conn.execute("UPDATE users SET role='normal', search_quota=10, request_quota=10 WHERE user_id=?", (target_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"User {target_id} has been unbanned.")
    log_action(user.id, "unban", f"target={target_id}")


async def addvol_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addvol <user_id or username>")
        return
    target_id = resolve_user_id(context.args[0])
    if not target_id:
        await update.message.reply_text("User not found.")
        return
    set_user_role(target_id, "volunteer")
    await update.message.reply_text(f"Assigned volunteer role to user {target_id}")
    log_action(user.id, "addvol", f"target={target_id}")


async def addprom_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addprom <user_id or username>")
        return
    target_id = resolve_user_id(context.args[0])
    if not target_id:
        await update.message.reply_text("User not found.")
        return
    set_user_role(target_id, "promoter")
    await update.message.reply_text(f"Assigned promoter role to user {target_id}")
    log_action(user.id, "addprom", f"target={target_id}")


async def addmod_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addmod <user_id or username>")
        return
    target_id = resolve_user_id(context.args[0])
    if not target_id:
        await update.message.reply_text("User not found.")
        return
    set_user_role(target_id, "moderator")
    await update.message.reply_text(f"Assigned moderator role to user {target_id}")
    log_action(user.id, "addmod", f"target={target_id}")


async def addadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_owner(user.id):
        await update.message.reply_text("Access denied. Owner only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addadmin <user_id or username>")
        return
    target_id = resolve_user_id(context.args[0])
    if not target_id:
        await update.message.reply_text("User not found.")
        return
    set_user_role(target_id, "admin")
    await update.message.reply_text(f"Assigned admin role to user {target_id}")
    log_action(user.id, "addadmin", f"target={target_id}")


async def setconfig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setconfig <key> <value>")
        return
    key = context.args[0]
    value = " ".join(context.args[1:])
    set_setting(key, value)
    await update.message.reply_text(f"Updated setting '{key}' = '{value}'")
    log_action(user.id, "setconfig", f"{key}={value}")


async def getconfig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /getconfig <key>")
        return
    await update.message.reply_text(f"{context.args[0]} = {get_setting(context.args[0], 'NOT_SET')}")


async def reloadconfig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    ensure_default_settings()
    await update.message.reply_text("Configuration reloaded from database.")
    log_action(user.id, "reloadconfig", "reloaded")


async def edittext_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /edittext <template_name>")
        return
    template_name = context.args[0]
    context.user_data["pending_template_name"] = template_name
    context.user_data["pending_template_mode"] = "text"
    await update.message.reply_text(
        f"Send the new text for template '{template_name}'. You can use placeholders: {{date}}, {{time}}, {{bot_title}}, {{bot_username}}, {{chat_title}}"
    )


async def setmedia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setmedia <template_name>")
        return
    context.user_data["pending_media_template"] = context.args[0]
    await update.message.reply_text("Send media for this template (photo/video/document).")


async def removemedia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /removemedia <template_name>")
        return
    name = context.args[0]
    existing = get_template(name) or {"text": "", "media_type": "", "media_file_id": "", "buttons": []}
    save_template(name, existing.get("text", ""), "", "", existing.get("buttons", []))
    await update.message.reply_text(f"Media removed from template '{name}'")
    log_action(user.id, "removemedia", name)


async def addbutton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /addbutton <template_name> <label> <callback>")
        return
    name, label, callback = context.args
    existing = get_template(name) or {"text": "", "media_type": "", "media_file_id": "", "buttons": []}
    buttons = existing.get("buttons", [])
    buttons.append({"label": label, "callback": callback})
    save_template(name, existing.get("text", ""), existing.get("media_type", ""), existing.get("media_file_id", ""), buttons)
    await update.message.reply_text(f"Button added to template '{name}'.")
    log_action(user.id, "addbutton", f"{name}|{label}|{callback}")


async def removebutton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /removebutton <template_name> <index>")
        return
    name, idx = context.args
    try:
        index = int(idx)
    except ValueError:
        await update.message.reply_text("Index must be an integer.")
        return
    existing = get_template(name) or {"text": "", "media_type": "", "media_file_id": "", "buttons": []}
    buttons = existing.get("buttons", [])
    if index < 0 or index >= len(buttons):
        await update.message.reply_text("Index out of range.")
        return
    del buttons[index]
    save_template(name, existing.get("text", ""), existing.get("media_type", ""), existing.get("media_file_id", ""), buttons)
    await update.message.reply_text(f"Removed button index {index} from template '{name}'.")
    log_action(user.id, "removebutton", f"{name}|{index}")


async def listtemplates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    templates = list_templates()
    if not templates:
        await update.message.reply_text("No templates are configured yet.")
        return
    await update.message.reply_text("Templates:\n- " + "\n- ".join(templates))


async def showtemplate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /showtemplate <template_name>")
        return
    name = context.args[0]
    template = get_template(name)
    if template is None:
        await update.message.reply_text(f"Template '{name}' not found.")
        return
    msg = f"Template: {name}\n\nText:\n{template['text']}\n\nButtons:\n"
    if template.get("buttons"):
        for i, btn in enumerate(template["buttons"]):
            msg += f"{i}. {btn.get('label')} -> {btn.get('callback')}\n"
    else:
        msg += "None\n"
    await update.message.reply_text(msg)


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/broadcast user <user_id> <message>\n"
            "/broadcast group <group_id> <message>\n"
            "/broadcast channel <channel_id> <message>\n"
            "/broadcast all_users <message>\n"
            "/broadcast all_groups <message>\n"
            "/broadcast all_channels <message>\n"
            "/broadcast everyone <message>"
        )
        return

    target = context.args[0].lower()
    payload = " ".join(context.args[1:])
    if target == "everyone":
        await update.message.reply_text(f"High-impact broadcast confirmed. Use /broadcast_confirm everyone {payload}")
        return

    if target == "all_users":
        sent = 0
        failed = 0
        for entry in get_all_users():
            try:
                await context.bot.send_message(chat_id=entry["user_id"], text=payload)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"Broadcast to all users completed. Sent: {sent}, Failed: {failed}")
        log_action(user.id, "broadcast", f"all_users:{payload[:100]}")
        return

    if target == "all_groups":
        sent = 0
        failed = 0
        for entry in get_all_chats("group"):
            try:
                await context.bot.send_message(chat_id=entry["chat_id"], text=payload)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"Broadcast to all groups completed. Sent: {sent}, Failed: {failed}")
        log_action(user.id, "broadcast", f"all_groups:{payload[:100]}")
        return

    if target == "all_channels":
        sent = 0
        failed = 0
        for entry in get_all_chats("channel"):
            try:
                await context.bot.send_message(chat_id=entry["chat_id"], text=payload)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"Broadcast to all channels completed. Sent: {sent}, Failed: {failed}")
        log_action(user.id, "broadcast", f"all_channels:{payload[:100]}")
        return

    if target in {"user", "group", "channel"}:
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /broadcast user <user_id> <message>")
            return
        target_id = context.args[1]
        payload = " ".join(context.args[2:])
        try:
            await context.bot.send_message(chat_id=int(target_id), text=payload)
            await update.message.reply_text(f"Broadcast sent to {target} {target_id}")
            log_action(user.id, "broadcast", f"{target}:{target_id}:{payload[:100]}")
        except Exception as exc:
            await update.message.reply_text(f"Broadcast failed: {exc}")
        return

    await update.message.reply_text("Unsupported broadcast target.")


async def broadcast_confirm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /broadcast_confirm everyone <message>")
        return
    if context.args[0].lower() != "everyone":
        await update.message.reply_text("Only everyone confirmation is supported right now.")
        return
    payload = " ".join(context.args[1:])
    sent = 0
    failed = 0
    for entry in get_all_users():
        try:
            await context.bot.send_message(chat_id=entry["user_id"], text=payload)
            sent += 1
        except Exception:
            failed += 1
    for entry in get_all_chats("group"):
        try:
            await context.bot.send_message(chat_id=entry["chat_id"], text=payload)
            sent += 1
        except Exception:
            failed += 1
    for entry in get_all_chats("channel"):
        try:
            await context.bot.send_message(chat_id=entry["chat_id"], text=payload)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"Everyone broadcast complete. Sent: {sent}, Failed: {failed}")
    log_action(user.id, "broadcast_confirm", payload[:100])


async def handle_media_for_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "pending_media_template" not in context.user_data:
        return
    template_name = context.user_data.pop("pending_media_template")
    msg = update.message
    if msg.photo:
        file_id = msg.photo[-1].file_id
        media_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        media_type = "video"
    elif msg.document:
        file_id = msg.document.file_id
        media_type = "document"
    else:
        await msg.reply_text("Unsupported media type. Please send photo, video, or document.")
        return
    existing = get_template(template_name) or {"text": "", "media_type": "", "media_file_id": "", "buttons": []}
    save_template(template_name, existing.get("text", ""), media_type, file_id, existing.get("buttons", []))
    await msg.reply_text(f"Media saved for template '{template_name}'.")
    log_action(msg.from_user.id, "setmedia", f"{template_name}|{media_type}")


async def handle_text_for_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "pending_template_name" in context.user_data and context.user_data.get("pending_template_mode") == "text":
        name = context.user_data.pop("pending_template_name")
        context.user_data.pop("pending_template_mode")
        current = get_template(name) or {"text": "", "media_type": "", "media_file_id": "", "buttons": []}
        save_template(name, update.message.text, current.get("media_type", ""), current.get("media_file_id", ""), current.get("buttons", []))
        await update.message.reply_text(f"Template '{name}' updated successfully.")
        log_action(update.effective_user.id, "edittext", f"{name}|{update.message.text[:100]}")
        return


async def callback_search_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    if not data.startswith("search_file:"):
        return
    try:
        file_id = int(data.split(":", 1)[1])
    except ValueError:
        await query.edit_message_text("Invalid file ID.")
        return
    resource = __import__('app.db', fromlist=['get_indexed_file_by_id']).get_indexed_file_by_id(file_id)
    if not resource:
        await query.edit_message_text("File not found.")
        return
    user = update.effective_user
    if not user:
        return
    ensure_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        await query.edit_message_text("Your account is banned.")
        return
    if not get_user(user.id) or not get_user(user.id).get("started"):
        await query.edit_message_text("Please start the bot first to receive files.")
        return

    posting_channel = get_setting("posting_channel_id", "")
    if posting_channel:
        try:
            if resource.get("file_type") == "photo":
                await context.bot.send_photo(chat_id=int(posting_channel), photo=resource["file_id"], caption=resource.get("caption") or resource.get("title"))
            elif resource.get("file_type") == "video":
                await context.bot.send_video(chat_id=int(posting_channel), video=resource["file_id"], caption=resource.get("caption") or resource.get("title"))
            else:
                await context.bot.send_document(chat_id=int(posting_channel), document=resource["file_id"], caption=resource.get("caption") or resource.get("title"))
        except Exception:
            pass

    allow_dm = get_setting("allow_dm_delivery", "true").lower() == "true"
    if allow_dm:
        try:
            if resource.get("file_type") == "photo":
                await context.bot.send_photo(chat_id=user.id, photo=resource["file_id"], caption=resource.get("caption") or resource.get("title"))
            elif resource.get("file_type") == "video":
                await context.bot.send_video(chat_id=user.id, video=resource["file_id"], caption=resource.get("caption") or resource.get("title"))
            else:
                await context.bot.send_document(chat_id=user.id, document=resource["file_id"], caption=resource.get("caption") or resource.get("title"))
            apply_successful_search_quota(user.id)
            await query.edit_message_text("File delivered successfully.")
        except Exception as exc:
            await query.edit_message_text(f"Delivery failed: {exc}")
    else:
        await query.edit_message_text("File selected. DM delivery is disabled; posting channel is being used.")

    log_action(user.id, "search_result_click", f"resource_id={file_id}")


async def callback_help_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    await query.edit_message_text(build_user_help_text())


async def callback_generic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    if data == "help:main":
        await callback_help_main(update, context)
    elif data.startswith("search_file:"):
        await callback_search_file(update, context)
    else:
        await query.edit_message_text(f"Callback received: {data}")


async def handle_unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ignore unknown comments by default, but keep chat tracked
    user = update.effective_user
    if user:
        ensure_user(user.id, user.username, user.first_name)
    save_chat(update.effective_chat.id, update.effective_chat.type, update.effective_chat.title or "")


def main() -> None:
    init_db()
    ensure_default_settings()
    seed_demo_templates()

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing; set it in your environment or .env file.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("adminhelp", adminhelp_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("request", request_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("addvol", addvol_cmd))
    app.add_handler(CommandHandler("addprom", addprom_cmd))
    app.add_handler(CommandHandler("addmod", addmod_cmd))
    app.add_handler(CommandHandler("addadmin", addadmin_cmd))
    app.add_handler(CommandHandler("setconfig", setconfig_cmd))
    app.add_handler(CommandHandler("getconfig", getconfig_cmd))
    app.add_handler(CommandHandler("reloadconfig", reloadconfig_cmd))
    app.add_handler(CommandHandler("edittext", edittext_cmd))
    app.add_handler(CommandHandler("setmedia", setmedia_cmd))
    app.add_handler(CommandHandler("removemedia", removemedia_cmd))
    app.add_handler(CommandHandler("addbutton", addbutton_cmd))
    app.add_handler(CommandHandler("removebutton", removebutton_cmd))
    app.add_handler(CommandHandler("listtemplates", listtemplates_cmd))
    app.add_handler(CommandHandler("showtemplate", showtemplate_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("broadcast_confirm", broadcast_confirm_cmd))

    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.DOCUMENT, handle_media_for_template))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_template))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown_text))

    app.add_handler(CallbackQueryHandler(callback_search_file, pattern=r"^search_file:"))
    app.add_handler(CallbackQueryHandler(callback_help_main, pattern=r"^help:"))
    app.add_handler(CallbackQueryHandler(callback_generic))

    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
