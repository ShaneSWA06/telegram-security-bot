import logging
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
from telegram.constants import ChatMemberStatus
import os
import json
from datetime import datetime
import pytz

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
        self.group_configs = {}  # Store group-specific configurations
        self.config_file = 'group_configs.json'
        self.load_group_configs()
        self.setup_handlers()
    
    def load_group_configs(self):
        """Load group configurations from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.group_configs = json.load(f)
                print(f"✅ Loaded configurations for {len(self.group_configs)} groups")
            else:
                print("📝 No existing config file found, starting fresh")
        except Exception as e:
            print(f"❌ Error loading configs: {e}")
            self.group_configs = {}
    
    def save_group_configs(self):
        """Save group configurations to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.group_configs, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved configurations for {len(self.group_configs)} groups")
        except Exception as e:
            print(f"❌ Error saving configs: {e}")
    
    def get_group_config(self, chat_id):
        """Get configuration for a specific group."""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.group_configs:
            # Default configuration
            self.group_configs[chat_id_str] = {
                'welcome_message': """
🎉 မင်္ဂလာပါ {user_name} 😊

💰 Smile Coin Selling by Pyae မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်! 
🤗 စိတ်ချစွာ၀ယ်ယူနိုင်ပါတယ်

👑 Admin - @PyaePPZ

🇲🇲 Myanmar Time: {myanmar_time}
                """.strip(),
                'goodbye_message': """
👋 {user_name} 
😢 List ထဲမှာမင်းရှိတယ်ဆိုတာသိလိုက်ရတဲ့အချိန်ကစပြီးကိုယ်ဟာသအား၀မ်းနည်းနေပါပြီ 
💔 ကောင်းရာဘ၀ကိုပိုင်ဆိုင်ရပါစေဗျာ

🇲🇲 Myanmar Time: {myanmar_time}

😊 ကောင်းမွန်ပါစေ! Take care! 🌈
                """.strip(),
                'group_name': 'Default Group'
            }
            self.save_group_configs()
        return self.group_configs[chat_id_str]
    
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("ban", self.ban_user))
        self.application.add_handler(CommandHandler("unban", self.unban_user))
        self.application.add_handler(CommandHandler("kick", self.kick_user))
        self.application.add_handler(CommandHandler("status", self.group_status))
        self.application.add_handler(CommandHandler("lookup", self.lookup_user))
        
        # New commands for group configuration
        self.application.add_handler(CommandHandler("setwelcome", self.set_welcome_message))
        self.application.add_handler(CommandHandler("setgoodbye", self.set_goodbye_message))
        self.application.add_handler(CommandHandler("setgroupname", self.set_group_name))
        self.application.add_handler(CommandHandler("showconfig", self.show_config))
        self.application.add_handler(CommandHandler("resetconfig", self.reset_config))
        
        # Chat member handler for tracking joins/leaves
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.CHAT_MEMBER))
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
        
        # Message handler to store user info
        from telegram.ext import MessageHandler, filters
        self.application.add_handler(MessageHandler(filters.ALL, self.store_user_info))
    
    async def set_welcome_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set custom welcome message for this group."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a welcome message.\n\n"
                "**Usage:** `/setwelcome Your custom message here`\n\n"
                "**Available placeholders:**\n"
                "• `{user_name}` - New member's name\n"
                "• `{myanmar_time}` - Current Myanmar time\n\n"
                "**Line breaks:**\n"
                "• Use `\\n` for new lines\n"
                "• Use `\\n\\n` for double spacing\n\n"
                "**Example:**\n"
                "`/setwelcome 🎉 Welcome {user_name}!\\n\\nTime: {myanmar_time}`",
                parse_mode='Markdown'
            )
            return
        
        chat_id = str(update.effective_chat.id)
        new_message = " ".join(context.args)
        
        # Convert \n to actual line breaks
        new_message = new_message.replace('\\n', '\n')
        
        config = self.get_group_config(chat_id)
        config['welcome_message'] = new_message
        self.save_group_configs()
        
        await update.message.reply_text(
            f"✅ **Welcome message updated!**\n\n"
            f"**Preview:**\n{new_message.format(user_name='[New Member]', myanmar_time=get_myanmar_time())}",
            parse_mode='Markdown'
        )
    
    async def set_goodbye_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set custom goodbye message for this group."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a goodbye message.\n\n"
                "**Usage:** `/setgoodbye Your custom message here`\n\n"
                "**Available placeholders:**\n"
                "• `{user_name}` - Leaving member's name\n"
                "• `{myanmar_time}` - Current Myanmar time\n\n"
                "**Line breaks:**\n"
                "• Use `\\n` for new lines\n"
                "• Use `\\n\\n` for double spacing\n\n"
                "**Example:**\n"
                "`/setgoodbye 👋 Goodbye {user_name}!\\n\\nTime: {myanmar_time}`",
                parse_mode='Markdown'
            )
            return
        
        chat_id = str(update.effective_chat.id)
        new_message = " ".join(context.args)
        
        # Convert \n to actual line breaks
        new_message = new_message.replace('\\n', '\n')
        
        config = self.get_group_config(chat_id)
        config['goodbye_message'] = new_message
        self.save_group_configs()
        
        await update.message.reply_text(
            f"✅ **Goodbye message updated!**\n\n"
            f"**Preview:**\n{new_message.format(user_name='[Leaving Member]', myanmar_time=get_myanmar_time())}",
            parse_mode='Markdown'
        )
    
    async def set_group_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set group name for identification."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a group name.\n\n"
                "**Usage:** `/setgroupname Your Group Name`",
                parse_mode='Markdown'
            )
            return
        
        chat_id = str(update.effective_chat.id)
        group_name = " ".join(context.args)
        
        config = self.get_group_config(chat_id)
        config['group_name'] = group_name
        self.save_group_configs()
        
        await update.message.reply_text(f"✅ **Group name set to:** {group_name}")
    
    async def show_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current group configuration."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        chat_id = str(update.effective_chat.id)
        config = self.get_group_config(chat_id)
        
        config_message = f"""
📋 **Current Group Configuration**

🏷️ **Group Name:** {config['group_name']}
🆔 **Chat ID:** `{chat_id}`

🎉 **Welcome Message:**
```
{config['welcome_message']}
```

👋 **Goodbye Message:**
```
{config['goodbye_message']}
```

📝 **Note:** Use placeholders `{{user_name}}` and `{{myanmar_time}}` in your messages.

🇲🇲 Myanmar Time: {get_myanmar_time()}
        """
        
        await update.message.reply_text(config_message, parse_mode='Markdown')
    
    async def reset_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset group configuration to default."""
        if not await self.is_admin(update, context):
            await update.message.reply_text("❌ Only group administrators can use this command.")
            return
        
        chat_id = str(update.effective_chat.id)
        
        # Remove existing config to trigger default creation
        if chat_id in self.group_configs:
            del self.group_configs[chat_id]
        
        # Get default config
        self.get_group_config(chat_id)
        
        await update.message.reply_text("✅ **Group configuration reset to default!**\n\nUse `/showconfig` to see current settings.")
    
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

**Group Configuration:**
• `/setwelcome` - Set custom welcome message
• `/setgoodbye` - Set custom goodbye message
• `/setgroupname` - Set group name
• `/showconfig` - Show current config
• `/resetconfig` - Reset to default

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
        config = self.get_group_config(str(update.effective_chat.id))
        
        help_text = f"""🔒 <b>Security Bot - {config['group_name']}</b>

