import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - Replace with your values
BOT_TOKEN = "8348691282:AAECsE1tTVn7QRzIOjBZsRtTIAvDr922ENY"
TARGET_GROUP_ID = -1003875102153  # Your private group ID (negative for groups)
MONITORED_GROUP_ID = -1003794947014,-1002554500064  # Group to monitor for files
ALLOWED_USERS = []  # Leave empty to allow all, or add user IDs

class FileMonitorBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(
                filters.Document.ALL & filters.Chat(chat_id=MONITORED_GROUP_ID),
                self.handle_document
            )
        )
        
        # Handle deleted messages (requires proper setup)
        # Note: Telegram doesn't directly notify about deletions
        # We'll implement a workaround
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when /start is issued."""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            f"I'm a file monitoring bot. I monitor group {MONITORED_GROUP_ID} "
            f"and forward all text files to group {TARGET_GROUP_ID}.\n\n"
            f"Commands:\n"
            f"/start - Show this message\n"
            f"/help - Show help\n"
            f"/stats - Show bot statistics"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a help message."""
        await update.message.reply_text(
            "🤖 Bot Help\n\n"
            "This bot monitors a specific group for text files and forwards "
            "them to another group.\n\n"
            "Features:\n"
            "✅ Auto-detects .txt files\n"
            "✅ Forwards files instantly\n"
            "✅ Works even if original is deleted\n"
            "✅ Preserves file information\n\n"
            "Just drop any .txt file in the monitored group!"
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send bot statistics."""
        stats = context.bot_data.get('stats', {'total': 0, 'today': 0})
        today = datetime.now().strftime("%Y-%m-%d")
        await update.message.reply_text(
            f"📊 Bot Statistics\n\n"
            f"Total files forwarded: {stats.get('total', 0)}\n"
            f"Today's forwards: {stats.get('today', 0)}\n"
            f"Monitored group: {MONITORED_GROUP_ID}\n"
            f"Target group: {TARGET_GROUP_ID}"
        )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text file documents."""
        try:
            document = update.message.document
            
            # Check if it's a text file
            if not document.file_name.endswith('.txt'):
                return
            
            # Check if user is allowed (if list is not empty)
            if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
                logger.info(f"User {update.effective_user.id} not allowed")
                return
            
            # Get file info
            file_name = document.file_name
            file_id = document.file_id
            file_size = document.file_size
            user = update.effective_user
            chat = update.effective_chat
            
            # Log the file
            logger.info(f"Text file detected: {file_name} from {user.first_name}")
            
            # Download file content (optional - if you want to read content)
            # file = await context.bot.get_file(file_id)
            # file_content = await file.download_as_bytearray()
            
            # Forward to target group with custom caption
            caption = (
                f"📄 <b>Text File Forwarded</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📁 File: <code>{file_name}</code>\n"
                f"👤 Uploaded by: {user.first_name}\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"📊 Size: {file_size} bytes\n"
                f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🏷️ Group: {chat.title or 'Private'}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>Original message may be deleted, but file is saved!</i>"
            )
            
            # Forward the document
            await context.bot.send_document(
                chat_id=TARGET_GROUP_ID,
                document=file_id,
                caption=caption,
                parse_mode='HTML'
            )
            
            # Send confirmation back to the user (optional)
            try:
                await update.message.reply_text(
                    f"✅ File <b>{file_name}</b> forwarded to the private group!",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not send confirmation: {e}")
            
            # Update statistics
            stats = context.bot_data.get('stats', {'total': 0, 'today': 0})
            stats['total'] += 1
            today = datetime.now().strftime("%Y-%m-%d")
            if stats.get('date') != today:
                stats['today'] = 1
                stats['date'] = today
            else:
                stats['today'] += 1
            context.bot_data['stats'] = stats
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text("❌ Error processing file. Please try again.")
    
    async def handle_deleted_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deleted messages (workaround)."""
        # Note: Telegram doesn't directly provide deleted message events
        # This is a placeholder for potential future implementation
        # You would need to track message IDs and check periodically
        pass
    
    def run(self):
        """Start the bot."""
        print("🤖 Bot is starting...")
        print(f"Monitoring group: {MONITORED_GROUP_ID}")
        print(f"Forwarding to group: {TARGET_GROUP_ID}")
        print("Press Ctrl+C to stop")
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Additional feature: Track deleted messages
class DeletedMessageTracker:
    """Track messages to detect deletions."""
    
    def __init__(self):
        self.messages = {}  # {message_id: (file_id, file_name, user_id)}
    
    def add_message(self, message_id, file_id, file_name, user_id):
        self.messages[message_id] = (file_id, file_name, user_id)
    
    def remove_message(self, message_id):
        if message_id in self.messages:
            return self.messages.pop(message_id)
        return None
    
    def check_deleted(self, current_message_ids):
        """Check which messages were deleted."""
        deleted = []
        for msg_id in list(self.messages.keys()):
            if msg_id not in current_message_ids:
                deleted.append((msg_id, self.messages[msg_id]))
        return deleted

# Main execution
if __name__ == '__main__':
    # Create and run the bot
    bot = FileMonitorBot(BOT_TOKEN)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
