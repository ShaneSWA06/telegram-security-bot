import logging
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
from telegram.constants import ChatMemberStatus
import os
from datetime import datetime
import requests
import threading 
import time 

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_IDS = [1925310270, 7137261147]  # PyaePPZ and shaneswa admin IDs
ADMIN_USERNAMES = ["PyaePPZ", "shaneswa"]  # Admin usernames for reference

class SecurityBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("ban", self.ban_user))
        self.application.add_handler(CommandHandler("unban", self.unban_user))
        self.application.add_handler(CommandHandler("kick", self.kick_user))
        self.application.add_handler(CommandHandler("status", self.group_status))
        
        # Chat member handler for tracking joins/leaves
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.CHAT_MEMBER))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        welcome_message = """
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
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message."""
        help_text = """🔒 <b>Smile Coin Security Bot</b>

🤖 <b>ဘာတွေလုပ်ပေးနိုင်လဲ:</b>
- အဖွဲ့ဝင်အသစ်တွေ ကြိုဆိုမယ်
- အဖွဲ့ဝင်တွေ နှုတ်ဆက်မယ်
- အဖွဲ့အချက်အလက်တွေ ပြပေးမယ်
- လုံခြုံရေး စောင့်ကြည့်ပေးမယ်

📋 <b>Available Commands:</b>
- /help - အကူအညီ ပြန်ပြမယ်
- /status - အဖွဲ့အချက်အလက် ကြည့်မယ်

👑 <b>Admins:</b>
- @PyaePPZ - Main Admin
- @shaneswa - Co-Admin

💎 <b>Smile Coin by Pyae</b> မှ လုံခြုံရေးစောင့်ရှောက်ပါတယ်!

🙋‍♂️ မေးခွန်းရှိရင် admin တွေကို ဆက်သွယ်ပါ"""
        
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
            return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
    
   async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group."""
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
        # Parse arguments
        if not context.args:
            await update.message.reply_text("❌ Please specify a user to ban.\nUsage: `/ban @username` or `/ban user_id` or reply to a message with `/ban`", parse_mode='Markdown')
            return
        
        user_identifier = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
        
        # Check if it's a username (starts with @) or user ID (numeric)
        if user_identifier.startswith('@'):
            username = user_identifier[1:]  # Remove @ symbol
            try:
                # Get chat administrators to find user by username
                chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
                
                # Search through recent messages or use a different approach
                # Since we can't directly get user by username, we'll try to find them in recent chat members
                # This is a limitation of the Telegram Bot API
                
                # Alternative approach: Ask user to reply to the target user's message
                await update.message.reply_text(
                    f"❌ Cannot find user @{username}.\n"
                    "Please either:\n"
                    "• Reply to their message with `/ban`\n"
                    "• Use their user ID: `/ban 123456789`\n"
                    "• Forward their message and reply to it with `/ban`",
                    parse_mode='Markdown'
                )
                return
                
            except Exception as e:
                await update.message.reply_text(f"❌ Error searching for user @{username}: {str(e)}")
                return
                
        else:
            # Assume it's a user ID
            try:
                user_id = int(user_identifier)
                # Get user info by ID
                try:
                    chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                    target_user = chat_member.user
                except Exception:
                    # User might not be in the group, but we can still try to ban by ID
                    target_user = type('User', (), {
                        'id': user_id,
                        'full_name': f'User {user_id}',
                        'username': None
                    })()
                    
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID. Please provide a valid number.")
                return
    
    if target_user:
        # Check if trying to ban an admin
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, target_user.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                await update.message.reply_text("❌ Cannot ban a group administrator.")
                return
        except Exception:
            pass  # User might not be in group
        
        # Check if trying to ban self
        if target_user.id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot ban yourself!")
            return
            
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target_user.id)
            
            ban_message = f"""
