import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from typing import List

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================
# CONFIGURATION - Edit these or use environment variables
# ============================================

# Your bot token from @BotFather
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8348691282:AAECeReqHgMbJ2g_En-pRM-ZSoMGSiW2EHE')

# Your private group where files will be forwarded (negative ID)
TARGET_GROUP_ID = int(os.environ.get('TARGET_GROUP_ID', -1003332800094))

# List of groups to monitor (negative IDs)
MONITORED_GROUP_IDS = [
    int(x.strip()) for x in os.environ.get('MONITORED_GROUP_IDS', '-1003794947014,-1002554500064').split(',')
    if x.strip()
]

# Optional: Only allow specific users to upload (comma-separated user IDs)
ALLOWED_USERS = [
    int(x.strip()) for x in os.environ.get('ALLOWED_USERS', '').split(',')
    if x.strip()
]

# File size limit in bytes (default: 10MB)
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 10 * 1024 * 1024))

# Allowed file extensions (comma-separated)
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', '.txt,.log,.csv,.json,.xml,.yaml,.ini,.cfg')

# ============================================
# BOT SETUP
# ============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MultiGroupFileMonitor:
    def __init__(self):
        if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError("Please set BOT_TOKEN environment variable")
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.stats = {
            'total_forwarded': 0,
            'today_forwarded': 0,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'groups_monitored': len(MONITORED_GROUP_IDS)
        }
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("groups", self.groups_command))
        
        # Document handler - monitors all groups
        self.application.add_handler(
            MessageHandler(
                filters.Document.ALL,
                self.handle_document
            )
        )
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message"""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            f"📁 <b>Multi-Group File Monitor Bot</b>\n\n"
            f"🔍 Monitoring <b>{len(MONITORED_GROUP_IDS)}</b> groups\n"
            f"📤 Forwarding to: <code>{TARGET_GROUP_ID}</code>\n\n"
            f"📄 <b>Supported files:</b> {ALLOWED_EXTENSIONS}\n"
            f"📊 <b>Max size:</b> {MAX_FILE_SIZE // (1024*1024)}MB\n\n"
            f"Commands:\n"
            f"/start - Show this message\n"
            f"/help - Show help\n"
            f"/stats - Show bot statistics\n"
            f"/groups - List monitored groups",
            parse_mode='HTML'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message"""
        await update.message.reply_text(
            "🤖 <b>Bot Help</b>\n\n"
            "This bot monitors multiple Telegram groups for text files "
            "and automatically forwards them to your private group.\n\n"
            "<b>How it works:</b>\n"
            "1️⃣ User drops a .txt file in any monitored group\n"
            "2️⃣ Bot instantly forwards it to your private group\n"
            "3️⃣ Works even if original message is deleted\n"
            "4️⃣ All metadata is preserved\n\n"
            "<b>Features:</b>\n"
            f"✅ Monitors {len(MONITORED_GROUP_IDS)} groups\n"
            f"✅ Supports {ALLOWED_EXTENSIONS} files\n"
            f"✅ Forwarded files are permanently saved\n"
            f"✅ Auto-detects file type\n"
            f"✅ Shows uploader info\n"
            f"✅ Statistics tracking\n\n"
            "Just drop any supported file in a monitored group!",
            parse_mode='HTML'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send bot statistics"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.stats['date'] != today:
            self.stats['today_forwarded'] = 0
            self.stats['date'] = today
        
        await update.message.reply_text(
            f"📊 <b>Bot Statistics</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📁 Total forwarded: <b>{self.stats['total_forwarded']}</b>\n"
            f"📅 Today's forwards: <b>{self.stats['today_forwarded']}</b>\n"
            f"👥 Groups monitored: <b>{self.stats['groups_monitored']}</b>\n"
            f"📤 Target group: <code>{TARGET_GROUP_ID}</code>\n"
            f"⏰ Uptime: <i>Since last restart</i>\n"
            f"━━━━━━━━━━━━━━━━━━",
            parse_mode='HTML'
        )
    
    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List monitored groups"""
        groups_list = "\n".join([f"• <code>{gid}</code>" for gid in MONITORED_GROUP_IDS])
        
        await update.message.reply_text(
            f"👥 <b>Monitored Groups</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{groups_list}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Total: <b>{len(MONITORED_GROUP_IDS)}</b> groups",
            parse_mode='HTML'
        )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document files from monitored groups"""
        try:
            # Check if this is from a monitored group
            chat_id = update.effective_chat.id
            if chat_id not in MONITORED_GROUP_IDS:
                # Not from a monitored group - silently ignore
                return
            
            document = update.message.document
            file_name = document.file_name or 'unknown.txt'
            
            # Check file extension
            file_ext = os.path.splitext(file_name)[1].lower()
            allowed_extensions = [ext.strip().lower() for ext in ALLOWED_EXTENSIONS.split(',')]
            
            if file_ext not in allowed_extensions:
                logger.info(f"Ignored non-supported file: {file_name} from {chat_id}")
                return
            
            # Check file size
            if document.file_size > MAX_FILE_SIZE:
                await update.message.reply_text(
                    f"❌ File <b>{file_name}</b> is too large!\n"
                    f"Max size: {MAX_FILE_SIZE // (1024*1024)}MB",
                    parse_mode='HTML'
                )
                return
            
            # Check user authorization
            user_id = update.effective_user.id
            if ALLOWED_USERS and user_id not in ALLOWED_USERS:
                logger.info(f"Unauthorized user {user_id} tried to upload in {chat_id}")
                return
            
            # Get file info
            file_id = document.file_id
            file_size = document.file_size
            user = update.effective_user
            chat = update.effective_chat
            
            # Forward to target group with details
            caption = (
                f"📄 <b>File Forwarded</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📁 File: <code>{file_name}</code>\n"
                f"👤 Uploaded by: {user.first_name}\n"
                f"🆔 User ID: <code>{user_id}</code>\n"
                f"📊 Size: {file_size:,} bytes\n"
                f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🏷️ From group: <code>{chat_id}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>✅ File saved - Original may be deleted</i>"
            )
            
            # Send the file to target group
            await context.bot.send_document(
                chat_id=TARGET_GROUP_ID,
                document=file_id,
                caption=caption,
                parse_mode='HTML'
            )
            
            # Send confirmation to the user
            try:
                await update.message.reply_text(
                    f"✅ <b>{file_name}</b> forwarded to private group!",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not send confirmation: {e}")
            
            # Update statistics
            self.stats['total_forwarded'] += 1
            today = datetime.now().strftime('%Y-%m-%d')
            if self.stats['date'] != today:
                self.stats['today_forwarded'] = 1
                self.stats['date'] = today
            else:
                self.stats['today_forwarded'] += 1
            
            logger.info(f"Forwarded {file_name} from {chat_id} by {user.first_name}")
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            try:
                await update.message.reply_text("❌ Error processing file. Please try again.")
            except:
                pass
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again later."
                )
        except:
            pass
    
    def run(self):
        """Start the bot"""
        print("=" * 50)
        print("🤖 Multi-Group File Monitor Bot")
        print("=" * 50)
        print(f"📁 Monitoring {len(MONITORED_GROUP_IDS)} groups:")
        for gid in MONITORED_GROUP_IDS:
            print(f"   • {gid}")
        print(f"📤 Forwarding to: {TARGET_GROUP_ID}")
        print(f"📄 Supported extensions: {ALLOWED_EXTENSIONS}")
        print(f"📊 Max file size: {MAX_FILE_SIZE // (1024*1024)}MB")
        print("=" * 50)
        print("🟢 Bot is running... Press Ctrl+C to stop")
        print("=" * 50)
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        bot = MultiGroupFileMonitor()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise
