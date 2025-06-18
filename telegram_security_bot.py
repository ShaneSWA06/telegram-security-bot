import logging
import os
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
from telegram.constants import ChatMemberStatus
from datetime import datetime
import pytz

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration - Use environment variables for security
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN environment variable not set!")
    exit(1)

ADMIN_USER_IDS = [1925310270]  # PyaePPZ and shaneswa admin IDs
ADMIN_USERNAMES = ["PyaePPZ"]  # Admin usernames for reference

# Myanmar timezone
MYANMAR_TZ = pytz.timezone('Asia/Yangon')

def get_myanmar_time():
    """Get current time in Myanmar timezone."""
    utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    myanmar_time = utc_now.astimezone(MYANMAR_TZ)
    return myanmar_time.strftime('%Y-%m-%d %H:%M:%S %Z')

def get_myanmar_time_short():
    """Get current time in Myanmar timezone (short format)."""
    utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    myanmar_time = utc_now.astimezone(MYANMAR_TZ)
    return myanmar_time.strftime('%H:%M:%S')

class SecurityBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.user_database = {}  # Store username -> user_info mapping
        self.setup_handlers()
    
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("ban", self.ban_user))
        self.application.add_handler(CommandHandler("unban", self.unban_user))
        self.application.add_handler(CommandHandler("kick", self.kick_user))
        self.application.add_handler(CommandHandler("status", self.group_status))
        self.application.add_handler(CommandHandler("lookup", self.lookup_user))
        
        # Chat member handler for tracking joins/leaves
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.CHAT_MEMBER))
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
        
        # Message handler to store user info
        from telegram.ext import MessageHandler, filters
        self.application.add_handler(MessageHandler(filters.ALL, self.store_user_info))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        welcome_message = f"""
🔒 **Security Bot Activated**

I'm now monitoring this group for member changes and providing admin controls.

**Available Commands:**
• `/ban @username` - Ban a user from the group
• `/unban @username` - Unban a user
• `/kick @username` - Kick a user (they can rejoin)
• `/status` - Show group statistics
• `/help` - Show this help message

**Auto-notifications:**
✅ User joins will be logged
❌ User leaves will be logged
🚫 Kicked/banned users will be logged

Only group admins can use moderation commands.

🕐 Myanmar Time: {get_myanmar_time_short()}
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message."""
        help_text = f"""🔒 <b>Smile Coin Security Bot</b>

🤖 <b>ဘာတွေလုပ်ပေးနိုင်လဲ:</b>
- အဖွဲ့ဝင်အသစ်တွေ ကြိုဆိုမယ်
- အဖွဲ့ဝင်တွေ နှုတ်ဆက်မယ်
- အဖွဲ့အချက်အလက်တွေ ပြပေးမယ်
- လုံခြုံရေး စောင့်ကြည့်ပေးမယ်

📋 <b>Available Commands:</b>
- /help - အကူအညီ ပြန်ပြမယ်
- /status - အဖွဲ့အချက်အလက် ကြည့်မယ်

💎 <b>Smile Coin by Pyae</b> မှ လုံခြုံရေးစောင့်ရှောက်ပါတယ်!

🙋‍♂️ မေးခွန်းရှိရင် admin တွေကို ဆက်သွယ်ပါ

👑 <b>Admins:</b>
- @PyaePPZ - Main Admin
- @shaneswa - Co-Admin

🇲🇲 Myanmar Time: {get_myanmar_time()}
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def is_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is admin of the group or in admin list."""
        user_id = update.effective_user.id
        username = update.effective_user.username
        chat_id = update.effective_chat.id
        
        # Check if user is in predefined admin list
        if user_id in ADMIN_USER_IDS or (username and username in ADMIN_USERNAMES):
            return True
        
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            # Fixed: Use OWNER instead of CREATOR for older versions
            admin_statuses = [ChatMemberStatus.ADMINISTRATOR]
            # Try both CREATOR and OWNER to be compatible with different versions
            try:
                admin_statuses.append(ChatMemberStatus.CREATOR)
            except AttributeError:
                pass
            try:
                admin_statuses.append(ChatMemberStatus.OWNER)
            except AttributeError:
                pass
            
            return member.status in admin_statuses
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
    
    async def store_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store user information from messages for later username-based actions."""
        if update.message and update.message.from_user:
            user = update.message.from_user
            if user.username:  # Only store if user has a username
                self.user_database[user.username.lower()] = {
                    'id': user.id,
                    'full_name': user.full_name,
                    'username': user.username,
                    'chat_id': update.effective_chat.id
                }
                logger.info(f"💾 Stored info for @{user.username} (ID: {user.id}) - {get_myanmar_time()}")
    
    async def lookup_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Look up a user's information by username."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please specify a username.\nUsage: `/lookup @username`", parse_mode='Markdown')
            return
        
        username = context.args[0].replace('@', '').lower()
        
        if username in self.user_database:
            user_info = self.user_database[username]
            lookup_message = f"""
👤 **User Found**
🏷️ Name: {user_info['full_name']}
👤 Username: @{user_info['username']}
🆔 ID: `{user_info['id']}`
📝 To ban: `/ban @{user_info['username']}`
🇲🇲 Myanmar Time: {get_myanmar_time()}
            """
            await update.message.reply_text(lookup_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ User @{username} not found in database.\nThey need to send a message first for me to store their info.")
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ban a user from the group."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        target_user = None
        target_user_id = None
        reason = None
        
        # Check if replying to a message
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
            reason = " ".join(context.args) if context.args else None
        else:
            # Parse arguments
            if not context.args:
                await update.message.reply_text("❌ Please specify a username to ban.\nUsage: `/ban @username` or reply to a message with `/ban`", parse_mode='Markdown')
                return
            
            username_arg = context.args[0]
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
            
            # Only accept usernames (must start with @)
            if not username_arg.startswith('@'):
                await update.message.reply_text("❌ Please provide a username starting with @\nUsage: `/ban @username`", parse_mode='Markdown')
                return
            
            # Remove @ symbol and convert to lowercase
            username = username_arg[1:].lower()
            
            # Check if trying to ban predefined admins by username
            if username in [admin.lower() for admin in ADMIN_USERNAMES]:
                await update.message.reply_text("❌ Cannot ban a bot administrator!")
                return
            
            # Look up user in database
            if username in self.user_database:
                user_info = self.user_database[username]
                target_user_id = user_info['id']
                # Create a user object for display
                target_user = type('User', (), {
                    'id': user_info['id'],
                    'full_name': user_info['full_name'],
                    'username': user_info['username']
                })()
                logger.info(f"🎯 Found @{username} in database - ID: {target_user_id}")
            else:
                await update.message.reply_text(
                    f"❌ Cannot find @{username} in my database.\n\n"
                    "**This user needs to:**\n"
                    "1. Send at least one message in this group\n"
                    "2. Then you can ban them with `/ban @{username}`\n\n"
                    "**Alternative:**\n"
                    "• Reply to their message with `/ban`\n"
                    "• Use `/lookup @{username}` to check if they're stored",
                    parse_mode='Markdown'
                )
                return
        
        if target_user_id:
            # Check if trying to ban an admin (including predefined admins)
            if target_user_id in ADMIN_USER_IDS:
                await update.message.reply_text("❌ Cannot ban a bot administrator!")
                return
            
            if target_user and target_user.username and target_user.username.lower() in [admin.lower() for admin in ADMIN_USERNAMES]:
                await update.message.reply_text("❌ Cannot ban a bot administrator!")
                return
            
            # Check if trying to ban self
            if target_user_id == update.effective_user.id:
                await update.message.reply_text("❌ You cannot ban yourself!")
                return
            
            # Check if trying to ban a group admin
            try:
                member = await context.bot.get_chat_member(update.effective_chat.id, target_user_id)
                admin_statuses = [ChatMemberStatus.ADMINISTRATOR]
                # Try both CREATOR and OWNER to be compatible with different versions
                try:
                    admin_statuses.append(ChatMemberStatus.CREATOR)
                except AttributeError:
                    pass
                try:
                    admin_statuses.append(ChatMemberStatus.OWNER)
                except AttributeError:
                    pass
                
                if member.status in admin_statuses:
                    await update.message.reply_text("❌ Cannot ban a group administrator.")
                    return
            except Exception:
                pass  # User might not be in group, continue with ban
            
            # Check if trying to ban the bot itself
            bot_info = await context.bot.get_me()
            if target_user_id == bot_info.id:
                await update.message.reply_text("❌ I cannot ban myself! 🤖")
                return
                
            try:
                await context.bot.ban_chat_member(update.effective_chat.id, target_user_id)
                
                ban_message = f"""
🚫 **User Banned**
👤 User: {target_user.full_name} (@{target_user.username or 'No username'})
🆔 ID: `{target_user_id}`
👮 Banned by: {update.effective_user.full_name}"""

                if reason:
                    ban_message += f"\n📝 Reason: {reason}"
                
                ban_message += f"\n🇲🇲 Myanmar Time: {get_myanmar_time()}"
                
                await update.message.reply_text(ban_message, parse_mode='Markdown')
                logger.info(f"✅ Successfully banned @{target_user.username} (ID: {target_user_id}) - {get_myanmar_time()}")
                
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to ban user: {str(e)}")
                logger.error(f"❌ Ban failed: {e}")
        else:
            await update.message.reply_text("❌ Could not identify the user to ban.")
    
    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unban a user from the group."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please specify a user ID to unban.\nUsage: `/unban 123456789`", parse_mode='Markdown')
            return
        
        try:
            user_id = int(context.args[0])
            await context.bot.unban_chat_member(update.effective_chat.id, user_id)
            
            unban_message = f"""
✅ **User Unbanned**
🆔 User ID: `{user_id}`
👮 Unbanned by: {update.effective_user.full_name}
🇲🇲 Myanmar Time: {get_myanmar_time()}
            """
            await update.message.reply_text(unban_message, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid user ID.")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to unban user: {str(e)}")
    
    async def kick_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kick a user from the group."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        target_user = None
        reason = None
        
        # Check if replying to a message
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            reason = " ".join(context.args) if context.args else None
        else:
            if not context.args:
                await update.message.reply_text("❌ Please specify a user to kick.\nUsage: `/kick user_id` or reply to a message with `/kick`", parse_mode='Markdown')
                return
            
            try:
                user_id = int(context.args[0])
                # Try to get user info
                try:
                    chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                    target_user = chat_member.user
                except Exception:
                    target_user = type('User', (), {
                        'id': user_id,
                        'full_name': f'User {user_id}',
                        'username': None
                    })()
                reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
            except ValueError:
                await update.message.reply_text("❌ Please provide a valid user ID or reply to a message.")
                return
        
        if target_user:
            try:
                # Kick user (ban then unban to allow rejoining)
                await context.bot.ban_chat_member(update.effective_chat.id, target_user.id)
                await context.bot.unban_chat_member(update.effective_chat.id, target_user.id)
                
                kick_message = f"""
👢 **User Kicked**
👤 User: {target_user.full_name} (@{target_user.username or 'No username'})
🆔 ID: `{target_user.id}`
👮 Kicked by: {update.effective_user.full_name}"""

                if reason:
                    kick_message += f"\n📝 Reason: {reason}"
                
                kick_message += f"\n🇲🇲 Myanmar Time: {get_myanmar_time()}"
                
                await update.message.reply_text(kick_message, parse_mode='Markdown')
                
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to kick user: {str(e)}")
    
    async def group_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show group statistics."""
        try:
            chat = await context.bot.get_chat(update.effective_chat.id)
            member_count = await context.bot.get_chat_member_count(update.effective_chat.id)
            
            status_message = f"""
📊 **Group Status**
🏷️ Group: {chat.title}
👥 Members: {member_count}
🆔 Chat ID: `{chat.id}`
🇲🇲 Myanmar Time: {get_myanmar_time()}

🔒 Security Bot: Active ✅
📝 Monitoring: Joins/Leaves ✅
👮 Admin Controls: Available ✅
            """
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting group status: {str(e)}")
    
    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track when users join or leave the chat."""
        try:
            # Check if chat_member update exists
            if not update.chat_member:
                logger.warning("❌ No chat_member update found")
                return
                
            result = self.extract_status_change(update.chat_member)
            
            if result is None:
                logger.warning("❌ No status change detected")
                return
            
            was_member, is_member = result
            user = update.chat_member.new_chat_member.user
            chat = update.effective_chat
            
            # Skip if it's the bot itself
            bot_info = await context.bot.get_me()
            if user.id == bot_info.id:
                logger.info("🤖 Skipping bot status change")
                return
            
            # Debug logging
            logger.info(f"👤 Status change detected: {user.full_name} - was_member: {was_member}, is_member: {is_member}")
            logger.info(f"📊 Old status: {update.chat_member.old_chat_member.status}, New status: {update.chat_member.new_chat_member.status}")
            
            # User joined
            if not was_member and is_member:
                logger.info(f"✅ {user.full_name} JOINED - Sending welcome message...")
                join_message = f"""