🚫 **User Banned**
👤 User: {target_user.full_name} (@{target_user.username or 'No username'})
🆔 ID: `{target_user.id}`
👮 Banned by: {update.effective_user.full_name}"""

            if reason:
                ban_message += f"\n📝 Reason: {reason}"
            
            ban_message += f"\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await update.message.reply_text(ban_message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to ban user: {str(e)}")
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
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
        reason = "No reason provided"
        
        # Check if replying to a message
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            reason = " ".join(context.args) if context.args else "No reason provided"
        else:
            if not context.args:
                await update.message.reply_text("❌ Please specify a user to kick.\nUsage: `/kick @username` or reply to a message with `/kick`", parse_mode='Markdown')
                return
            
            try:
                user_id = int(context.args[0])
                # In a real implementation, you'd need to get user info
                reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
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
👮 Kicked by: {update.effective_user.full_name}
📝 Reason: {reason}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
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
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔒 Security Bot: Active ✅
📝 Monitoring: Joins/Leaves ✅
👮 Admin Controls: Available ✅
            """
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting group status: {str(e)}")
    
    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track when users join or leave the chat."""
        result = self.extract_status_change(update.chat_member)
        
        if result is None:
            return
        
        was_member, is_member = result
        user = update.chat_member.new_chat_member.user
        chat = update.effective_chat
        
        # User joined
        if not was_member and is_member:
            join_message = f"""
🎉 မင်္ကလာပါ {user.full_name} 😊

💰 Smile Coin Selling by Pyae မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်! 🤗

🌟 သင်ဟာ ကျွန်တော်တို့ရဲ့ အထူးမိသားစုဝင် ဖြစ်လာပါပြီ! 
💎 ဒီမှာ တကယ်လို့ Smile Coin အကြောင်း သိချင်ရင် လွတ်လပ်စွာ မေးမြန်းနိုင်ပါတယ်
📈 ကျွန်တော်တို့ အတူတူ အောင်မြင်ကြည်ညိုမှုရဲ့ ခရီးကို စတင်ကြပါစို့! 🚀

👤 အမည်: {user.full_name}
👤 Username: @{user.username or 'မရှိပါ'}
🆔 ID: `{user.id}`
⏰ အချိန်: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎊 ကြိုဆိုပါတယ်နော်! Welcome to our family! 🎊
            """
            await context.bot.send_message(chat.id, join_message, parse_mode='Markdown')
        
        # User left
        elif was_member and not is_member:
            leave_message = f"""
😔 နွေးနူးတယ်...

👋 {user.full_name} ကို နမ်းနေပါပြီ 😢

💔 Smile Coin Selling by Pyae မှ နှုတ်ဆက်ပါတယ်...
🙏 သင်နဲ့ အတူတူ ရှိခဲ့ရတာ ဝမ်းသာပါတယ်
🌟 နောင်တချိန်မှာ ပြန်လာခဲ့ပါဦးနော်
💝 သင့်အတွက် တံခါးကို အမြဲဖွင့်ထားပါမယ်

👤 အမည်: {user.full_name}
👤 Username: @{user.username or 'မရှိပါ'}
🆔 ID: `{user.id}`
⏰ အချိန်: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

😊 ကောင်းမွန်ပါစေ! Take care! 🌈
            """
            await context.bot.send_message(chat.id, leave_message, parse_mode='Markdown')
    
    def extract_status_change(self, chat_member_update):
        """Extract whether the 'old_chat_member' was a member and whether the 'new_chat_member' is a member."""
        status_change = chat_member_update.difference().get("status")
        old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))
        
        if status_change is None:
            return None
        
        old_status, new_status = status_change
        was_member = old_status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
        ] or (old_status == ChatMemberStatus.RESTRICTED and old_is_member is True)
        
        is_member = new_status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
        ] or (new_status == ChatMemberStatus.RESTRICTED and new_is_member is True)
        
        return was_member, is_member
    
    def run(self):
        """Start the bot."""
        print("🔒 Security Bot starting...")
        print("Bot is now running. Press Ctrl+C to stop.")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run the bot."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your bot token in the BOT_TOKEN variable!")
        print("Get your token from @BotFather on Telegram")
        return
    
    bot = SecurityBot()
    bot.run()

if __name__ == '__main__':
    main()