🤖 <b>ဘာတွေလုပ်ပေးနိုင်လဲ:</b>
- အဖွဲ့ဝင်အသစ်တွေ ကြိုဆိုမယ်
- အဖွဲ့ဝင်တွေ နှုတ်ဆက်မယ်
- အဖွဲ့အချက်အလက်တွေ ပြပေးမယ်
- လုံခြုံရေး စောင့်ကြည့်ပေးမယ်

📋 <b>Available Commands:</b>
- /help - အကူအညီ ပြန်ပြမယ်
- /status - အဖွဲ့အချက်အလက် ကြည့်မယ်

⚙️ <b>Group Configuration (Admins only):</b>
- /setwelcome - Welcome message ပြောင်းမယ်
- /setgoodbye - Goodbye message ပြောင်းမယ်
- /showconfig - လက်ရှိ setting တွေကြည့်မယ်

💎 <b>Multi-Group Security Bot</b> မှ လုံခြုံရေးစောင့်ရှောက်ပါတယ်!

🙋‍♂️ မေးခွန်းရှိရင် admin တွေကို ဆက်သွယ်ပါ

👑 <b>Admins:</b>
- @PyaePPZ - Main Admin

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
                print(f"💾 Stored info for @{user.username} (ID: {user.id}) - {get_myanmar_time()}")
    
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
🕐 Myanmar Time: {get_myanmar_time()}
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
                print(f"🎯 Found @{username} in database - ID: {target_user_id}")
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
                print(f"✅ Successfully banned @{target_user.username} (ID: {target_user_id}) - {get_myanmar_time()}")
                
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to ban user: {str(e)}")
                print(f"❌ Ban failed: {e}")
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
            config = self.get_group_config(str(update.effective_chat.id))
            
            status_message = f"""
📊 **Group Status**
🏷️ Group: {chat.title}
🎯 Custom Name: {config['group_name']}
👥 Members: {member_count}
🆔 Chat ID: `{chat.id}`
🇲🇲 Myanmar Time: {get_myanmar_time()}

🔒 Security Bot: Active ✅
📝 Monitoring: Joins/Leaves ✅
👮 Admin Controls: Available ✅
⚙️ Custom Messages: Configured ✅
            """
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting group status: {str(e)}")
    
    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track when users join or leave the chat."""
        try:
            # Check if chat_member update exists
            if not update.chat_member:
                print("❌ No chat_member update found")
                return
                
            result = self.extract_status_change(update.chat_member)
            
            if result is None:
                print("❌ No status change detected")
                return
            
            was_member, is_member = result
            user = update.chat_member.new_chat_member.user
            chat = update.effective_chat
            
            # Skip if it's the bot itself
            bot_info = await context.bot.get_me()
            if user.id == bot_info.id:
                print("🤖 Skipping bot status change")
                return
            
            # Get group-specific configuration
            config = self.get_group_config(str(chat.id))
            
            # Debug logging with print
            print(f"👤 Status change detected: {user.full_name} - was_member: {was_member}, is_member: {is_member}")
            print(f"📊 Old status: {update.chat_member.old_chat_member.status}, New status: {update.chat_member.new_chat_member.status}")
            print(f"🏷️ Group: {config['group_name']} (ID: {chat.id})")
            
            # User joined
            if not was_member and is_member:
                print(f"✅ {user.full_name} JOINED - Sending welcome message...")
                
                # Format the welcome message with user info
                join_message = config['welcome_message'].format(
                    user_name=user.full_name,
                    myanmar_time=get_myanmar_time()
                )
                
                await context.bot.send_message(chat.id, join_message)
                print(f"✅ Welcome message sent for {user.full_name} in {config['group_name']} - {get_myanmar_time()}")
            
            # User left or was removed/banned
            elif was_member and not is_member:
                print(f"❌ {user.full_name} LEFT/REMOVED - Sending goodbye message...")
                
                # Check if user was kicked/banned vs left voluntarily
                new_status = update.chat_member.new_chat_member.status
                action_type = "left" if new_status == ChatMemberStatus.LEFT else "removed"
                
                # Format the goodbye message with user info
                leave_message = config['goodbye_message'].format(
                    user_name=user.full_name,
                    myanmar_time=get_myanmar_time()
                )
                
                await context.bot.send_message(chat.id, leave_message)
                print(f"✅ Goodbye message sent for {user.full_name} ({action_type}) in {config['group_name']} - {get_myanmar_time()}")
            else:
                print(f"🔄 Status change for {user.full_name} but no action needed (was: {was_member}, is: {is_member})")
                
        except Exception as e:
            print(f"🚨 ERROR in track_chats: {e}")
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
        print(f"🔒 Multi-Group Security Bot starting... - {get_myanmar_time()}")
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