🎉 မင်္ဂလာပါ {user.full_name} 😊

💰 Smile Coin Selling by Pyae မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်! 
🤗 စိတ်ချစွာ၀ယ်ယူနိုင်ပါတယ်

👑 Admin - @PyaePPZ

🇲🇲 Myanmar Time: {get_myanmar_time()}
                """
                await context.bot.send_message(chat.id, join_message, parse_mode='Markdown')
                logger.info(f"✅ Welcome message sent for {user.full_name} - {get_myanmar_time()}")
            
            # User left or was removed/banned
            elif was_member and not is_member:
                new_status = update.chat_member.new_chat_member.status
                
                # Check if user was banned/kicked vs left voluntarily
                banned_statuses = []
                try:
                    banned_statuses.append(ChatMemberStatus.KICKED)
                except AttributeError:
                    pass
                try:
                    banned_statuses.append(ChatMemberStatus.BANNED)
                except AttributeError:
                    pass
                
                # Only send goodbye message if user left voluntarily, not if banned/kicked
                if new_status == ChatMemberStatus.LEFT:
                    logger.info(f"👋 {user.full_name} LEFT VOLUNTARILY - Sending goodbye message...")
                    leave_message = f"""
👋 {user.full_name} 
😢 List ထဲမှာမင်းရှိတယ်ဆိုတာသိလိုက်ရတဲ့အချိန်ကစပြီးကိုယ်ဟာသအား၀မ်းနည်းနေပါပြီ 
💔 ကောင်းရာဘ၀ကိုပိုင်ဆိုင်ရပါစေဗျာ

🇲🇲 Myanmar Time: {get_myanmar_time()}

😊 ကောင်းမွန်ပါစေ! Take care! 🌈
                    """
                    await context.bot.send_message(chat.id, leave_message, parse_mode='Markdown')
                    logger.info(f"✅ Goodbye message sent for {user.full_name} (left voluntarily) - {get_myanmar_time()}")
                elif new_status in banned_statuses:
                    logger.info(f"🚫 {user.full_name} was BANNED/KICKED by admin - No goodbye message sent")
                else:
                    logger.info(f"❌ {user.full_name} was REMOVED (status: {new_status}) - No goodbye message sent")
            else:
                logger.info(f"🔄 Status change for {user.full_name} but no action needed (was: {was_member}, is: {is_member})")
                
        except Exception as e:
            logger.error(f"🚨 ERROR in track_chats: {e}")
            import traceback
            traceback.print_exc()
    
    def extract_status_change(self, chat_member_update):
        """Extract whether the 'old_chat_member' was a member and whether the 'new_chat_member' is a member."""
        status_change = chat_member_update.difference().get("status")
        old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))
        
        if status_change is None:
            return None
        
        old_status, new_status = status_change
        
        # Create compatible admin status lists for both old and new versions
        admin_statuses = [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]
        
        # Try to add both CREATOR and OWNER for compatibility
        try:
            admin_statuses.append(ChatMemberStatus.CREATOR)
        except AttributeError:
            pass
        try:
            admin_statuses.append(ChatMemberStatus.OWNER)
        except AttributeError:
            pass
        
        # Check if was a member
        was_member = old_status in admin_statuses or (old_status == ChatMemberStatus.RESTRICTED and old_is_member is True)
        
        # Check if is currently a member
        is_member = new_status in admin_statuses or (new_status == ChatMemberStatus.RESTRICTED and new_is_member is True)
        
        # Handle kicked/banned status
        banned_statuses = []
        try:
            banned_statuses.append(ChatMemberStatus.KICKED)
        except AttributeError:
            pass
        try:
            banned_statuses.append(ChatMemberStatus.BANNED)
        except AttributeError:
            pass
        
        if new_status in banned_statuses:
            is_member = False
        
        return was_member, is_member
    
    def run(self):
        """Start the bot."""
        logger.info(f"🔒 Security Bot starting... - {get_myanmar_time()}")
        logger.info("Bot is now running. Press Ctrl+C to stop.")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run the bot."""
    if not BOT_TOKEN:
        logger.error("❌ Please set your BOT_TOKEN environment variable!")
        logger.error("Get your token from @BotFather on Telegram")
        return
    
    bot = SecurityBot()
    bot.run()

if __name__ == '__main__':
    main()
