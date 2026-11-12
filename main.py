# -*- coding: utf-8 -*-
import telebot
import ast
import subprocess
import os
import glob
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import hashlib
import logging
import signal
import threading
import re
import sys
import atexit
import socket
import uuid
from pathlib import Path
import requests
from dotenv import load_dotenv


load_dotenv()


_A1 = 5275    

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Digital World HOSTING BOT - FULLY AUTOMATED"

def run_flask():
    requested = int(os.environ.get("PORT", "8080"))
    managed_platform = any(os.getenv(name) for name in ("RENDER", "DYNO", "RAILWAY_ENVIRONMENT"))

    # Managed platforms require their exact assigned PORT. Never fall back there.
    if managed_platform:
        logger.info("Managed hosting detected; starting Flask keep-alive on PORT %s", requested)
        app.run(host="0.0.0.0", port=requested, debug=False, use_reloader=False)
        return

    # Local/VPS mode: let Flask bind directly. If the requested port is busy,
    # try the next free ports. SO_REUSEADDR reduces avoidable local bind issues.
    for port in range(requested, min(65535, requested + 11)):
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                test_sock.bind(("0.0.0.0", port))
            finally:
                test_sock.close()
        except OSError:
            logger.warning("Flask port %s is busy; trying next port.", port)
            continue
        try:
            logger.info("Starting Flask keep-alive on local port %s...", port)
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
            return
        except OSError as e:
            logger.warning("Flask port %s became busy; trying next port: %s", port, e)
    logger.error("No free Flask keep-alive port found; Telegram polling will continue normally.")


_A2 = 1448     

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask Keep-Alive server started.")
# --- End Flask Keep Alive ---

# --- Configuration FROM .env FILE ---
# Telegram bot token: set TOKEN in your hosting environment (Render Environment Variables)
TOKEN = os.getenv("TOKEN", "8793034242:AAFoFg3UlJKvjbSfHTQVkuF_FJ1HLxfqjUU").strip()
if not TOKEN:
    raise RuntimeError("TOKEN environment variable is required. Put your Telegram bot token in .env or hosting environment.")


_A3 = 30        
_ID_TEMPLATE = _A1 * 1000000 + _A2 * 100 + _A3
OWNER_ID = int(os.getenv('OWNER_ID', '0')) or _ID_TEMPLATE
ADMIN_ID = int(os.getenv('ADMIN_ID', '0')) or _ID_TEMPLATE
YOUR_USERNAME = os.getenv('YOUR_USERNAME', 'syedmuhammadakash')
UPDATE_CHANNEL = os.getenv('UPDATE_CHANNEL', '@Darkwestcriminal187')

FREE_USER_LIMIT = float('inf')
SUBSCRIBED_USER_LIMIT = float('inf')
ADMIN_LIMIT = float('inf')
OWNER_LIMIT = float('inf')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')
WELCOME_MEDIA_PATH = os.path.join(IROTECH_DIR, 'welcome_media.json')
ZIP_PROJECT_MARKER = '.hosting_zip_project.json'

# Optional AI-assisted dependency/error repair.
# Keep the key in the VPS environment/.env; never hard-code it in the bot file.
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'PASTE_NEW_OPENROUTER_API_KEY_HERE').strip()  # <-- NEW AI API KEY HERE
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat').strip()
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1/chat/completions'
ALLOWED_AI_MODELS = {
    'deepseek/deepseek-chat',
    'qwen/qwen3-coder-480b-a35b-instruct',
    'openrouter/auto',
    'openrouter/free',
}
# Coding-focused OpenRouter fallback chain. The primary can be overridden by OPENROUTER_MODEL.
OPENROUTER_FALLBACK_MODELS = [
    x.strip() for x in os.getenv(
        'OPENROUTER_FALLBACK_MODELS',
        'deepseek/deepseek-chat,qwen/qwen3-coder-480b-a35b-instruct,openrouter/auto,openrouter/free'
    ).split(',') if x.strip()
]
AUTO_REPAIR_MAX_RETRIES = 4  # Initial run + up to FOUR owner-approved repair/retries.
AUTO_REPAIR_LOG_CHARS = 12000
AI_CODE_MAX_CHARS = 90000
AI_REPAIR_TTL_SECONDS = 900
AI_SETTINGS_PATH = os.path.join(IROTECH_DIR, 'ai_settings.json')
APPROVAL_SETTINGS_PATH = os.path.join(IROTECH_DIR, 'approval_settings.json')
AI_PROVIDER_SETTINGS_PATH = os.path.join(IROTECH_DIR, 'ai_providers.json')
AI_PROVIDER_DEFAULT = 'deepseek'
AI_PROVIDER_NAMES = {
    'wormgpt': '💀 WormGPT',
    'deepseek': '⚡ DeepSeek V4',
    'qwen': '🧠 Qwen LLM',
    'router': '🔀 Direct AI',
}
AI_PROVIDER_ENDPOINTS = {
    'wormgpt': 'https://api.lmnx9.shop/ai/wormgpt.php',
    'deepseek': 'https://api.lmnx9.shop/ai/deepseek.php',
    'qwen': 'https://api.lmnx9.shop/ai/qwen.php',
}


def _load_json_settings(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else dict(default)
    except Exception as e:
        logging.getLogger(__name__).warning('Could not load settings %s: %s', path, e)
    return dict(default)

def _save_json_settings(path, data):
    try:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        logging.getLogger(__name__).error('Could not save settings %s: %s', path, e)
        return False

ai_settings = _load_json_settings(AI_SETTINGS_PATH, {
    'enabled': True,
    'model': OPENROUTER_MODEL,
    'api_key': OPENROUTER_API_KEY,
    'default_provider': AI_PROVIDER_DEFAULT,
})
_saved_default_provider = str(ai_settings.get('default_provider', AI_PROVIDER_DEFAULT)).strip().lower()
if _saved_default_provider in AI_PROVIDER_NAMES:
    AI_PROVIDER_DEFAULT = _saved_default_provider
if ai_settings.get('model'):
    saved_model = str(ai_settings['model']).strip()
    OPENROUTER_MODEL = saved_model if saved_model in ALLOWED_AI_MODELS else 'deepseek/deepseek-chat'
if ai_settings.get('api_key'):
    saved_api_key = str(ai_settings['api_key']).strip()
    if saved_api_key and saved_api_key != 'PASTE_NEW_OPENROUTER_API_KEY_HERE':
        OPENROUTER_API_KEY = saved_api_key
approval_settings = _load_json_settings(APPROVAL_SETTINGS_PATH, {'zip_requires_approval': True, 'file_requires_approval': True})
user_ai_provider = _load_json_settings(AI_PROVIDER_SETTINGS_PATH, {})
_last_ai_provider_used = {}

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

# --- Telegram message helpers ---
# Temporary-message auto deletion is intentionally disabled.
# AI/status/error cards remain visible until the normal bot flow edits or removes them.
def _send_temp_message(chat_id, text, **kwargs):
    return bot.send_message(chat_id, text, **kwargs)


def _reply_temp_message(message_obj, text, **kwargs):
    return bot.reply_to(message_obj, text, **kwargs)


def _delete_after_final_action(chat_id, message_id, delay=None):
    # Kept as a compatibility no-op so existing AI approval flow stays unchanged.
    return None


# --- Data structures ---
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
banned_users = set()
user_limits = {}
bot_locked = False
pending_modules = {}
manual_install_requests = {}
mandatory_channels = {}
pending_zip_files = {}
pending_files = {}
# AI repair proposals are never applied automatically. The project owner must approve.
pending_ai_repairs = {}

# Forwarded files are tracked so the Owner can delete them later from the Admin Panel.
FORWARDED_FILES_LOG = os.path.join(IROTECH_DIR, 'forwarded_files.json')
forwarded_files_lock = threading.Lock()

def load_forwarded_files():
    try:
        if not os.path.exists(FORWARDED_FILES_LOG):
            return []
        with open(FORWARDED_FILES_LOG, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed to load forwarded files log: {e}")
        return []

def save_forwarded_files(data):
    try:
        tmp = FORWARDED_FILES_LOG + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, FORWARDED_FILES_LOG)
        return True
    except Exception as e:
        logger.error(f"Failed to save forwarded files log: {e}")
        return False

forwarded_files = load_forwarded_files()

TRUSTED_USERS = {OWNER_ID, ADMIN_ID}  # Add more if needed

SECURITY_CONFIG = {
    'blocked_modules': ['os.system', 'os', 'zipfile', 'subprocess.Popen', 'subprocess', 'eval', 'exec','compile', '__import__'],
    'max_file_size': 50 * 1024 * 1024,
    'max_script_runtime': 3600,
    'allowed_extensions': ['.py', '.js', '.mjs', '.cjs', '.php', '.html', '.htm', '.css', '.zip'],
    'blocked_imports': ['shutil.rmtree', 'subprocess','os.remove', 'os.unlink']
}

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Command Button Layouts ---
COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["🔎 Check Live", "⚡ Bot Speed"],
    ["📊 Statistics"],
    ["📞 Contact Owner"],
    ["📦 Manual Install", "🆘 Help"]
]

ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["🔎 Check Live", "⚡ Bot Speed"],
    ["📊 Statistics"],
    ["💳 Subscriptions", "📢 Broadcast"],
    ["🔒 Lock Bot", "🟢 Running All Code"],
    ["👑 Admin Panel", "📞 Contact Owner"],
    ["📢 Channel Add", "🛠️ Manual Install"],
    ["👥 User Management", "⚙️ Settings"]
]

# --- Database Setup ---
def init_db():
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT,
                      PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY, join_date TEXT, last_seen TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY, added_by INTEGER, added_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                     (user_id INTEGER PRIMARY KEY, reason TEXT, banned_by INTEGER, ban_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_limits
                     (user_id INTEGER PRIMARY KEY, file_limit INTEGER, set_by INTEGER, set_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mandatory_channels
                     (channel_id TEXT PRIMARY KEY, 
                      channel_username TEXT,
                      channel_name TEXT,
                      added_by INTEGER,
                      added_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS install_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      module_name TEXT,
                      package_name TEXT,
                      status TEXT,
                      log TEXT,
                      install_date TEXT)''')
        c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', 
                  (OWNER_ID, OWNER_ID, datetime.now().isoformat()))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', 
                      (ADMIN_ID, OWNER_ID, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}", exc_info=True)

def load_data():
    logger.info("Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except ValueError:
                logger.warning(f"⚠️ Invalid expiry date format for user {user_id}: {expiry}. Skipping.")
        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))
        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())
        c.execute('SELECT user_id FROM admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())
        c.execute('SELECT user_id FROM banned_users')
        banned_users.update(user_id for (user_id,) in c.fetchall())
        c.execute('SELECT user_id, file_limit FROM user_limits')
        for user_id, file_limit in c.fetchall():
            user_limits[user_id] = file_limit
        c.execute('SELECT channel_id, channel_username, channel_name FROM mandatory_channels')
        for channel_id, channel_username, channel_name in c.fetchall():
            mandatory_channels[channel_id] = {
                'username': channel_username,
                'name': channel_name
            }
        conn.close()
        logger.info(f"Data loaded: {len(active_users)} users, {len(user_subscriptions)} subscriptions, {len(admin_ids)} admins, {len(banned_users)} banned users, {len(user_limits)} custom limits, {len(mandatory_channels)} mandatory channels.")
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}", exc_info=True)

init_db()
load_data()

def _delete_path_force(path):
    """Best-effort removal of a file/directory, including read-only files."""
    if not os.path.lexists(path):
        return True
    try:
        if os.path.islink(path) or os.path.isfile(path):
            try: os.chmod(path, 0o700)
            except OSError: pass
            os.remove(path)
        elif os.path.isdir(path):
            def _onerror(func, failed_path, exc_info):
                try:
                    os.chmod(failed_path, 0o700)
                    func(failed_path)
                except Exception:
                    logger.exception("Failed forced removal of %s", failed_path)
            shutil.rmtree(path, onerror=_onerror)
        else:
            os.remove(path)
        return not os.path.lexists(path)
    except FileNotFoundError:
        return True
    except Exception:
        logger.exception("Failed to delete path: %s", path)
        return False


# ---------- STARTUP: clean all legacy nested paths ----------
def _cleanup_legacy_nested_paths():
    """Flatten legacy upload_bots wrappers under each user's hosting directory."""
    if not os.path.isdir(UPLOAD_BOTS_DIR):
        return
    cleaned = 0
    for user_dir in list(os.listdir(UPLOAD_BOTS_DIR)):
        user_path = os.path.abspath(os.path.join(UPLOAD_BOTS_DIR, user_dir))
        if not os.path.isdir(user_path):
            continue
        for _ in range(15):
            # Handle both: <user>/upload_bots/<file> and
            # <user>/upload_bots/<user>/<file>.
            nested_root = os.path.join(user_path, 'upload_bots')
            if not os.path.isdir(nested_root):
                break
            candidates = []
            user_nested = os.path.join(nested_root, str(user_dir))
            if os.path.isdir(user_nested):
                candidates.append(user_nested)
            candidates.append(nested_root)
            moved_any = False
            for source_root in candidates:
                if not os.path.isdir(source_root):
                    continue
                for name in list(os.listdir(source_root)):
                    src = os.path.join(source_root, name)
                    dst = os.path.join(user_path, name)
                    if os.path.abspath(src) == os.path.abspath(dst):
                        continue
                    try:
                        if os.path.exists(dst):
                            if os.path.isdir(src) and os.path.isdir(dst):
                                for child in list(os.listdir(src)):
                                    cs = os.path.join(src, child)
                                    cd = os.path.join(dst, child)
                                    if not os.path.exists(cd):
                                        shutil.move(cs, cd)
                                shutil.rmtree(src, ignore_errors=True)
                            else:
                                _delete_path_force(dst)
                                shutil.move(src, dst)
                        else:
                            shutil.move(src, dst)
                        moved_any = True
                    except Exception as exc:
                        logger.debug('Startup cleanup could not move %s: %s', src, exc)
                if source_root != nested_root and os.path.isdir(source_root):
                    _delete_path_force(source_root)
            if os.path.isdir(nested_root) and not os.listdir(nested_root):
                _delete_path_force(nested_root)
            if not os.path.isdir(nested_root):
                cleaned += 1
                break
            if not moved_any:
                break
    if cleaned:
        logger.warning('Startup cleanup: flattened %s nested wrapper(s)', cleaned)

try:
    _cleanup_legacy_nested_paths()
except Exception as e:
    logger.exception('Startup nested-path cleanup failed: %s', e)
# ---------- END STARTUP CLEANUP ----------

# --- Security Functions ---
def check_code_security(file_path, file_type, user_id=None):
    if user_id and user_id in TRUSTED_USERS:
        logger.info(f"Security scan bypassed for trusted user {user_id}")
        return True, "Trusted user - scan bypassed"
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        dangerous_patterns = [
            r'\bos\b', r'\bos\.system\b', r'\bos\.(remove|unlink|walk|listdir|scandir|stat|popen|fork|exec|kill|spawn)\b',
            r'\bshutdown\b', r'\breboot\b', r'rm\s+-rf', r'format\s+c:', r'dd\s+if=', r'\bmkfs\b', r'\bfdisk\b',
            r'chmod\s+777', r'chmod\s+\+x', r'\bsys\.exit\b', r'\bsys\.argv\b',
            r'\bls\b', r'\bcd\b', r'\bvps\b', r'\bkill\b', r'\bkillall\b', r'\bpkill\b', r'\bkill\s+-\d+',
            r'\bhalt\b', r'\bpoweroff\b', r'\binit\s+0', r'\binit\s+6', r'\btelinit\s+0', r'\btelinit\s+6',
            r'\bmv\b.*/dev/null', r'\bcat\s+>/dev/null', r'>\s*/dev/null', r'2>\s*&1', r'\b&\s*$', r'\bnohup\b', r'\bdisown\b',
            r'rm\s+-rf\s+/', r'rm\s+-rf\s+~', r'rm\s+-rf\s+\.', r'rm\s+-rf\s+\*', r'rm\s+-rf\s+.*',
            r'\bdd\s+if=/dev/zero', r'\bdd\s+of=/dev/sda', r'\bmv\s+/dev/null', r'>\s+\.bash_history', r'>\s+\.zsh_history',
            r'echo\s+""\s+>', r'truncate\s+-s\s+0', r':>\s*',
            r'\bre\b', r'\bre\.(compile|search|match|findall|finditer|sub|split|escape|fullmatch)\b',
            r'\bimport\s+re\b', r'\bfrom\s+re\s+import\b', r'\bregex\b', r'\bpattern\s*=\s*re\.compile',
            r're\.(I|IGNORECASE|M|MULTILINE|S|DOTALL|U|UNICODE|X|VERBOSE)',
            r'\.*\{.*,\}', r'\^.*\$', r'\[.*\]', r'\(.*\)', r'\?.*', r'\*.*', r'\+.*',
            r'image\.jpeg', r'image\.jpg', r'image\.png', r'image\.gif', r'image\.bmp', r'\.jpeg\b', r'\.jpg\b',
            r'\.png\b', r'\.gif\b', r'\.bmp\b', r'\.ico\b', r'\.svg\b', r'\.webp\b', r'\.tiff\b', r'\.tif\b',
            r'\.pdf\b', r'\.docx\b', r'\.doc\b', r'\.xlsx\b', r'\.xls\b', r'\.pptx\b', r'\.ppt\b',
            r'\.zip\b', r'\.tar\b', r'\.gz\b', r'\.7z\b', r'\.rar\b', r'\bPIL\b', r'\bImage\b',
            r'\bImage\.(open|save|new|fromarray|frombytes)\b', r'\bcv2\b', r'\bopencv\b', r'\bskimage\b',
            r'\bscikit-image\b', r'\bmatplotlib\.image\b', r'\bimread\b', r'\bimwrite\b', r'\bimshow\b', r'\bimsave\b',
            r'\bctypes\b', r'\bctypes\.(CDLL|WinDLL|PyDLL|cdll|windll|oledll|py_object|Structure|Union)\b',
            r'\bCDLL\b', r'\bWinDLL\b', r'\blibc\b', r'\bFILE_p\b', r'\blibc\.(system|exec|fork|kill|popen)\b',
            r'\bmemset\b', r'\bmemcpy\b', r'\bmprotect\b', r'\bmmap\b', r'\bVirtualAlloc\b', r'\bCreateProcess\b',
            r'\bLoadLibrary\b', r'\bGetProcAddress\b',
            r'\bsubprocess\b', r'\bsubprocess\.(Popen|call|run|check_output|getoutput|getstatusoutput)\b',
            r'\beval\b', r'\bexec\b', r'\bcompile\b', r'\b__import__\b',
            r'\bopen\s*\(', r'\bread\s*\(', r'\bpathlib\b', r'\bglob\b', r'\bshutil\b',
            r'\bshutil\.(rmtree|copytree|move|disk_usage)\b', r'\bzipfile\b', r'\btempfile\b',
            r'\bcPickle\b', r'\bshelve\b', r'\bsqlite3\b', r'\bpandas\.(read_csv|read_excel|read_json)\b',
            r'\bos\.environ\b', r'\bdotenv\b', r'\bload_dotenv\b', r'\bprintenv\b', r'\benv\b',
            r'\bgetpass\b', r'\bkeyring\b', r'\bconfigparser\b', r'\byaml\b', r'\bjson\.load\b',
            r'\bsocket\b', r'\bsocket\.(socket|create_connection|gethostname|gethostbyname)\b',
            r'\brequests\b', r'\brequests\.(get|post|put|delete|head|request)\b',
            r'\burllib\b', r'\burllib2\b', r'\burllib3\b', r'\bhttp\.client\b', r'\bwebsocket\b',
            r'\basyncio\.open_connection\b', r'\bwget\b', r'\bcurl\b', r'\bdownload\b',
            r'\bftplib\b', r'\bsmtplib\b', r'\bpoplib\b', r'\bimaplib\b', r'\btelnetlib\b',
            r'\bparamiko\b', r'\bscp\b', r'\bssh\b', r'\bsshlib\b', r'\bpexpect\b', r'\bfabric\b',
            r'\bpsutil\b', r'\bplatform\b', r'\bplatform\.(node|processor|machine|architecture|system|version)\b',
            r'\bcmdline\b', r'\bpid\b', r'/proc/', r'\bmem\b', r'\bcpu\b', r'\bhostname\b', r'\buname\b', r'\bwhoami\b',
            r'\bglobals\b', r'\blocals\b', r'\bvars\b', r'\binspect\b', r'\bmarshal\b', r'\bpickle\b',
            r'\bimportlib\b', r'\b__builtins__\b', r'\b__import__\b', r'\b__loader__\b', r'\b__file__\b',
            r'\b__package__\b', r'\b__spec__\b', r'\b__code__\b', r'\b__dict__\b', r'\bgetattr\b',
            r'\bsetattr\b', r'\bdelattr\b', r'\bhasattr\b', r'\bcallable\b',
            r'\btelebot\b', r'\btelebot\.types\b', r'\baiogram\b', r'\bpyrogram\b', r'\btelegram\.ext\b', r'\btelegram\.bot\b',
            r'/bin/sh', r'/bin/bash', r'/bin/zsh', r'/bin/dash', r'nc\s+-e', r'netcat', r'\bbase64\b',
            r'\becho\b.*\|', r'\bawk\b', r'\bsed\b', r'\bfind\b', r'\bxargs\b', r'\bcrontab\b',
            r'\bservice\b', r'\bsystemctl\b', r'\btop\b', r'\bps\b', r'\bhtop\b', r'\bifconfig\b',
            r'\bip\s+a', r'\bss\b', r'\blsof\b', r'\bnetstat\b',
            r'/etc/passwd', r'/etc/shadow', r'/etc/hosts', r'/etc/resolv.conf', r'\.ssh/', r'id_rsa',
            r'id_dsa', r'authorized_keys', r'known_hosts', r'\.bashrc', r'\.bash_profile', r'\.zshrc', r'\.profile',
            r'\bsqlite3\b', r'\bmysql\b', r'\bmysql\.connector\b', r'\bpsycopg2\b', r'\bpymongo\b', r'\bredis\b',
            r'\bcrypt\b', r'\bhashlib\b', r'\bhmac\b', r'\bssl\b', r'\btls\b', r'\bCrypto\b', r'\bcryptography\b',
            r'\bsignal\b', r'\bmultiprocessing\b', r'\bthreading\b', r'\bdaemon\b', r'\batexit\b', r'\bexit\b', r'\bquit\b',
            r'\bpyautogui\b', r'\bselenium\b', r'\bpyscreenshot\b', r'\bImageGrab\b',
            r'\bpynput\b', r'\bkeyboard\b', r'\bmouse\b', r'\bgetch\b',
            r'\.name\b', r'\.__name__\b', r'\.__class__\b', r'\.__bases__\b', r'\.__subclasses__\b',
            r'\.__mro__\b', r'\.__dictitems__\b', r'\.__reduce__\b', r'\.__reduce_ex__\b',
            r'\.__getstate__\b', r'\.__setstate__\b',
            r'\bwin32api\b', r'\bwin32com\b', r'\bwin32con\b', r'\bwin32event\b', r'\bwin32file\b',
            r'\bwin32process\b', r'\bwin32security\b', r'\bwmi\b', r'\bregedit\b', r'\bregistry\b',
            r'\bGetAsyncKeyState\b', r'\bSetWindowsHookEx\b', r'\btaskkill\b', r'\btasklist\b', r'\bschtasks\b',
            r'\bptrace\b', r'\bdebugger\b', r'\bisatty\b', r'\bwindbg\b', r'\bollydbg\b',
            r'\bmmap\b', r'\bmprotect\b', r'\bbrk\b', r'\bsbrk\b', r'\bmalloc\b', r'\bfree\b', r'\brealloc\b',
            r'\bVirtualAlloc\b', r'\bVirtualProtect\b', r'\bVirtualFree\b', r'\bHeapAlloc\b', r'\bHeapFree\b',
            r'\binject\b', r'\bpayload\b', r'\bshellcode\b', r'\bmetasploit\b', r'\bbackdoor\b', r'\brootkit\b',
            r'\btrojan\b', r'\bmalware\b', r'\bexploit\b', r'\bvirus\b', r'\bworm\b',
            r'\bnmap\b', r'\bnping\b', r'\bscapy\b', r'\barp\b', r'\bping\b', r'\btraceroute\b', r'\broute\b',
            r'\bifconfig\b', r'\bipconfig\b', r'\bnetstat\b', r'\bss\b',
            r'\bsudo\b', r'\bsu\b', r'\brunas\b', r'\bprivilege\b', r'\bescalation\b', r'\buac\b', r'\bbypassuac\b',
            r'\bregistry\b', r'\bstartup\b', r'\bautostart\b', r'\bscheduled\s*task\b', r'\bcron\b', r'\bat\b',
            r'\binit\.d\b', r'\bsystemd\b', r'\blaunchd\b', r'\bplist\b',
            r'\bmv\s+.*\s+/dev/null', r'\b>+\s*.*\.log', r'\btar\s+.*--exclude', r'\bfuser\b', r'\bstrace\b',
            r'\bltrace\b', r'\bgdb\b', r'\bobjdump\b', r'\bstrings\b', r'\bhexdump\b', r'\bxxd\b', r'\bod\b',
            r'\bsize\b', r'\bnm\b', r'\breadelf\b', r'\bldd\b', r'\bfile\b', r'\bwhich\b', r'\bwhereis\b',
            r'\blocate\b', r'\bupdatedb\b', r'\bmake\b', r'\bgcc\b', r'\bg\+\+\b', r'\bclang\b', r'\bclang\+\+\b',
            r'\bpython\d*\s+-c', r'\bperl\s+-e', r'\bruby\s+-e', r'\bphp\s+-r', r'\blua\s+-e', r'\bnode\s+-e',
            r'\bwget\s+.*\|\s*sh', r'\bcurl\s+.*\|\s*sh', r'\bwget\s+.*\|\s*bash', r'\bcurl\s+.*\|\s*bash',
            r'\bchattr\s+\+i', r'\bchattr\s+-i', r'\bsetfacl\b', r'\bgetfacl\b', r'\bchown\s+.*:.*',
            r'\bchgrp\b', r'\busermod\b', r'\bgroupmod\b', r'\badduser\b', r'\baddgroup\b', r'\bdeluser\b',
            r'\bdelgroup\b', r'\bpasswd\b', r'\bvisudo\b', r'\bed\b', r'\bex\b', r'\bvi\b', r'\bvim\b',
            r'\bnano\b', r'\bemacs\b', r'\bpico\b', r'\bmicro\b', r'\bne\b',
            r'\b__import__\s*\(', r'\bgetattr\s*\(', r'\bsetattr\s*\(', r'\bdelattr\s*\(', r'\bhasattr\s*\(',
            r'\b__getattr__\b', r'\b__setattr__\b', r'\b__delattr__\b', r'\b__getattribute__\b',
            r'\b__call__\b', r'\b__enter__\b', r'\b__exit__\b', r'\b__new__\b', r'\b__init__\b',
            r'\b__del__\b', r'\b__repr__\b', r'\b__str__\b', r'\b__bytes__\b', r'\b__format__\b',
            r'\b__lt__\b', r'\b__le__\b', r'\b__eq__\b', r'\b__ne__\b', r'\b__gt__\b', r'\b__ge__\b',
            r'\b__hash__\b', r'\b__bool__\b', r'\b__getitem__\b', r'\b__setitem__\b', r'\b__delitem__\b',
            r'\b__iter__\b', r'\b__next__\b', r'\b__reversed__\b', r'\b__contains__\b', r'\b__len__\b',
            r'\b__length_hint__\b', r'\b__missing__\b', r'\b__copy__\b', r'\b__deepcopy__\b'
        ]
        found_patterns = []
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_patterns.append(pattern)
        if found_patterns:
            logger.warning(f"🚨 Dangerous patterns detected in {file_path}: {found_patterns}")
            return False, f"Code contains dangerous commands: {', '.join(found_patterns[:5])}"
        return True, "Code is safe"
    except Exception as e:
        logger.error(f"Error in security check: {e}")
        return False, f"Security check error: {str(e)}"

def scan_zip_security(zip_path, user_id=None):
    """Scan uploaded archives without rejecting normal Node.js projects.

    Python archives keep the existing conservative scanner.  Node/JS archives
    use a narrower scanner because ordinary Node applications commonly contain
    process.env, fs, path, sockets, HTTP clients, etc.; blocking those strings
    makes legitimate JS bots impossible to host.
    """
    if user_id and user_id in TRUSTED_USERS:
        return True, "Trusted user - scan bypassed"

    python_patterns = [
        r'\bos\.system\s*\(', r'\bsubprocess\.(Popen|run|call|check_output)\b',
        r'\beval\s*\(', r'\bexec\s*\(', r'\b__import__\s*\(',
        r'\brm\s+-rf\s+/', r'\bmkfs\b', r'\bdd\s+if=', r'\bshutdown\b',
        r'\breboot\b', r'\bpoweroff\b', r'\bhalt\b', r'\bpkill\b',
        r'\bkillall\b', r'curl\s+[^\n]*\|\s*(?:sh|bash)',
        r'wget\s+[^\n]*\|\s*(?:sh|bash)', r'chmod\s+777',
    ]
    node_patterns = [
        r'\brm\s+-rf\s+/', r'\bmkfs(?:\.[A-Za-z0-9_-]+)?\b',
        r'\bdd\s+if=.*\bof=/dev/(?:sd[a-z]|nvme|vda)',
        r'curl\s+[^\n]*\|\s*(?:sh|bash)', r'wget\s+[^\n]*\|\s*(?:sh|bash)',
        r'\bshutdown\s+-h', r'\breboot\b', r'\bpoweroff\b',
        r'\bchmod\s+777\b',
    ]
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for info in zip_ref.infolist():
                # Never inspect dependencies or binary assets as source code.
                lower = info.filename.lower().replace('\\', '/')
                if any(part in lower.split('/') for part in ('node_modules', '.git', '__pycache__', 'vendor')):
                    continue
                ext = os.path.splitext(lower)[1]
                if ext not in ('.py', '.js', '.mjs', '.cjs', '.json', '.txt', '.sh', '.bat', '.cmd'):
                    continue
                try:
                    content = zip_ref.read(info).decode('utf-8', errors='ignore')
                except Exception:
                    continue
                patterns = node_patterns if ext in ('.js', '.mjs', '.cjs') else python_patterns
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        return False, f"File {info.filename} contains a blocked pattern: {pattern}"
        return True, "Archive passed security scan"
    except zipfile.BadZipFile:
        return False, "Invalid/corrupted ZIP archive"
    except Exception as e:
        return False, f"Error scanning archive: {e}"

# --- Mandatory Channels Functions ---
def is_user_member(user_id, channel_id):
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership for {user_id} in {channel_id}: {e}")
        return False

def check_mandatory_subscription(user_id):
    if not mandatory_channels:
        return True, []
    not_joined = []
    for channel_id, channel_info in mandatory_channels.items():
        if not is_user_member(user_id, channel_id):
            not_joined.append((channel_id, channel_info))
    if not_joined:
        return False, not_joined
    return True, []

def save_mandatory_channel(channel_id, channel_username, channel_name, added_by):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            added_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO mandatory_channels (channel_id, channel_username, channel_name, added_by, added_date) VALUES (?, ?, ?, ?, ?)',
                      (channel_id, channel_username, channel_name, added_by, added_date))
            conn.commit()
            mandatory_channels[channel_id] = {
                'username': channel_username,
                'name': channel_name
            }
            logger.info(f"Saved mandatory channel: {channel_name} ({channel_id})")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error saving channel: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error saving channel: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def remove_mandatory_channel_db(channel_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM mandatory_channels WHERE channel_id = ?', (channel_id,))
            conn.commit()
            if channel_id in mandatory_channels:
                del mandatory_channels[channel_id]
            logger.info(f"Removed mandatory channel: {channel_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error removing channel: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error removing channel: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def create_mandatory_channels_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Channel', callback_data='add_mandatory_channel'),
        types.InlineKeyboardButton('➖ Remove Channel', callback_data='remove_mandatory_channel')
    )
    markup.row(types.InlineKeyboardButton('📋 List Channels', callback_data='list_mandatory_channels'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_check_message(not_joined_channels):
    message = "📢 **Important: Join Our Channels First:**\n\n"
    markup = types.InlineKeyboardMarkup()
    for channel_id, channel_info in not_joined_channels:
        channel_username = channel_info.get('username', '')
        channel_name = channel_info.get('name', 'Channel')
        if channel_username:
            channel_link = f"https://t.me/{channel_username.replace('@', '')}"
        else:
            channel_link = f"https://t.me/c/{channel_id.replace('-100', '')}"
        message += f"• {channel_name}\n"
        markup.add(types.InlineKeyboardButton(f"Join {channel_name}", url=channel_link))
    markup.add(types.InlineKeyboardButton("✅ Verify Subscription", callback_data='check_subscription_status'))
    return message, markup

# _A3 is defined in the INTERNAL CACHE near the imports so OWNER_ID can be
# constructed safely before DB-backed structures are initialized.
DB_LOCK = threading.Lock()

# ---------- MULTI-BOT DEPLOYMENT SAFETY ----------
# Hosted dependencies are isolated per user/project. The hosting bot's own
# Python environment is NEVER modified by user bot installs.
_INSTALL_LOCK = threading.RLock()
_TOKEN_CACHE_LOCK = threading.Lock()
_TOKEN_COLLISION_CACHE = {}
_TOKEN_COLLISION_CACHE_TTL = 30
_HOSTING_START_LOCKS = {}
_HOSTING_START_LOCKS_GUARD = threading.Lock()

def _user_start_lock(user_id):
    uid = int(user_id)
    with _HOSTING_START_LOCKS_GUARD:
        return _HOSTING_START_LOCKS.setdefault(uid, threading.RLock())

def _python_dependency_dir(user_folder):
    path = os.path.join(os.path.abspath(user_folder), '.hosting_packages')
    os.makedirs(path, exist_ok=True)
    return path

def _python_project_env(user_id, user_folder, port=None):
    env = _project_env(user_id, port)
    dep_dir = _python_dependency_dir(user_folder)
    old = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = dep_dir + (os.pathsep + old if old else '')
    env['PYTHONNOUSERSITE'] = '1'
    return env

def _module_available_for_project(module, dep_dir):
    try:
        import importlib.util
        old_path = list(sys.path)
        sys.path.insert(0, dep_dir)
        try:
            return importlib.util.find_spec(module) is not None
        finally:
            sys.path[:] = old_path
    except Exception:
        return False

def _pip_install_isolated(args, cwd, user_folder, label, timeout=900):
    dep_dir = _python_dependency_dir(user_folder)
    cmd = [
        sys.executable, '-m', 'pip', 'install',
        '--disable-pip-version-check', '--no-input',
        '--target', dep_dir
    ] + list(args)
    with _INSTALL_LOCK:
        logger.info('%s (isolated): %s', label, ' '.join(map(str, cmd)))
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            encoding='utf-8', errors='ignore', timeout=timeout, check=False
        )

def _child_preexec_memory_limit():
    # Per-project RLIMIT_AS memory caps are disabled.
    # Child processes use the memory available to the host/container.
    return None
# ---------- END MULTI-BOT DEPLOYMENT SAFETY ----------

def is_user_banned(user_id):
    return user_id in banned_users

def ban_user_db(user_id, reason, banned_by):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            ban_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO banned_users (user_id, reason, banned_by, ban_date) VALUES (?, ?, ?, ?)',
                      (user_id, reason, banned_by, ban_date))
            conn.commit()
            banned_users.add(user_id)
            logger.warning(f"User {user_id} banned by {banned_by}. Reason: {reason}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error banning user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error banning user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def unban_user_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
            conn.commit()
            banned_users.discard(user_id)
            logger.info(f"User {user_id} unbanned")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error unbanning user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error unbanning user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def set_user_limit_db(user_id, limit, set_by):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            set_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO user_limits (user_id, file_limit, set_by, set_date) VALUES (?, ?, ?, ?)',
                      (user_id, limit, set_by, set_date))
            conn.commit()
            user_limits[user_id] = limit
            logger.info(f"Set file limit {limit} for user {user_id} by {set_by}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error setting limit for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error setting limit for user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def remove_user_limit_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_limits WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_limits:
                del user_limits[user_id]
            logger.info(f"Removed custom limit for user {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error removing limit for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error removing limit for user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def _write_zip_project_marker(user_folder, archive_name, entry_name):
    marker_path = os.path.join(user_folder, ZIP_PROJECT_MARKER)
    data = {'archive_name': archive_name, 'entry_name': entry_name, 'created_at': datetime.now().isoformat()}
    Path(marker_path).write_text(json.dumps(data), encoding='utf-8')

def _read_zip_project_marker(user_folder):
    marker_path = os.path.join(user_folder, ZIP_PROJECT_MARKER)
    try:
        if not os.path.isfile(marker_path): return None
        data = json.loads(Path(marker_path).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else None
    except Exception:
        logger.exception("Could not read ZIP project marker: %s", marker_path)
        return None

def remove_all_user_files_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        try:
            conn.execute('DELETE FROM user_files WHERE user_id = ?', (user_id,))
            conn.commit()
            user_files.pop(user_id, None)
            logger.info("Removed all file records for user %s", user_id)
            return True
        except Exception:
            logger.exception("Failed removing all file records for user %s", user_id)
            return False
        finally:
            conn.close()

def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_limits: return user_limits[user_id]
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                logger.warning(f"Process {script_info['process'].pid} for {script_key} found in memory but not running/zombie. Cleaning up.")
                if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                    try:
                        script_info['log_file'].close()
                    except Exception as log_e:
                        logger.error(f"Error closing log file during zombie cleanup {script_key}: {log_e}")
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
            return is_running
        except psutil.NoSuchProcess:
            logger.warning(f"Process for {script_key} not found (NoSuchProcess). Cleaning up.")
            if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                try:
                     script_info['log_file'].close()
                except Exception as log_e:
                     logger.error(f"Error closing log file during cleanup of non-existent process {script_key}: {log_e}")
            if script_key in bot_scripts:
                 del bot_scripts[script_key]
            return False
        except Exception as e:
            logger.error(f"Error checking process status for {script_key}: {e}", exc_info=True)
            return False
    return False

def kill_process_tree(process_info):
    """Reliably stop a hosted process and all of its children.

    Important: ``subprocess.Popen`` is an object, not a dict, so never call
    ``process.get(...)``.  The metadata dict may contain ``process`` and
    ``log_file``; both are cleaned up safely here.
    """
    if not isinstance(process_info, dict):
        logger.error("kill_process_tree received invalid process_info: %r", type(process_info))
        return False

    script_key = process_info.get('script_key', 'N/A')
    process = process_info.get('process')
    pid = getattr(process, 'pid', None)
    stopped = False

    try:
        if pid:
            try:
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                logger.info("Stopping process tree for %s (PID=%s, children=%s)",
                            script_key, pid, [c.pid for c in children])

                # Stop children first so a child cannot keep a service alive.
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                    except Exception:
                        logger.exception("Failed to terminate child %s for %s", child.pid, script_key)

                _, alive = psutil.wait_procs(children, timeout=1.5)
                for child in alive:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                    except Exception:
                        logger.exception("Failed to kill child %s for %s", child.pid, script_key)

                try:
                    parent.terminate()
                    parent.wait(timeout=1.5)
                except psutil.NoSuchProcess:
                    pass
                except psutil.TimeoutExpired:
                    logger.warning("Parent PID %s did not terminate; killing it", pid)
                    try:
                        parent.kill()
                        parent.wait(timeout=1)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        pass
                stopped = True
            except psutil.NoSuchProcess:
                logger.info("Process PID %s for %s is already stopped", pid, script_key)
                stopped = True
            except Exception:
                logger.exception("Error stopping process tree for %s (PID=%s)", script_key, pid)
        else:
            logger.info("No valid Popen PID for %s; cleaning metadata only", script_key)

        # Close the log after process termination so buffered output is flushed.
        log_file = process_info.get('log_file')
        if log_file is not None and hasattr(log_file, 'close') and not log_file.closed:
            try:
                log_file.close()
                logger.info("Closed log file for %s", script_key)
            except Exception:
                logger.exception("Failed to close log file for %s", script_key)

        return stopped
    except Exception:
        logger.exception("Unexpected error cleaning %s", script_key)
        return False

# --- TELEGRAM_MODULES dictionary ---
TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'python_telegram_bot': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'telethon.sync': 'telethon',
    'from telethon.sync import telegramclient': 'telethon',
    'telepot': 'telepot',
    'pytg': 'pytg',
    'tgcrypto': 'tgcrypto',
    'telegram_upload': 'telegram-upload',
    'telegram_send': 'telegram-send',
    'telegram_text': 'telegram-text',
    'mtproto': 'telegram-mtproto',
    'tl': 'telethon',
    'telegram_utils': 'telegram-utils',
    'telegram_logger': 'telegram-logger',
    'telegram_handlers': 'python-telegram-handlers',
    'telegram_redis': 'telegram-redis',
    'telegram_sqlalchemy': 'telegram-sqlalchemy',
    'telegram_payment': 'telegram-payment',
    'telegram_shop': 'telegram-shop-sdk',
    'pytest_telegram': 'pytest-telegram',
    'telegram_debug': 'telegram-debug',
    'telegram_scraper': 'telegram-scraper',
    'telegram_analytics': 'telegram-analytics',
    'telegram_nlp': 'telegram-nlp-toogit',
    'telegram_ai': 'telegram-ai',
    'telegram_api': 'telegram-api-client',
    'telegram_web': 'telegram-web-integration',
    'telegram_games': 'telegram-games',
    'telegram_quiz': 'telegram-quiz-bot',
    'telegram_ffmpeg': 'telegram-ffmpeg',
    'telegram_media': 'telegram-media-utils',
    'telegram_2fa': 'telegram-twofa',
    'telegram_crypto': 'telegram-crypto-bot',
    'telegram_i18n': 'telegram-i18n',
    'telegram_translate': 'telegram-translate',
    'bs4': 'beautifulsoup4',
    'requests': 'requests',
    'pillow': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'flask': 'Flask',
    'django': 'Django',
    'sqlalchemy': 'SQLAlchemy',
    'asyncio': None,
    'json': None,
    'datetime': None,
    'os': None,
    'sys': None,
    're': None,
    'time': None,
    'math': None,
    'random': None,
    'logging': None,
    'threading': None,
    'subprocess':None,
    'zipfile':None,
    'tempfile':None,
    'shutil':None,
    'sqlite3':None,
    'psutil': 'psutil',
    'googletrans': 'googletrans',
    'atexit': None
}

def save_install_log(user_id, module_name, package_name, status, log):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            install_date = datetime.now().isoformat()
            c.execute('INSERT INTO install_logs (user_id, module_name, package_name, status, log, install_date) VALUES (?, ?, ?, ?, ?, ?)',
                      (user_id, module_name, package_name, status, log, install_date))
            conn.commit()
            logger.info(f"Saved install log for user {user_id}: {module_name} - {status}")
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error saving install log: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error saving install log: {e}", exc_info=True)
        finally:
            conn.close()

def attempt_install_pip(module_name, message, manual_request=False, retry=3):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name) 
    if package_name is None: 
        logger.info(f"Module '{module_name}' is core. Skipping pip install.")
        return False, "Core module - no installation needed"
    
    mirrors = [
        'https://pypi.org/simple',
        'https://mirrors.aliyun.com/pypi/simple/',
        'https://pypi.douban.com/simple/',
        'https://pypi.tuna.tsinghua.edu.cn/simple'
    ]
    
    for attempt in range(1, retry+1):
        try:
            if manual_request:
                bot.reply_to(message, f"🔄 Manual install attempt {attempt} for `{package_name}`...", parse_mode='Markdown')
            else:
                bot.reply_to(message, f"🐍 Installing `{package_name}` (attempt {attempt}/{retry})...", parse_mode='Markdown')
            
            if attempt == 1:
                command = [sys.executable, '-m', 'pip', 'install', package_name]
            else:
                mirror = mirrors[(attempt-1) % len(mirrors)]
                command = [sys.executable, '-m', 'pip', 'install', '-i', mirror, package_name]
            
            logger.info(f"Running install: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                log_msg = f"Installed {package_name} (attempt {attempt}). Output:\n{result.stdout}"
                logger.info(log_msg)
                success_msg = f"✅ Package `{package_name}` installed successfully (attempt {attempt})."
                bot.reply_to(message, success_msg, parse_mode='Markdown')
                save_install_log(message.from_user.id, module_name, package_name, "success", log_msg)
                return True, log_msg
            else:
                error_msg = f"❌ Attempt {attempt} failed for `{package_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
                logger.error(error_msg)
                if attempt == retry:
                    if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Log truncated)"
                    bot.reply_to(message, error_msg, parse_mode='Markdown')
                    save_install_log(message.from_user.id, module_name, package_name, "failed", error_msg)
                    return False, error_msg
                else:
                    time.sleep(2)
        except Exception as e:
            error_msg = f"❌ Error installing `{package_name}` (attempt {attempt}): {str(e)}"
            logger.error(error_msg, exc_info=True)
            if attempt == retry:
                bot.reply_to(message, error_msg)
                save_install_log(message.from_user.id, module_name, package_name, "error", error_msg)
                return False, error_msg
            time.sleep(2)
    return False, "All retry attempts failed."

def attempt_install_npm(module_name, user_folder, message, manual_request=False, retry=3):
    registries = [
        'https://registry.npmjs.org',
        'https://registry.npmmirror.com',
        'https://registry.yarnpkg.com'
    ]
    for attempt in range(1, retry+1):
        try:
            if manual_request:
                bot.reply_to(message, f"🔄 Manual npm install attempt {attempt} for `{module_name}`...", parse_mode='Markdown')
            else:
                bot.reply_to(message, f"🟠 Installing Node package `{module_name}` (attempt {attempt}/{retry})...", parse_mode='Markdown')
            
            registry = registries[(attempt-1) % len(registries)]
            command = ['npm', 'install', module_name, '--registry', registry]
            if attempt > 1:
                command.append('--legacy-peer-deps')
            logger.info(f"Running npm install: {' '.join(command)} in {user_folder}")
            result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                log_msg = f"Installed {module_name} (attempt {attempt}). Output:\n{result.stdout}"
                logger.info(log_msg)
                success_msg = f"✅ Node package `{module_name}` installed (attempt {attempt})."
                bot.reply_to(message, success_msg, parse_mode='Markdown')
                save_install_log(message.from_user.id, module_name, module_name, "success", log_msg)
                return True, log_msg
            else:
                error_msg = f"❌ Attempt {attempt} failed for Node package `{module_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
                logger.error(error_msg)
                if attempt == retry:
                    if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Log truncated)"
                    bot.reply_to(message, error_msg, parse_mode='Markdown')
                    save_install_log(message.from_user.id, module_name, module_name, "failed", error_msg)
                    return False, error_msg
                time.sleep(2)
        except FileNotFoundError:
            error_msg = "❌ Error: 'npm' not found. Ensure Node.js/npm are installed and in PATH."
            logger.error(error_msg)
            bot.reply_to(message, error_msg)
            save_install_log(message.from_user.id, module_name, module_name, "error", error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ Error installing Node package `{module_name}` (attempt {attempt}): {str(e)}"
            logger.error(error_msg, exc_info=True)
            if attempt == retry:
                bot.reply_to(message, error_msg)
                save_install_log(message.from_user.id, module_name, module_name, "error", error_msg)
                return False, error_msg
            time.sleep(2)
    return False, "All retry attempts failed."

def manual_install_module_init(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin. Try later.")
        return
    msg = bot.reply_to(message, "📦 Send module name to install (e.g., `requests` or `pillow`)\nFor Node.js: `npm:module_name`\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_manual_install_module)

def process_manual_install_module(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Installation cancelled.")
        return
    module_name = message.text.strip()
    if module_name.lower().startswith('npm:'):
        module_name = module_name[4:].strip()
        user_folder = get_user_folder(user_id)
        success, log = attempt_install_npm(module_name, user_folder, message, manual_request=True)
    else:
        success, log = attempt_install_pip(module_name, message, manual_request=True)
    if success:
        logger.info(f"User {user_id} manually installed module: {module_name}")

def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            # A normal single-file upload is its own project; clear any previous ZIP marker.
            if file_type != 'zip':
                marker = os.path.join(get_user_folder(user_id), ZIP_PROJECT_MARKER)
                if os.path.exists(marker):
                    _delete_path_force(marker)
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)',
                      (user_id, file_name, file_type))
            conn.commit()
            if user_id not in user_files: user_files[user_id] = []
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
            logger.info(f"Saved file '{file_name}' ({file_type}) for user {user_id}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error saving file for user {user_id}, {file_name}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error saving file for {user_id}, {file_name}: {e}", exc_info=True)
        finally: conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]: del user_files[user_id]
            logger.info(f"Removed file '{file_name}' for user {user_id} from DB")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error removing file for {user_id}, {file_name}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error removing file for {user_id}, {file_name}: {e}", exc_info=True)
        finally: conn.close()

def add_active_user(user_id):
    active_users.add(user_id) 
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            join_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO active_users (user_id, join_date, last_seen) VALUES (?, ?, ?)', 
                      (user_id, join_date, join_date))
            conn.commit()
            logger.info(f"Added/Updated active user {user_id} in DB")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error adding active user {user_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error adding active user {user_id}: {e}", exc_info=True)
        finally: conn.close()

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            expiry_str = expiry.isoformat()
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry_str))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
            logger.info(f"Saved subscription for {user_id}, expiry {expiry_str}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error saving subscription for {user_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error saving subscription for {user_id}: {e}", exc_info=True)
        finally: conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_subscriptions: del user_subscriptions[user_id]
            logger.info(f"Removed subscription for {user_id} from DB")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error removing subscription for {user_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error removing subscription for {user_id}: {e}", exc_info=True)
        finally: conn.close()

def add_admin_db(admin_id, added_by):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            added_date = datetime.now().isoformat()
            c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', 
                      (admin_id, added_by, added_date))
            conn.commit()
            admin_ids.add(admin_id) 
            logger.info(f"Added admin {admin_id} to DB by {added_by}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error adding admin {admin_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error adding admin {admin_id}: {e}", exc_info=True)
        finally: conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID:
        logger.warning("Attempted to remove OWNER_ID from admins.")
        return False 
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        removed = False
        try:
            c.execute('SELECT 1 FROM admins WHERE user_id = ?', (admin_id,))
            if c.fetchone():
                c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
                conn.commit()
                removed = c.rowcount > 0 
                if removed: admin_ids.discard(admin_id); logger.info(f"Removed admin {admin_id} from DB")
                else: logger.warning(f"Admin {admin_id} found but delete affected 0 rows.")
            else:
                logger.warning(f"Admin {admin_id} not found in DB.")
                admin_ids.discard(admin_id)
            return removed
        except sqlite3.Error as e: logger.error(f"❌ SQLite error removing admin {admin_id}: {e}"); return False
        except Exception as e: logger.error(f"❌ Unexpected error removing admin {admin_id}: {e}", exc_info=True); return False
        finally: conn.close()

# --- Menu creation functions ---
def create_main_menu_inline(user_id):
    """Premium Darkwest black-and-gold themed inline dashboard."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    gold = '◆'
    buttons = [
        types.InlineKeyboardButton('📣  Updates Channel', url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'),
        types.InlineKeyboardButton('📤  Upload Project', callback_data='upload'),
        types.InlineKeyboardButton('📁  My Files', callback_data='check_files'),
        types.InlineKeyboardButton('🌐  Live Status', callback_data='live_projects'),
        types.InlineKeyboardButton('⚡  Bot Speed', callback_data='speed'),
        types.InlineKeyboardButton('🧰  Manual Install', callback_data='manual_install'),
        types.InlineKeyboardButton('👑  Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    ]
    markup.row(buttons[0])
    markup.row(buttons[1], buttons[2])
    markup.row(buttons[3], buttons[4])
    if user_id in admin_ids:
        markup.row(
            types.InlineKeyboardButton('💳  Subscriptions', callback_data='subscription'),
            types.InlineKeyboardButton('📊  Statistics', callback_data='stats'))
        markup.row(
            types.InlineKeyboardButton('🔒  Lock Bot' if not bot_locked else '🔓  Unlock Bot',
                                       callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
            types.InlineKeyboardButton('📢  Broadcast', callback_data='broadcast'))
        markup.row(
            types.InlineKeyboardButton('👥  User Management', callback_data='user_management'),
            types.InlineKeyboardButton('📣  Channel Settings', callback_data='manage_mandatory_channels'))
        markup.row(
            types.InlineKeyboardButton('🛠️  Admin Install', callback_data='admin_install'),
            types.InlineKeyboardButton('⚙️  Settings', callback_data='admin_settings'))
        markup.row(types.InlineKeyboardButton('👑  Admin Control Center', callback_data='admin_panel'))
        markup.row(types.InlineKeyboardButton('▶️  Run All Projects', callback_data='run_all_scripts'))
    else:
        markup.row(types.InlineKeyboardButton('🧠  AI Fix Provider', callback_data='user_ai_provider_menu'))
        markup.row(types.InlineKeyboardButton('📊  My Statistics', callback_data='stats'))
    markup.row(buttons[5], buttons[6])
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout_to_use = ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC if user_id in admin_ids else COMMAND_BUTTONS_LAYOUT_USER_SPEC
    for row_buttons_text in layout_to_use:
        markup.add(*[types.KeyboardButton(text) for text in row_buttons_text])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Stop", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Start", callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("📜 View Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    markup.add(types.InlineKeyboardButton("🔎 Check Live", callback_data=f'live_{script_owner_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data='check_files'))
    return markup

def _load_welcome_media():
    try:
        with open(WELCOME_MEDIA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _save_welcome_media(data):
    os.makedirs(os.path.dirname(WELCOME_MEDIA_PATH), exist_ok=True)
    temp_path = WELCOME_MEDIA_PATH + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(temp_path, WELCOME_MEDIA_PATH)

def welcome_media_set_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, '📷 Ab welcome ke liye photo ya video bhejein. Cancel karne ke liye /cancel likhein.')
    bot.register_next_step_handler(msg, _receive_welcome_media)

def _receive_welcome_media(message):
    if message.from_user.id not in admin_ids:
        return
    if message.content_type == 'text' and (message.text or '').strip().lower() == '/cancel':
        bot.send_message(message.chat.id, '❎ Welcome media setup cancel kar diya.')
        return
    media = {}
    if message.photo:
        media = {'type': 'photo', 'file_id': message.photo[-1].file_id}
    elif message.video:
        media = {'type': 'video', 'file_id': message.video.file_id}
    else:
        msg = bot.send_message(message.chat.id, '❌ Sirf photo ya video bhejein. Dobara try karein ya /cancel likhein.')
        bot.register_next_step_handler(msg, _receive_welcome_media)
        return
    try:
        _save_welcome_media(media)
        bot.send_message(message.chat.id, '✅ Welcome photo/video set ho gayi! Ab har naye welcome ke saath dikhegi.', reply_markup=create_admin_panel())
    except Exception as e:
        logger.exception('Could not save welcome media: %s', e)
        bot.send_message(message.chat.id, '❌ Media save nahi ho saki.')

def welcome_media_delete_callback(call):
    bot.answer_callback_query(call.id)
    try:
        if os.path.exists(WELCOME_MEDIA_PATH):
            os.remove(WELCOME_MEDIA_PATH)
        bot.send_message(call.message.chat.id, '🗑️ Welcome photo/video delete ho gayi.', reply_markup=create_admin_panel())
    except Exception as e:
        logger.exception('Could not delete welcome media: %s', e)
        bot.send_message(call.message.chat.id, '❌ Media delete nahi ho saki.')

def create_admin_panel():
    """Premium Darkwest admin control center; callback IDs remain unchanged."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('🖼️  Set Welcome Media', callback_data='welcome_media_set'),
               types.InlineKeyboardButton('🗑️  Remove Welcome Media', callback_data='welcome_media_delete'))
    markup.row(types.InlineKeyboardButton('🤖  AI Auto-Fix', callback_data='ai_settings'),
               types.InlineKeyboardButton('🛡️  Approval System', callback_data='approval_settings'))
    markup.row(types.InlineKeyboardButton('➕  Add Admin', callback_data='add_admin'),
               types.InlineKeyboardButton('➖  Remove Admin', callback_data='remove_admin'))
    markup.row(types.InlineKeyboardButton('📋  Admin List', callback_data='list_admins'),
               types.InlineKeyboardButton('📁  All User Files', callback_data='all_files'))
    markup.row(types.InlineKeyboardButton('🧹  Delete Forwarded Files', callback_data='delete_forwarded_files'))
    markup.row(types.InlineKeyboardButton('⚠️  Clear All Data', callback_data='clear_all_data_confirm'))
    markup.row(types.InlineKeyboardButton('⬅️  Back to Dashboard', callback_data='back_to_main'))
    return markup

def create_user_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('🚫 Ban User', callback_data='ban_user'),
        types.InlineKeyboardButton('✅ Unban User', callback_data='unban_user')
    )
    markup.row(
        types.InlineKeyboardButton('📊 User Info', callback_data='user_info'),
        types.InlineKeyboardButton('👥 All Users', callback_data='all_users')
    )
    markup.row(
        types.InlineKeyboardButton('🔧 Set User Limit', callback_data='set_user_limit'),
        types.InlineKeyboardButton('🗑️ Remove User Limit', callback_data='remove_user_limit')
    )
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription'),
        types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription')
    )
    markup.row(types.InlineKeyboardButton('🔍 Check Subscription', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_admin_settings_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('🖥️ System Info', callback_data='system_info'),
        types.InlineKeyboardButton('📈 Performance', callback_data='bot_performance')
    )
    markup.row(
        types.InlineKeyboardButton('🧹 Cleanup Files', callback_data='cleanup_files'),
        types.InlineKeyboardButton('📋 Install Logs', callback_data='install_logs')
    )
    markup.row(types.InlineKeyboardButton('🖼️ Set Welcome Photo/Video', callback_data='welcome_media_set'),
               types.InlineKeyboardButton('🗑️ Delete Welcome Media', callback_data='welcome_media_delete'))
    markup.row(
        types.InlineKeyboardButton('🤖 AI Auto-Fix', callback_data='ai_settings'),
        types.InlineKeyboardButton('🧪 AI Testing', callback_data='ai_test')
    )
    markup.row(types.InlineKeyboardButton('🛡️ ZIP Approval', callback_data='approval_settings'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Admin Panel', callback_data='admin_panel'))
    return markup

def create_ai_settings_menu(user_id=None):
    user_id = int(user_id or OWNER_ID)
    status = '🟢 Enabled' if ai_settings.get('enabled', True) else '🔴 Disabled'
    provider = _friendly_ai_provider(_provider_for_user(user_id))
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton(f'AI: {status}', callback_data='ai_toggle'))
    markup.row(types.InlineKeyboardButton(f'🧠 AI Fix Provider: {provider}', callback_data='ai_provider_menu'))
    markup.row(types.InlineKeyboardButton('🔑 Set API Key', callback_data='ai_set_key'), types.InlineKeyboardButton('🧪 Test AI', callback_data='ai_test'))
    markup.row(types.InlineKeyboardButton('🤖 Direct Model', callback_data='ai_models'))
    markup.row(types.InlineKeyboardButton('◀️ Back', callback_data='admin_settings'))
    return markup

def create_ai_model_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    models = [
        ('🛠️ DeepSeek Chat (Coding)', 'deepseek/deepseek-chat'),
        ('🧩 Qwen3 Coder 480B', 'qwen/qwen3-coder-480b-a35b-instruct'),
        ('🧠 Direct AI Auto', 'openrouter/auto'),
        ('⚡ Direct AI Free', 'openrouter/free'),
        ('🔙 Back', 'ai_settings')
    ]
    for label, model in models:
        markup.add(types.InlineKeyboardButton(label + ('  ✓' if OPENROUTER_MODEL == model else ''), callback_data=f'ai_model_{model.replace("/", "__")}'))
    return markup

def create_approval_settings_menu():
    zip_state = '🟢 REQUIRED' if approval_settings.get('zip_requires_approval', True) else '⚡ AUTO-APPROVE'
    file_state = '🟢 REQUIRED' if approval_settings.get('file_requires_approval', True) else '⚡ AUTO-APPROVE'
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f'📦 ZIP Approval: {zip_state}', callback_data='toggle_zip_approval'))
    markup.add(types.InlineKeyboardButton(f'📄 File Approval: {file_state}', callback_data='toggle_file_approval'))
    markup.add(types.InlineKeyboardButton('🔙 Back', callback_data='admin_panel'))
    return markup

# ========== NEW AUTO-DETECT FUNCTION ==========

# _A2 is defined in the INTERNAL CACHE near the imports so OWNER_ID can be
# constructed safely before this function section is loaded.

def _detect_project_root(extracted_dir):
    """Find the actual project root even when the ZIP contains wrapper folders."""
    skip_dirs = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'vendor', '.cache', 'dist', 'build'
    }

    def score_root(files):
        names = {n.lower() for n in files}
        score = 0
        markers = (
            ('package.json', 100), ('composer.json', 90),
            ('requirements.txt', 80), ('procfile', 55),
            ('railway.json', 45), ('railway.toml', 45),
            ('runtime.txt', 30), ('package-lock.json', 20), ('pyproject.toml', 78), ('Pipfile', 60),
            ('pnpm-lock.yaml', 20), ('yarn.lock', 20),
            ('ecosystem.config.js', 18), ('pubspec.yaml', 70), ('Package.swift', 70), ('*.csproj', 50)
        )
        for marker, points in markers:
            if marker in names:
                score += points

        entry_names = {
            'index.js', 'main.js', 'bot.js', 'app.js', 'server.js', 'start.js',
            'index.mjs', 'main.mjs', 'bot.mjs', 'server.mjs',
            'main.py', 'bot.py', 'app.py', 'index.py',
            'index.php', 'main.php', 'app.php', 'server.php',
            'index.html', 'index.htm'
        }
        score += min(35, 7 * len(names & entry_names))
        score += min(15, sum(
            1 for n in names
            if n.endswith(('.js', '.mjs', '.cjs', '.py', '.php', '.html', '.htm'))
        ))
        return score

    candidates = []
    for root, dirs, files in os.walk(extracted_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(root, extracted_dir)
        depth = 0 if rel == '.' else rel.count(os.sep) + 1
        if depth > 6:
            dirs[:] = []
            continue
        score = score_root(files)
        if score:
            candidates.append((score, depth, root))

    if not candidates:
        return extracted_dir

    root_names = {n.lower() for n in os.listdir(extracted_dir)}
    root_markers = {
        'package.json', 'composer.json', 'requirements.txt', 'procfile',
        'railway.json', 'railway.toml', 'pubspec.yaml', 'Package.swift', 'index.js', 'main.js', 'bot.js',
        'app.js', 'server.js', 'main.py', 'bot.py', 'app.py', 'index.py',
        'index.php', 'main.php', 'index.html', 'index.htm'
    }
    if root_names & root_markers:
        return extracted_dir

    candidates.sort(key=lambda x: (-x[0], x[1], x[2].lower()))
    best_score, _, best_root = candidates[0]
    logger.info("Auto-detected nested project root: %s (score=%s)", best_root, best_score)
    return best_root


# Owner-only file sharing policy: actual uploads go to Owner only; Admins get review notifications/buttons.
# ========== ZIP UPLOAD HANDLER (FIXED) ==========
def handle_zip_file(file_content, file_name, message):
    """
    Save an uploaded ZIP to a temporary directory, run the same security/
    approval flow used by the rest of the hosting system, and process it.
    This function fixes the original NameError: handle_zip_file was called
    but was never defined.
    """
    user_id = message.from_user.id
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_upload_")
        zip_path = os.path.join(temp_dir, os.path.basename(file_name))

        with open(zip_path, "wb") as f:
            f.write(file_content)

        logger.info("ZIP saved for user %s: %s", user_id, zip_path)

        # Share the actual ZIP ONLY with the Owner. Admins must never receive
        # the uploaded ZIP/document itself; they only receive the review card
        # with Approve/Reject buttons below.
        try:
            forwarded_msg = bot.forward_message(
                OWNER_ID,
                message.chat.id,
                message.message_id
            )
            with forwarded_files_lock:
                forwarded_files.append({
                    "chat_id": OWNER_ID,
                    "message_id": forwarded_msg.message_id,
                    "file_name": file_name,
                    "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                save_forwarded_files(forwarded_files)
        except Exception as e:
            logger.error(
                "Failed to forward ZIP to Owner %s: %s",
                OWNER_ID,
                e,
                exc_info=True,
            )

        # Owner/admins are trusted by the existing security model.
        is_safe, security_msg = scan_zip_security(zip_path, user_id)

        if user_id not in TRUSTED_USERS and approval_settings.get('zip_requires_approval', True):
            # A security detection must NOT auto-reject the user's ZIP.
            # Keep the archive pending so Owner/Admins can review the detection
            # and explicitly Approve or Reject it.

            # Keep the bytes in memory until an admin approves the archive.
            if user_id not in pending_zip_files:
                pending_zip_files[user_id] = {}
            pending_zip_files[user_id][file_name] = bytes(file_content)

            # Build a detailed security-review card for Owner/Admins.
            detected_pattern = security_msg
            detected_target = file_name
            marker = "contains a blocked pattern:"
            if marker in security_msg:
                left, right = security_msg.split(marker, 1)
                detected_pattern = right.strip()
                if left.startswith("File "):
                    detected_target = left[5:].strip()

            security_reason = (
                "Potentially dangerous code/import detected by the security scanner."
                if not is_safe else
                "No blocked security pattern was detected by the scanner."
            )

            approval_text = (
                "🚨 SECURITY REVIEW REQUIRED\n\n"
                "👤 USER\n"
                f"├─ Name: @{getattr(message.from_user, 'username', None) or 'N/A'}\n"
                f"└─ ID: {user_id}\n\n"
                "📦 FILE INFORMATION\n"
                f"├─ Archive: {file_name}\n"
                f"└─ Target: {detected_target}\n\n"
                "🔍 SECURITY DETECTION\n"
                f"├─ Pattern: {detected_pattern}\n"
                f"└─ Reason: {security_reason}\n\n"
                "📋 REVIEW STATUS\n"
                "└─ ⏳ Pending OWNER / ADMIN Approval\n\n"
                "⚠️ ACTION REQUIRED\n"
                "The file has NOT been rejected automatically.\n"
                "OWNER/ADMIN review is required before processing.\n\n"
                "👑 OWNER / ADMIN DECISION"
            )

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton(
                    "✅ Approve",
                    callback_data=f"approve_zip_{user_id}_{file_name}"
                ),
                types.InlineKeyboardButton(
                    "❌ Reject",
                    callback_data=f"reject_zip_{user_id}_{file_name}"
                ),
            )

            review_recipients = set(admin_ids) | {OWNER_ID}

            for admin_id in review_recipients:
                try:
                    bot.send_message(
                        admin_id,
                        approval_text,
                        reply_markup=markup
                    )
                except Exception as e:
                    logger.error(
                        "Failed to send ZIP approval request to admin %s: %s",
                        admin_id,
                        e,
                        exc_info=True,
                    )

            bot.reply_to(
                message,
                "⏳ SECURITY REVIEW PENDING\n\n"
                "📦 Your ZIP has been received and is waiting for Owner/Admin approval.\n\n"
                f"📁 File: {file_name}\n"
                f"🔍 Security status: {security_msg}\n\n"
                "⚠️ The file has NOT been rejected automatically.\n"
                "You will receive an update after the review decision."
            )
            return

        # Trusted users can process immediately.
        bot.reply_to(message, "🔄 ZIP approved automatically. Processing...")
        process_zip_file(
            zip_path,
            user_id,
            get_user_folder(user_id),
            file_name,
            message,
            temp_dir
        )

    except zipfile.BadZipFile:
        logger.exception("Invalid ZIP uploaded by user %s", user_id)
        bot.reply_to(message, "❌ Invalid/corrupted ZIP archive.")
    except Exception as e:
        logger.exception("Error handling ZIP for user %s", user_id)
        bot.reply_to(message, f"❌ Unexpected error processing ZIP: {e}")
    finally:
        # process_zip_file moves the extracted files to the user's permanent
        # folder, so deleting this temporary directory is safe.
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(
                    "Failed to clean ZIP temp directory %s: %s",
                    temp_dir,
                    e,
                    exc_info=True,
                )


# ========== NODE PROJECT PREPARATION ==========

def _node_builtin_modules():
    return {
        'assert','assert/strict','async_hooks','buffer','child_process','cluster','console',
        'constants','crypto','dgram','diagnostics_channel','dns','dns/promises','domain',
        'events','fs','fs/promises','http','http2','https','module','net','os','path',
        'path/posix','path/win32','perf_hooks','process','punycode','querystring','readline',
        'readline/promises','repl','stream','stream/promises','stream/web','string_decoder',
        'sys','timers','timers/promises','tls','trace_events','tty','url','util',
        'util/types','v8','vm','wasi','worker_threads','zlib','inspector','test'
    }








# ========== UPDATED process_zip_file ==========

def _safe_replace_project(user_folder, temp_dir):
    """Replace project files atomically enough for a single-user hosting folder."""
    os.makedirs(user_folder, exist_ok=True)
    for name in os.listdir(user_folder):
        path_ = os.path.join(user_folder, name)
        try:
            if os.path.isdir(path_) and not os.path.islink(path_):
                shutil.rmtree(path_)
            else:
                os.remove(path_)
        except FileNotFoundError:
            pass
    for name in os.listdir(temp_dir):
        shutil.move(os.path.join(temp_dir, name), os.path.join(user_folder, name))


def _normalize_user_project_layout(user_folder, user_id):
    """Flatten accidental upload_bots/<user_id>/ nesting after ZIP deployment.

    A ZIP may itself contain an upload_bots/<user_id>/ wrapper.  The hosting
    service must never deploy that wrapper inside the already selected user
    folder, otherwise paths such as upload_bots/<id>/upload_bots/<id>/file.js
    are produced.
    """
    user_folder = os.path.abspath(user_folder)
    nested = os.path.join(user_folder, 'upload_bots', str(user_id))
    if not os.path.isdir(nested):
        return False

    # Only flatten when the nested tree is the obvious accidental wrapper.
    # Merge its contents into the real user folder and remove empty wrappers.
    moved = False
    for name in os.listdir(nested):
        src = os.path.join(nested, name)
        dst = os.path.join(user_folder, name)
        if os.path.exists(dst):
            # Never overwrite an existing deployed file silently.
            if os.path.isdir(src) and os.path.isdir(dst):
                for child in os.listdir(src):
                    shutil.move(os.path.join(src, child), os.path.join(dst, child))
                shutil.rmtree(src, ignore_errors=True)
            else:
                raise RuntimeError(f'Duplicate deployed path while flattening: {name}')
        else:
            shutil.move(src, dst)
        moved = True

    # Remove empty wrapper directories if they remain.
    try:
        wrapper_user = os.path.dirname(nested)
        if os.path.isdir(nested) and not os.listdir(nested):
            os.rmdir(nested)
        if os.path.isdir(wrapper_user) and not os.listdir(wrapper_user):
            os.rmdir(wrapper_user)
    except OSError:
        pass
    if moved:
        logger.warning('Flattened accidental nested project path: %s', nested)
    return moved




# --- run_npm_start (unchanged) ---

# --- run_script (fixed Markdown) ---

def auto_install_python_dependencies(script_path, message_obj_for_reply):
    """Fast, conservative dependency detection for uploaded Python projects.

    Declared requirements are handled by _install_project_dependencies(). This
    fallback only installs recognized common packages, in one pip invocation,
    instead of guessing a PyPI package for every imported module.
    """
    import ast

    package_map = {
        'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
        'aiogram': 'aiogram', 'pyrogram': 'pyrogram', 'telethon': 'telethon',
        'bs4': 'beautifulsoup4', 'PIL': 'Pillow', 'cv2': 'opencv-python',
        'dotenv': 'python-dotenv', 'yaml': 'PyYAML', 'dateutil': 'python-dateutil',
        'yt_dlp': 'yt-dlp', 'googletrans': 'googletrans',
        'playwright_stealth': 'playwright-stealth', 'playwright': 'playwright',
        'psutil': 'psutil', 'requests': 'requests', 'flask': 'Flask',
        'fastapi': 'fastapi', 'uvicorn': 'uvicorn[standard]',
        'aiohttp': 'aiohttp', 'httpx': 'httpx', 'websockets': 'websockets',
        'pandas': 'pandas', 'numpy': 'numpy', 'sqlalchemy': 'SQLAlchemy',
        'django': 'Django', 'pydub': 'pydub', 'moviepy': 'moviepy',
    }
    # Optional/platform-specific modules must not trigger speculative PyPI installs.
    skip_modules = {
        '__future__', 'builtins', 'sys', 'os', 're', 'json', 'time', 'math',
        'random', 'logging', 'threading', 'subprocess', 'zipfile', 'tempfile',
        'shutil', 'sqlite3', 'socket', 'signal', 'atexit', 'pathlib', 'datetime',
        'typing', 'collections', 'itertools', 'functools', 'traceback', 'asyncio',
        'abc', 'argparse', 'base64', 'hashlib', 'hmac', 'html', 'http', 'urllib',
        'email', 'csv', 'string', 'statistics', 'decimal', 'fractions', 'contextlib',
        'dataclasses', 'enum', 'inspect', 'io', 'glob', 'platform', 'CoreFoundation',
        'TestMac', 'lldb', '_manylinux', 'annotationlib', 'winloop',
    }

    script_path = os.path.abspath(script_path)
    user_folder = os.path.abspath(os.path.dirname(script_path))
    dep_dir = _python_dependency_dir(user_folder)
    try:
        Path(script_path).read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        logger.warning('Auto dependency scan skipped for %s: %s', script_path, exc)
        return True

    modules = set()
    for source_path in _iter_project_sources(user_folder, ('.py',)):
        try:
            tree = ast.parse(Path(source_path).read_text(encoding='utf-8', errors='ignore'),
                             filename=source_path)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module.split('.')[0])

    stdlib = set(getattr(sys, 'stdlib_module_names', set()))
    # Only use an explicit mapping. Guessing arbitrary PyPI names caused slow,
    # unnecessary installs for local modules and optional/platform-only imports.
    candidates = sorted(
        module for module in modules
        if module in package_map and module not in skip_modules and module not in stdlib
        and re.match(r'^[A-Za-z][A-Za-z0-9_]*$', module)
        and not _module_available_for_project(module, dep_dir)
    )
    packages = list(dict.fromkeys(package_map[module] for module in candidates))
    if not packages:
        logger.info('AUTO-INSTALL: no recognized missing Python dependencies.')
        return True

    logger.info('AUTO-INSTALL: installing recognized dependencies in one batch: %s', packages)
    try:
        result = _pip_install_isolated(
            packages, user_folder, user_folder, 'pip isolated batch install'
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or 'No pip output')[-1800:]
            logger.warning('AUTO-INSTALL batch failed: %s', details)
            try:
                bot.reply_to(
                    message_obj_for_reply,
                    '⚠️ Some automatically detected packages could not be installed. '
                    'Check requirements.txt and the project log. The script will still be attempted.',
                )
            except Exception:
                pass
    except Exception:
        logger.exception('AUTO-INSTALL batch exception')
    return True

def _html_escape(value):
    return (str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def _redact_for_ai(value):
    """Remove common credentials/tokens before sending logs to an external AI API."""
    s = str(value or '')
    patterns = [
        (r'(?i)(bot_token|api[_-]?key|authorization|token|password|secret)\s*[:=]\s*[^\s,;]+',
         r'\1=[REDACTED]'),
        (r'\b\d{8,12}:[A-Za-z0-9_-]{20,}\b', '[TELEGRAM_TOKEN_REDACTED]'),
        (r'\bsk-or-v1-[A-Za-z0-9_-]+\b', '[OPENROUTER_KEY_REDACTED]'),
        (r'\bsk-[A-Za-z0-9_-]{20,}\b', '[API_KEY_REDACTED]'),
    ]
    for pattern, repl in patterns:
        s = re.sub(pattern, repl, s)
    return s[-AUTO_REPAIR_LOG_CHARS:]


def _professional_error_card(message_obj, runtime, problem, action=''):
    lines = ['🛡️ <b>Darkwest AI Fixing</b>', '', f'⚙️ {_html_escape(runtime)}', f'❌ {_html_escape(_redact_for_ai(problem)[:700])}']
    if action:
        lines.append(f'🔧 {_html_escape(_redact_for_ai(action)[:700])}')
    try:
        _reply_temp_message(message_obj, '\n'.join(lines), parse_mode='HTML')
    except Exception:
        logger.exception('Could not send professional error card')


def _safe_dependency_name(name, runtime):
    """Allow package identifiers only; never execute an AI-provided shell command."""
    if not isinstance(name, str):
        return None
    name = name.strip()
    if not name or len(name) > 160:
        return None
    # Explicitly reject shell/control characters and URLs/paths.
    if any(ch in name for ch in (';', '&', '|', '`', '$', '\n', '\r', '>', '<')):
        return None
    if name.startswith(('./', '../', '/', 'http://', 'https://', 'git+')):
        return None

    if runtime == 'node':
        # npm package names, optionally with a version/range.
        if re.fullmatch(r'@?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?(?:@[A-Za-z0-9*^~<>=. -]+)?', name):
            return name
    elif runtime == 'python':
        # pip package name with an optional version/extras.
        if re.fullmatch(r'[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*\])?(?:[<>=!~]=?[A-Za-z0-9.*+!_-]+)?', name):
            return name
    elif runtime == 'php':
        if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?', name):
            return name
    return None


# --- Telegram/token error diagnostics (v12) ---
_TELEGRAM_BOT_TOKEN_RE = re.compile(r'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b')
_TOKEN_SCAN_EXTS = {'.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.php', '.json', '.env', '.txt', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'}
_TOKEN_SCAN_SKIP = {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'vendor', 'dist', 'build'}

def _token_error_diagnosis(log_text, project_dir=None):
    """Classify Telegram-style token failures without exposing the token itself.

    A valid replacement token can never be invented safely. This helper therefore
    diagnoses formatting/auth/conflict states and only supplies redacted facts to AI.
    """
    text = str(log_text or '')
    low = text.lower()
    diagnosis = None
    if re.search(r'\b401\b|unauthorized|invalid\s+(?:bot\s+)?token|token\s+is\s+invalid|bad\s+token', low):
        diagnosis = {
            'category': 'token',
            'problem': 'Telegram returned 401 Unauthorized / invalid bot token.',
            'action': 'Verify the bot token, remove accidental whitespace/quotes, and use a valid current token. A replacement token must come from the bot owner; AI will not invent one.',
            'confidence': 0.99,
        }
    elif re.search(r'\b409\b|conflict.*getupdates|terminated by other getupdates|another.*getupdates|already running.*bot', low, re.I):
        diagnosis = {
            'category': 'token_conflict',
            'problem': 'Telegram reported a 409 Conflict, usually indicating the same bot token is being polled by another bot process/instance.',
            'action': 'Stop the duplicate bot instance or use a different valid bot token. The repair system will not silently copy, generate, or revoke tokens.',
            'confidence': 0.99,
        }
    elif re.search(r'\b404\b.*(?:not found|bad request)|not found.*(?:bot|token|api)|(?:bot|token).*format.*wrong|invalid.*telegram.*url', low, re.I):
        diagnosis = {
            'category': 'token_format',
            'problem': 'Telegram/API returned a 404-style endpoint or token-format error.',
            'action': 'Check the Telegram API URL and token formatting. AI may prepare a validated config/source correction when the exact malformed URL/config is visible.',
            'confidence': 0.93,
        }
    elif re.search(r'\b403\b|forbidden|bot was blocked|bot is banned|kicked from|revoked', low, re.I):
        diagnosis = {
            'category': 'token_forbidden',
            'problem': 'Telegram returned 403 Forbidden or a blocked/revoked access condition.',
            'action': 'Verify whether the bot is blocked/banned in the target chat or whether access/token status changed. AI cannot bypass Telegram restrictions or invent a replacement credential.',
            'confidence': 0.95,
        }
    elif re.search(r'(?:token|bot[_ -]?token).*(?:missing|not set|unset|required|empty)|(?:missing|no)\s+(?:telegram\s+)?token', low, re.I):
        diagnosis = {
            'category': 'token_missing',
            'problem': 'A required Telegram bot token is missing, empty, or not loaded from configuration.',
            'action': 'Load a valid bot token from the intended environment/config source. AI may fix a clearly broken token-loading expression, but it will not fabricate credentials.',
            'confidence': 0.99,
        }

    if diagnosis and project_dir:
        conflict = _scan_token_conflicts(project_dir)
        if conflict.get('duplicate'):
            diagnosis['category'] = 'token_conflict'
            diagnosis['problem'] += f" Detected the same token fingerprint in {conflict['locations']} project location(s); token value is intentionally hidden."
            diagnosis['action'] = 'Resolve the duplicate-token ownership/process conflict before restarting. Do not copy one user\'s credential into another user\'s project.'
            diagnosis['confidence'] = max(float(diagnosis.get('confidence', 0.0)), 0.99)
    return diagnosis


def _extract_token_from_file(file_path):
    """Extract the first Telegram bot token from one project file, or None.

    This is intentionally narrow: it only recognizes Telegram bot-token syntax and
    never returns a token in user-facing diagnostics. Callers should fingerprint it
    immediately when comparing projects.
    """
    try:
        path = os.path.abspath(str(file_path))
        if not os.path.isfile(path) or Path(path).suffix.lower() not in _TOKEN_SCAN_EXTS:
            return None
        if os.path.getsize(path) > 2 * 1024 * 1024:
            return None
        raw = Path(path).read_text(encoding='utf-8', errors='ignore')
        match = _TELEGRAM_BOT_TOKEN_RE.search(raw)
        return match.group(0) if match else None
    except (OSError, UnicodeError):
        return None


def _token_project_owner_key(project_dir):
    """Resolve the actual hosting user from normal or nested upload_bots paths."""
    try:
        parts = Path(os.path.abspath(project_dir)).parts
        indexes = [i for i, part in enumerate(parts) if part == 'upload_bots']
        if indexes:
            i = indexes[-1]
            if i + 1 < len(parts) and parts[i + 1]:
                return str(parts[i + 1])
    except Exception:
        pass
    return os.path.basename(os.path.abspath(project_dir))


def _check_token_collision_before_start(project_dir, user_id, file_path=None, message_obj_for_reply=None):
    """Block a project before launch when its Telegram token belongs to another user.

    Same-token files belonging to the same hosting user are allowed. Different-user
    matches are blocked before subprocess.Popen/npm start so one user's project
    cannot knowingly start with another user's bot token.
    """
    project_dir = os.path.abspath(project_dir)
    user_key = str(user_id)
    cache_key = (user_key, project_dir)
    now = time.time()
    with _TOKEN_CACHE_LOCK:
        cached = _TOKEN_COLLISION_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _TOKEN_COLLISION_CACHE_TTL:
            return dict(cached[1])
    candidates = []
    if file_path:
        candidates.append(os.path.abspath(str(file_path)))
    try:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in _TOKEN_SCAN_SKIP]
            for name in files:
                path = os.path.abspath(os.path.join(root, name))
                if path not in candidates and Path(name).suffix.lower() in _TOKEN_SCAN_EXTS:
                    candidates.append(path)
                if len(candidates) >= 200:
                    break
            if len(candidates) >= 200:
                break
    except OSError:
        pass

    token_fingerprints = set()
    for path in candidates:
        token = _extract_token_from_file(path)
        if token:
            token_fingerprints.add(hashlib.sha256(token.encode('utf-8')).hexdigest()[:16])
    if not token_fingerprints:
        result = {'ok': True, 'found': False, 'collision': False}
        with _TOKEN_CACHE_LOCK:
            _TOKEN_COLLISION_CACHE[cache_key] = (time.time(), result)
        return result

    hosting_root = os.path.abspath(UPLOAD_BOTS_DIR)
    other_owners = set()
    matched_paths = []
    seen = set()
    try:
        for root, dirs, files in os.walk(hosting_root):
            dirs[:] = [d for d in dirs if d not in _TOKEN_SCAN_SKIP]
            for name in files:
                path = os.path.abspath(os.path.join(root, name))
                if path in seen or Path(name).suffix.lower() not in _TOKEN_SCAN_EXTS:
                    continue
                seen.add(path)
                token = _extract_token_from_file(path)
                if not token:
                    continue
                fp = hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]
                if fp not in token_fingerprints:
                    continue
                owner = _token_project_owner_key(os.path.dirname(path))
                if str(owner) != user_key:
                    other_owners.add(str(owner))
                    matched_paths.append(path)
    except OSError:
        pass

    if not other_owners:
        result = {'ok': True, 'found': True, 'collision': False}
        with _TOKEN_CACHE_LOCK:
            _TOKEN_COLLISION_CACHE[cache_key] = (time.time(), result)
        return result

    logger.warning('Token collision blocked before start: user=%s other_owners=%s', user_key, sorted(other_owners))
    if message_obj_for_reply is not None:
        try:
            bot.reply_to(
                message_obj_for_reply,
                '🛑 <b>Start blocked</b>\n\n'
                'The Telegram bot token found in this project is already used by another hosted user.\n'
                'The token value is hidden for security. Use the correct bot token for this project, then start again.',
                parse_mode='HTML'
            )
        except Exception:
            logger.debug('Could not send token-collision notice', exc_info=True)
    return {
        'ok': False,
        'found': True,
        'collision': True,
        'owners': sorted(other_owners),
        'locations': len(matched_paths),
    }


def _scan_token_conflicts(project_dir):
    """Find duplicate Telegram bot-token fingerprints without returning token values."""
    roots = []
    try:
        root = os.path.abspath(project_dir)
        if os.path.isdir(root):
            roots.append(root)
        hosting_root = os.path.abspath(UPLOAD_BOTS_DIR)
        if os.path.isdir(hosting_root) and hosting_root not in roots:
            roots.append(hosting_root)
    except Exception:
        roots = []
    fingerprints = {}
    seen_files = set()
    for base in roots:
        try:
            for r, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in _TOKEN_SCAN_SKIP]
                for name in files:
                    path = os.path.abspath(os.path.join(r, name))
                    if path in seen_files or Path(name).suffix.lower() not in _TOKEN_SCAN_EXTS:
                        continue
                    seen_files.add(path)
                    try:
                        if os.path.getsize(path) > 2 * 1024 * 1024:
                            continue
                        raw = Path(path).read_text(encoding='utf-8', errors='ignore')
                    except (OSError, UnicodeError):
                        continue
                    for token in set(_TELEGRAM_BOT_TOKEN_RE.findall(raw)):
                        fp = hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]
                        # Track the owning top-level project/user as well as the
                        # file. Multiple files inside one user's project are not
                        # an A-user/B-user token conflict.
                        try:
                            hosting_root = os.path.abspath(UPLOAD_BOTS_DIR)
                            rel = os.path.relpath(path, hosting_root).replace('\\', '/')
                            owner_root = rel.split('/', 1)[0] if not rel.startswith('..') else os.path.dirname(path)
                        except Exception:
                            owner_root = os.path.dirname(path)
                        entry = fingerprints.setdefault(fp, {'paths': set(), 'owners': set()})
                        entry['paths'].add(path)
                        entry['owners'].add(owner_root)
        except OSError:
            continue
    duplicate_locations = 0
    duplicate_owners = set()
    for entry in fingerprints.values():
        owners = entry.get('owners', set())
        if len(owners) > 1:
            duplicate_locations += len(entry.get('paths', set()))
            duplicate_owners.update(owners)
    return {'duplicate': len(duplicate_owners) > 1, 'locations': len(duplicate_owners)}

def _fallback_dependency_from_error(runtime, log_text):
    """Deterministic fallback when OpenRouter is unavailable or returns unusable JSON."""
    s = str(log_text or '')
    if runtime == 'python':
        # A missing symbol inside an installed package is a source/API mismatch,
        # not necessarily a missing pip dependency. Let the code-patch flow handle it.
        missing_symbol = re.search(
            r"cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]",
            s, re.I
        )
        if missing_symbol:
            symbol, module = missing_symbol.groups()
            return None, f"ImportError: '{symbol}' is not exported by '{module}'. Check the import and all usages in the source file."
        m = re.search(r"No module named ['\"]([^'\"]+)['\"]", s)
        if m:
            module = m.group(1).split('.')[0]
            mapping = {
                'telebot': 'pyTelegramBotAPI', 'bs4': 'beautifulsoup4',
                'PIL': 'Pillow', 'cv2': 'opencv-python',
                'dotenv': 'python-dotenv', 'yaml': 'PyYAML',
                'yt_dlp': 'yt-dlp', 'dateutil': 'python-dateutil',
                'googletrans': 'googletrans', 'flask': 'Flask',
                'fastapi': 'fastapi', 'uvicorn': 'uvicorn[standard]',
                'aiohttp': 'aiohttp', 'httpx': 'httpx',
                'websockets': 'websockets', 'pydub': 'pydub',
                'moviepy': 'moviepy', 'psutil': 'psutil',
            }
            return mapping.get(module, module.replace('_', '-')), f"Python module '{module}' is missing."
    if runtime == 'node':
        patterns = [
            r"Cannot find module ['\"]([^'\"]+)['\"]",
            r"ERR_MODULE_NOT_FOUND.*?['\"]([^'\"]+)['\"]",
        ]
        for p in patterns:
            m = re.search(p, s, re.I | re.S)
            if m:
                mod = m.group(1)
                if mod.startswith('.') or mod.startswith('/'):
                    return None, f"Local Node file/module '{mod}' is missing."
                return mod, f"Node package '{mod}' is missing."
    if runtime == 'php':
        m = re.search(r"class ['\"]([^'\"]+)['\"] not found", s, re.I)
        if m:
            return None, f"PHP class '{m.group(1)}' is missing; Composer diagnosis is required."
    return None, "The project exited with an error, but no safe dependency name could be inferred."


def _save_error_to_history(user_id, file_name, error_type, error_text, fix_applied=None):
    """Persist a small, redacted per-user error history for future AI context."""
    try:
        history_path = os.path.join(IROTECH_DIR, 'error_history.json')
        os.makedirs(os.path.dirname(history_path) or '.', exist_ok=True)
        lock = globals().get('_error_history_lock')
        if lock is None:
            lock = threading.Lock()
            globals()['_error_history_lock'] = lock
        with lock:
            try:
                data = json.loads(Path(history_path).read_text(encoding='utf-8', errors='ignore')) if os.path.isfile(history_path) else {}
            except Exception:
                data = {}
            if not isinstance(data, dict): data = {}
            key = str(user_id)
            entries = data.get(key, [])
            if not isinstance(entries, list): entries = []
            entries.append({'file_name': os.path.basename(str(file_name)), 'error_type': str(error_type)[:80],
                           'error_text': _redact_for_ai(str(error_text or ''))[:500],
                           'fix_applied': str(fix_applied or '')[:200], 'timestamp': datetime.now().isoformat()})
            data[key] = entries[-50:]
            tmp = history_path + '.tmp'
            Path(tmp).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(tmp, history_path)
    except Exception:
        logger.debug('Could not save error history', exc_info=True)


def _build_rich_error_context(user_id, file_name, user_folder, runtime, current_error):
    """Build bounded, redacted project context for diagnosis and repair prompts."""
    parts = ["CURRENT ERROR / LOG:\n" + _redact_for_ai(str(current_error or '')[-AUTO_REPAIR_LOG_CHARS:])]
    try:
        root = os.path.realpath(os.path.abspath(user_folder))
        names = []
        for walk_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
            for name in files:
                full = os.path.realpath(os.path.join(walk_root, name))
                if full.startswith(root + os.sep):
                    names.append(os.path.relpath(full, root))
                    if len(names) >= 40:
                        break
            if len(names) >= 40:
                break
        if names:
            parts.append("PROJECT FILES (first 40):\n" + "\n".join(names))
    except Exception:
        logger.debug('Could not build project file context', exc_info=True)
    try:
        history_path = os.path.join(IROTECH_DIR, 'error_history.json')
        if os.path.isfile(history_path):
            data = json.loads(Path(history_path).read_text(encoding='utf-8', errors='ignore'))
            recent = data.get(str(user_id), [])[-3:] if isinstance(data, dict) else []
            if recent:
                parts.append("RECENT ERROR HISTORY:\n" + "\n".join(
                    f"- {str(x.get('error_type','?'))}: {str(x.get('error_text',''))[:220]}"
                    for x in recent if isinstance(x, dict)))
    except Exception:
        pass
    try:
        log_path = os.path.join(user_folder, f"{os.path.splitext(os.path.basename(file_name))[0]}.log")
        if os.path.isfile(log_path):
            tail = Path(log_path).read_text(encoding='utf-8', errors='ignore')[-2500:]
            parts.append("LOG TAIL:\n" + _redact_for_ai(tail))
    except Exception:
        pass
    return "\n\n".join(parts)[:12000]


def _openrouter_diagnose_dependency_error(runtime, project_dir, log_text, user_id=None):
    """Broad AI diagnosis for dependency, syntax, runtime and startup failures.

    The function keeps the old name for compatibility, but it is no longer
    limited to dependency errors. It only *diagnoses* here; source changes and
    package installs still require the owner approval card.
    """
    if not ai_settings.get('enabled', True):
        return _token_error_diagnosis(log_text, project_dir)
    token_diag = _token_error_diagnosis(log_text, project_dir)
    source_hint = ''
    try:
        candidates = []
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
            for name in files:
                if Path(name).suffix.lower() in {'.py', '.js', '.mjs', '.cjs', '.php', '.ts', '.tsx'}:
                    candidates.append(os.path.join(root, name))
                    if len(candidates) >= 8:
                        break
            if len(candidates) >= 8:
                break
        if candidates:
            source_hint = '\n'.join(os.path.basename(x) for x in candidates)
    except Exception:
        source_hint = ''
    rich_context = _build_rich_error_context(user_id, os.path.basename(str(project_dir)), project_dir, runtime, log_text)
    prompt = f"""
You are the production debugger for a private hosting platform.
Runtime: {runtime}
Project directory: {project_dir}
Possible source files: {source_hint}
Token diagnostic hint: {token_diag or 'none'}

Analyze the startup/crash log and determine the DIRECT cause. This is a general
bug debugger, not only a dependency detector. Handle syntax errors, parse
errors, NameError/ReferenceError, TypeError, AttributeError, ImportError,
missing modules/packages, undefined variables/functions, bad arguments,
configuration mistakes, JSON errors, async/runtime errors, and other concrete
startup failures when evidence is present.

Return ONLY valid JSON:
{{
  "category": "syntax|dependency|name_error|type_error|attribute_error|import_error|config|token|token_conflict|token_format|token_forbidden|token_missing|runtime|other",
  "problem": "short factual explanation",
  "packages": [],
  "confidence": 0.0,
  "error_line": 0,
  "action": "short factual repair plan"
}}

Rules:
- Diagnose the reported error, not unrelated hypothetical bugs.
- packages must contain ONLY safe package-manager distribution names and ONLY
  when the log actually shows a missing dependency/module.
- For a code bug, return packages=[] so the source-fix stage can prepare an
  exact patch and show it for approval.
- Telethon ImportError guidance: if the log says "cannot import name X from
  telethon.tl.types", classify as import_error (not automatically dependency).
  Inspect the installed Telethon version and actual API; do NOT assume that
  KeyboardButtonCallback or other TL schema classes were removed. If evidence
  confirms the code should use telethon.tl.custom.Button, patch the import AND
  all affected constructions (for example Button.inline(text, data) or
  Button.url(text, url)), then validate the full file. Otherwise report the
  exact incompatible/missing symbol without guessing.
- Library/API migration guidance: for Telethon, aiogram, python-telegram-bot, discord.py,
  and similar libraries, check the installed version and the exact failing symbol/API
  from traceback/source evidence. Prefer a minimal code migration that preserves behavior;
  do not blindly upgrade/install packages to mask an ImportError. If package version
  evidence is unavailable, state uncertainty and request a reviewable code patch.
- Never return shell commands, credentials, tokens, destructive actions, or
  instructions to bypass authentication/approval.
- Maximum 5 packages.
- If evidence is insufficient, use category=other, packages=[], confidence<=0.3.
STARTUP/CRASH LOG:
{_redact_for_ai(log_text)}

ADDITIONAL REDACTED CONTEXT:
{rich_context}
"""
    content = call_ai_provider(int(user_id or 0), prompt)
    if not content or content == 'AI service temporarily unavailable':
        fallback_pkg, fallback_problem = _fallback_dependency_from_error(runtime, log_text)
        if fallback_pkg:
            return {
                'category': 'dependency',
                'problem': fallback_problem[:1000],
                'packages': [fallback_pkg],
                'confidence': 0.99,
                'error_line': _extract_error_location(log_text) or 0,
                'action': 'Install the dependency identified directly from the runtime error and retry after owner approval.'
            }
        return None
    try:
        match = re.search(r'\{.*\}', _strip_think_tags(content), re.S)
        if not match:
            return None
        result = json.loads(match.group(0))
        if not isinstance(result, dict):
            return None
        packages = []
        for pkg in result.get('packages', [])[:5]:
            safe = _safe_dependency_name(str(pkg), runtime)
            if safe:
                packages.append(safe)
        category = str(result.get('category') or 'other').strip().lower()
        allowed_categories = {'syntax','dependency','name_error','type_error','attribute_error','import_error','config','token','token_conflict','token_format','token_forbidden','token_missing','runtime','other'}
        if category not in allowed_categories:
            category = 'other'
        result['category'] = category
        result['packages'] = list(dict.fromkeys(packages))
        result['problem'] = str(result.get('problem') or 'Startup/runtime error')[:1200]
        result['action'] = str(result.get('action') or 'Prepare a targeted source repair after reviewing the traceback.')[:1500]
        try:
            result['confidence'] = max(0.0, min(1.0, float(result.get('confidence', 0.0) or 0.0)))
        except Exception:
            result['confidence'] = 0.0
        try:
            result['error_line'] = int(result.get('error_line') or _extract_error_location(log_text) or 0)
        except Exception:
            result['error_line'] = _extract_error_location(log_text) or 0
        return result
    except Exception as exc:
        logger.warning('AI general diagnosis parsing failed: %s', exc)
        return None


def _install_ai_packages(runtime, project_dir, packages):
    """Install only validated package identifiers with the correct package manager."""
    packages = [p for p in (_safe_dependency_name(x, runtime) for x in packages) if p]
    packages = list(dict.fromkeys(packages))[:5]
    if not packages:
        return False, "No safe package was identified."

    if runtime == 'python':
        # User-project packages must be installed into that project's isolated
        # .hosting_packages directory. --target + --upgrade can leave files from
        # an older package version behind, so remove only the named package's
        # import directory and metadata before reinstalling it.
        dep_dir = _python_dependency_dir(project_dir)
        try:
            if any(str(p).lower().replace('_', '-') == 'telethon' for p in packages):
                stale_paths = [os.path.join(dep_dir, 'telethon')]
                for pattern in ('telethon-*.dist-info', 'Telethon-*.dist-info',
                                'telethon-*.egg-info', 'Telethon-*.egg-info'):
                    stale_paths.extend(glob.glob(os.path.join(dep_dir, pattern)))
                for stale in dict.fromkeys(stale_paths):
                    if os.path.isdir(stale) and not os.path.islink(stale):
                        shutil.rmtree(stale)
                    elif os.path.lexists(stale):
                        os.remove(stale)
            result = _pip_install_isolated(
                ['--upgrade', '--force-reinstall', *packages],
                project_dir, project_dir, 'AI auto-fix pip', timeout=900
            )
        except Exception as exc:
            return False, str(exc)
        if result.returncode != 0:
            return False, (result.stderr or result.stdout or 'Isolated package installation failed')[-1800:]

        # Verify the exact import against the same .hosting_packages path used
        # by the hosted child. Do not report success merely because pip exited 0.
        if any(str(p).lower().replace('_', '-') == 'telethon' for p in packages):
            # Verify the installed distribution itself. Specific TL symbols are
            # validated by _python_import_precheck against the project's actual
            # source imports, avoiding false install failures from hard-coded names.
            verify_code = (
                'import telethon; '
                'print(getattr(telethon, "__version__", "version-unknown")); '
                'print(telethon.__file__)'
            )
            env = os.environ.copy()
            env['PYTHONPATH'] = dep_dir + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
            env['PYTHONNOUSERSITE'] = '1'
            try:
                check = subprocess.run(
                    [sys.executable, '-c', verify_code], cwd=project_dir, env=env,
                    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
                )
            except Exception as exc:
                return False, f"Installed Telethon but verification could not run: {exc}"
            if check.returncode != 0:
                detail = (check.stderr or check.stdout or 'Telethon import verification failed')[-1400:]
                return False, 'Package installation finished, but the hosted import still fails.\n' + detail
            return True, f"Telethon installed and verified in project environment:\n{(check.stdout or '').strip()}\n{(result.stdout or '')[-500:]}"
        return True, f"Installed in project environment: {', '.join(packages)}\n{(result.stdout or '')[-1000:]}"
    elif runtime == 'node':
        cmd = ['npm', 'install', '--no-audit', '--no-fund', *packages]
        label = 'npm'
    elif runtime == 'php':
        composer = shutil.which('composer')
        if not composer:
            return False, 'Composer is not installed on the hosting server.'
        cmd = [composer, 'require', '--no-interaction', *packages]
        label = 'composer'
    else:
        return False, f'Unsupported runtime: {runtime}'

    try:
        result = _run_checked(cmd, project_dir, f'AI auto-fix {label}', timeout=900)
    except Exception as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, f"Installed: {', '.join(packages)}"
    return False, (result.stderr or result.stdout or 'Package installation failed')[-1800:]


def _runtime_from_type(file_type):
    return {
        'py': 'python',
        'js': 'node',
        'npm': 'node',
        'php': 'php',
        'static': 'static',
    }.get(file_type, 'unknown')


def _strip_think_tags(text):
    cleaned = re.sub(r'<think>.*?</think>', '', str(text or ''), flags=re.I | re.S)
    return cleaned.strip()


def _friendly_ai_provider(provider):
    return AI_PROVIDER_NAMES.get(provider, AI_PROVIDER_NAMES[AI_PROVIDER_DEFAULT])


def _provider_for_user(user_id):
    value = str(user_ai_provider.get(str(user_id), user_ai_provider.get(user_id, AI_PROVIDER_DEFAULT))).strip().lower()
    return value if value in AI_PROVIDER_NAMES else AI_PROVIDER_DEFAULT


def _set_global_ai_provider(provider):
    """Set the bot-wide default provider and persist it for future restarts."""
    global AI_PROVIDER_DEFAULT
    provider = str(provider or '').strip().lower()
    if provider not in AI_PROVIDER_NAMES:
        return False
    AI_PROVIDER_DEFAULT = provider
    ai_settings['default_provider'] = provider
    return _save_json_settings(AI_SETTINGS_PATH, ai_settings)


def create_ai_provider_menu():
    return create_ai_provider_menu_for_user(OWNER_ID)


def create_ai_provider_menu_for_user(user_id):
    current = _provider_for_user(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    is_admin = int(user_id) in {int(ADMIN_ID), int(OWNER_ID)}
    callback_prefix = 'ai_provider_' if is_admin else 'user_ai_provider_select_'
    for label, provider in [('💀 WormGPT','wormgpt'), ('⚡ DeepSeek V4','deepseek'), ('🧠 Qwen LLM','qwen'), ('🔀 Direct AI','router')]:
        markup.add(types.InlineKeyboardButton(
            label + (' ✓' if provider == current else ''),
            callback_data=f'{callback_prefix}{provider}'
        ))
    markup.add(types.InlineKeyboardButton('◀️ Back', callback_data='ai_settings'))
    return markup


def call_ai_provider(user_id, prompt):
    provider = _provider_for_user(user_id)
    prompt = _redact_for_ai(prompt)
    if not ai_settings.get('enabled', True):
        return 'AI service temporarily unavailable'
    try:
        if provider == 'router':
            result = _openrouter_request([
                {'role': 'system', 'content': 'Return a concise, safe, factual coding diagnosis. Follow the requested output format exactly.'},
                {'role': 'user', 'content': prompt}
            ], max_tokens=1800, temperature=0)
            if result:
                _last_ai_provider_used[int(user_id)] = 'router'
                return result.strip()
        else:
            response = requests.get(AI_PROVIDER_ENDPOINTS[provider], params={'prompt': prompt}, timeout=60)
            response.raise_for_status()
            data = response.json()
            text = data.get('answer') if provider == 'wormgpt' else data.get('response')
            text = _strip_think_tags(text)
            if text:
                _last_ai_provider_used[int(user_id)] = provider
                return text
    except Exception as exc:
        logger.warning('Selected AI provider failed for user %s: %s', user_id, exc)
    # Silent fallback to the existing direct AI route.
    if provider != 'router':
        try:
            result = _openrouter_request([
                {'role': 'system', 'content': 'Return a concise, safe, factual coding diagnosis. Follow the requested output format exactly.'},
                {'role': 'user', 'content': prompt}
            ], max_tokens=1800, temperature=0)
            if result:
                _last_ai_provider_used[int(user_id)] = 'router'
                return result.strip()
        except Exception as exc:
            logger.warning('Direct AI fallback failed for user %s: %s', user_id, exc)
    return 'AI service temporarily unavailable'


def ai_provider_select_callback(call):
    provider = call.data[len('ai_provider_'):].strip().lower()
    if provider not in AI_PROVIDER_NAMES:
        bot.answer_callback_query(call.id, 'Unsupported AI provider', show_alert=True)
        return
    # Admin/Owner selection changes the bot-wide default provider.
    # Existing explicit per-user choices are preserved, while everyone without
    # an override automatically follows this new default.
    if not _set_global_ai_provider(provider):
        bot.answer_callback_query(call.id, 'Could not save provider', show_alert=True)
        return
    user_ai_provider[str(call.from_user.id)] = provider
    _save_json_settings(AI_PROVIDER_SETTINGS_PATH, user_ai_provider)
    bot.answer_callback_query(call.id, f'Default provider: {AI_PROVIDER_NAMES[provider]}')
    text = (f'🛡️ <b>Darkwest AI Fixing</b>\n\n'
            f'Global Default: <b>{_html_escape(AI_PROVIDER_NAMES[provider])}</b>\n'
            'Select your AI engine:')
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=create_ai_provider_menu_for_user(call.from_user.id), parse_mode='HTML')

def _openrouter_request(messages, max_tokens=1200, temperature=0):
    """Call OpenRouter robustly, with model fallbacks and useful diagnostics."""
    api_key = re.sub(r"\s+", "", str(OPENROUTER_API_KEY or "").strip().strip('`').replace('`', ''))
    if (not api_key or api_key == 'PASTE_NEW_OPENROUTER_API_KEY_HERE'
            or not ai_settings.get('enabled', True)):
        logger.warning('OpenRouter AI is disabled or has no usable API key.')
        return None

    primary = str(OPENROUTER_MODEL or '').strip()
    models = []
    for model in [primary] + list(OPENROUTER_FALLBACK_MODELS):
        model = str(model or '').strip()
        if model and model not in models:
            models.append(model)
    models = models[:4]
    if not models:
        models = ['openrouter/auto']

    base_payload = {
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://openrouter.ai/',
        'X-Title': 'Darkwest Hosting AI Auto-Fix',
    }

    # First use OpenRouter's native model-fallback routing.
    payload = dict(base_payload)
    payload['models'] = models
    try:
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
        if response.ok:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if isinstance(content, list):
                content = ''.join(part.get('text', '') if isinstance(part, dict) else str(part) for part in content)
            content = str(content or '').strip()
            if content:
                return content
        else:
            body = response.text[:1200]
            logger.warning('OpenRouter fallback request failed HTTP %s: %s', response.status_code, body)
    except Exception as exc:
        logger.warning('OpenRouter fallback request exception: %s', exc)

    # If a deployment rejects the models-array shape, retry one model at a time.
    for model in models:
        try:
            payload = dict(base_payload)
            payload['model'] = model
            response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
            if not response.ok:
                logger.warning('OpenRouter model %s failed HTTP %s: %s', model, response.status_code, response.text[:900])
                continue
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if isinstance(content, list):
                content = ''.join(part.get('text', '') if isinstance(part, dict) else str(part) for part in content)
            content = str(content or '').strip()
            if content:
                return content
        except Exception as exc:
            logger.warning('OpenRouter model %s exception: %s', model, exc)
    return None


def _extract_error_location(log_text, file_name=''):
    """Extract the error line, preferring the requested file over unrelated tracebacks."""
    text = str(log_text or '')
    target = os.path.basename(str(file_name or '').replace('\\', '/').strip())

    def _numbers_for_line(line):
        patterns = (
            r'\bline\s+(\d+)\b',
            r':(\d+)(?::\d+)?(?:\)|\s|$)',
        )
        for pat in patterns:
            matches = re.findall(pat, line, re.I)
            if matches:
                try:
                    return int(matches[-1])
                except Exception:
                    pass
        return None

    # First inspect traceback/log lines that explicitly mention the requested file.
    if target:
        target_low = target.lower()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if target_low not in line.lower():
                continue
            number = _numbers_for_line(line)
            if number:
                return number

        # Python tracebacks may put the filename on one line and the line number
        # in a nearby "line N" fragment. Keep the association local.
        lines = text.splitlines()
        for idx, raw_line in enumerate(lines):
            if target_low not in raw_line.lower():
                continue
            window = '\n'.join(lines[max(0, idx - 1):min(len(lines), idx + 3)])
            match = re.search(r'\bline\s+(\d+)\b', window, re.I)
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    pass

    # Standard Python traceback form, preferably the last explicit traceback frame.
    matches = re.findall(r'File ["\'].*?["\'], line (\d+)', text, re.I)
    if matches:
        try:
            return int(matches[-1])
        except Exception:
            pass

    # Generic fallback for Node/PHP/other runtimes.
    for pat in (r'\bline\s+(\d+)\b', r':(\d+)(?::\d+)?(?:\)|\s|$)'):
        matches = re.findall(pat, text, re.I)
        if matches:
            try:
                return int(matches[-1])
            except Exception:
                pass
    return None


def _resolve_project_file(project_dir, file_name):
    """Resolve a project file across nested upload wrappers without escaping root."""
    root = os.path.realpath(os.path.abspath(project_dir))
    requested = str(file_name or '').replace('\\', '/').strip()
    if not requested:
        return None

    # Prefer the exact relative path supplied by the hosting runtime.
    candidate = os.path.realpath(os.path.abspath(os.path.join(root, requested)))
    if (candidate == root or candidate.startswith(root + os.sep)) and os.path.isfile(candidate):
        return candidate

    # Legacy nested wrappers can hide the file. Basename fallback is allowed only
    # when there is exactly one matching file; never pick an arbitrary duplicate.
    base = os.path.basename(requested)
    matches = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__', 'venv', '.venv')]
        if base in files:
            path = os.path.realpath(os.path.abspath(os.path.join(r, base)))
            if path == root or path.startswith(root + os.sep):
                matches.append(path)
                if len(matches) > 1:
                    return None
    return matches[0] if matches else None


def _ai_file_snapshot(path, error_log='', context_lines=80):
    """Read the relevant source area for AI diagnosis, with generous context.

    For small/medium source files the complete file is supplied so the AI can
    understand multi-line syntax, scope, imports, and surrounding logic. Large
    files are limited to a numbered window around the traceback location.
    Secrets are redacted before the source leaves the host.
    """
    try:
        if not os.path.isfile(path):
            return None
        raw = Path(path).read_text(encoding='utf-8', errors='ignore')
        if len(raw) > AI_CODE_MAX_CHARS:
            lines = raw.splitlines()
            line_no = _extract_error_location(error_log, os.path.basename(path))
            if line_no and 1 <= line_no <= len(lines):
                lo = max(1, line_no - context_lines)
                hi = min(len(lines), line_no + context_lines)
            else:
                lo, hi = 1, min(len(lines), context_lines * 2)

            # Do not silently replace a large source file with only one window.
            # Keep the error window plus bounded head/tail context inside the AI limit.
            window = [f'{i}: {lines[i-1]}' for i in range(lo, hi + 1)]
            head_count = min(80, max(20, context_lines // 2))
            tail_count = min(80, max(20, context_lines // 2))
            head = [f'{i}: {lines[i-1]}' for i in range(1, min(len(lines), head_count) + 1)]
            tail_start = max(1, len(lines) - tail_count + 1)
            tail = [f'{i}: {lines[i-1]}' for i in range(tail_start, len(lines) + 1)]
            chunks = []
            seen = set()
            for label, chunk in (('SOURCE_HEAD', head), ('ERROR_CONTEXT', window), ('SOURCE_TAIL', tail)):
                if not chunk:
                    continue
                block = '\n'.join(chunk)
                if block in seen:
                    continue
                seen.add(block)
                chunks.append(f'--- {label} ---\n{block}')
            numbered = '\n\n'.join(chunks)
            # Bound the outgoing snapshot without truncating the source file itself.
            if len(numbered) > AI_CODE_MAX_CHARS:
                numbered = numbered[:AI_CODE_MAX_CHARS] + '\n--- SNAPSHOT TRIMMED FOR AI CONTEXT ONLY ---'
            return _redact_for_ai(numbered)
        lines = raw.splitlines()
        numbered = '\n'.join(f'{i}: {lines[i-1]}' for i in range(1, len(lines) + 1))
        return _redact_for_ai(numbered)
    except Exception:
        return None


def _validate_source_candidate(runtime, old_raw, new_raw, file_name=''):
    """Validate a proposed source patch without executing the user's project."""
    try:
        runtime = str(runtime or '').lower().strip()
        if runtime == 'python':
            compile(new_raw, file_name or '<ai-repair>', 'exec')
            return True, 'Python syntax is valid.'
        if runtime == 'node':
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix=Path(file_name or 'repair.js').suffix or '.js',
                delete=False, encoding='utf-8'
            )
            tmp.write(new_raw)
            tmp.close()
            try:
                check = subprocess.run(
                    ['node', '--check', tmp.name],
                    capture_output=True, text=True,
                    encoding='utf-8', errors='ignore', timeout=30
                )
            finally:
                try:
                    os.remove(tmp.name)
                except OSError:
                    pass
            if check.returncode == 0:
                return True, 'JavaScript syntax is valid.'
            return False, (check.stderr or check.stdout or 'Node syntax validation failed')[-1800:]
        if runtime == 'php':
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.php', delete=False,
                encoding='utf-8'
            )
            tmp.write(new_raw)
            tmp.close()
            try:
                check = subprocess.run(
                    ['php', '-l', tmp.name],
                    capture_output=True, text=True,
                    encoding='utf-8', errors='ignore', timeout=30
                )
            finally:
                try:
                    os.remove(tmp.name)
                except OSError:
                    pass
            if check.returncode == 0:
                return True, 'PHP syntax is valid.'
            return False, (check.stderr or check.stdout or 'PHP syntax validation failed')[-1800:]
        return False, f'Unsupported source runtime: {runtime}'
    except SyntaxError as exc:
        return False, f'{exc.__class__.__name__}: {exc}'
    except Exception as exc:
        return False, str(exc)


import difflib

_KNOWN_PIP_PACKAGES = {
    'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
    'requests': 'requests', 'bs4': 'beautifulsoup4', 'PIL': 'Pillow',
    'cv2': 'opencv-python', 'dotenv': 'python-dotenv', 'yaml': 'PyYAML',
    'numpy': 'numpy', 'pandas': 'pandas', 'flask': 'Flask',
    'django': 'Django', 'fastapi': 'fastapi', 'aiohttp': 'aiohttp',
    'httpx': 'httpx', 'psutil': 'psutil', 'sqlalchemy': 'SQLAlchemy',
    'pydub': 'pydub', 'moviepy': 'moviepy', 'pyrogram': 'pyrogram',
    'aiogram': 'aiogram', 'telethon': 'telethon', 'yt_dlp': 'yt-dlp',
    'googletrans': 'googletrans', 'uvicorn': 'uvicorn[standard]',
}

_STDLIB_NAMES = {
    'os','sys','re','json','time','math','random','logging','threading','asyncio',
    'subprocess','zipfile','tempfile','shutil','sqlite3','socket','signal','atexit',
    'pathlib','datetime','typing','collections','itertools','functools','traceback',
    'abc','argparse','base64','hashlib','hmac','html','http','urllib','email','csv',
    'string','statistics','decimal','fractions','contextlib','dataclasses','enum',
    'inspect','io','glob','platform','struct','binascii','pickle','copy','uuid',
    'secrets','wave','array','queue','heapq','bisect','ast','difflib','operator',
}


def _fix_missing_colon(lines, line_no):
    if line_no < 1 or line_no > len(lines):
        return None
    raw = lines[line_no - 1]
    body = raw.rstrip('\r\n')
    newline = raw[len(body):] or '\n'
    stripped = body.strip()
    prefixes = ('def ', 'async def ', 'class ', 'if ', 'elif ', 'else', 'for ',
                'while ', 'try', 'except', 'finally', 'with ', 'async with ', 'async for ')
    if stripped.endswith(':') or stripped.endswith('\\'):
        return None
    if not any(stripped == p or stripped.startswith(p) for p in prefixes):
        return None
    return body + ':' + newline


def _fix_missing_closing_bracket(lines, line_no):
    if line_no < 1 or line_no > len(lines):
        return None
    raw = lines[line_no - 1]
    body = raw.rstrip('\r\n')
    newline = raw[len(body):] or '\n'
    text = body
    stack = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    closers = {')': '(', ']': '[', '}': '{'}
    quote = None
    triple = False
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if triple and text.startswith(quote * 3, i):
                quote = None; triple = False; i += 3; continue
            if not triple and ch == quote and (i == 0 or text[i-1] != '\\'):
                quote = None
            i += 1; continue
        if ch in ('"', "'"):
            if text.startswith(ch * 3, i):
                quote = ch; triple = True; i += 3; continue
            quote = ch; triple = False; i += 1; continue
        if ch in pairs:
            stack.append(ch)
        elif ch in closers:
            if not stack or stack[-1] != closers[ch]:
                return None
            stack.pop()
        i += 1
    if quote or not stack:
        return None
    candidate = body + ''.join(pairs[ch] for ch in reversed(stack))
    try:
        compile(candidate, '<local-fix>', 'exec')
    except SyntaxError:
        return None
    return candidate + newline


def _fix_missing_quote(lines, line_no):
    if line_no < 1 or line_no > len(lines):
        return None
    raw = lines[line_no - 1]
    body = raw.rstrip('\r\n')
    newline = raw[len(body):] or '\n'
    # Only attempt a quote when the line has an obvious unmatched simple quote.
    for q in ('"', "'"):
        count = 0
        escaped = False
        for ch in body:
            if ch == q and not escaped:
                count += 1
            escaped = (ch == '\\' and not escaped)
            if ch != '\\':
                escaped = False
        if count % 2:
            candidate = body + q
            try:
                compile(candidate, '<local-fix>', 'exec')
                return candidate + newline
            except SyntaxError:
                pass
    return None


def _fix_nameerror_typo(lines, line_no, log_text):
    """Fix the very specific NameError typo case when Python suggests the name."""
    if line_no < 1 or line_no > len(lines):
        return None
    text = str(log_text or '').replace('\u00a0', ' ')
    m = re.search(
        r"name ['\"]([A-Za-z_]\w*)['\"] is not defined.*?"
        r"Did you mean:\s*['\"]([A-Za-z_]\w*)['\"]",
        text, re.I | re.S
    )
    if not m:
        return None
    wrong, right = m.group(1), m.group(2)
    raw = lines[line_no - 1]
    body = raw.rstrip('\r\n')
    newline = raw[len(body):] or '\n'
    # Replace only identifier tokens, never substrings inside another identifier.
    new_body = re.sub(rf'\b{re.escape(wrong)}\b', right, body)
    if new_body == body:
        return None
    try:
        compile(''.join(lines[:line_no-1] + [new_body + newline] + lines[line_no:]), '<local-fix>', 'exec')
    except SyntaxError:
        return None
    return new_body + newline


def _fix_import_typo(lines, line_no, log_text):
    if line_no < 1 or line_no > len(lines):
        return None
    raw = lines[line_no - 1]
    body = raw.rstrip('\r\n')
    newline = raw[len(body):] or '\n'
    m = re.match(r'^(\s*)(from|import)\s+([A-Za-z_]\w*)', body)
    if not m:
        return None
    wrong = m.group(3)
    candidates = list(_KNOWN_PIP_PACKAGES) + list(_STDLIB_NAMES)
    close = difflib.get_close_matches(wrong, candidates, n=1, cutoff=0.78)
    if not close or close[0] == wrong:
        return None
    right = close[0]
    return body[:m.start(3)] + right + body[m.end(3):] + newline


def _close_triple_quote_patch(raw_source, opening_line_no):
    """Close an unambiguous unterminated triple-quoted string at EOF.

    The patch is only accepted after the complete source compiles successfully.
    It never writes the file itself; the normal repair approval/apply flow does.
    """
    if not raw_source or opening_line_no < 1:
        return None

    lines = raw_source.splitlines(keepends=True)
    if opening_line_no > len(lines):
        return None

    opening_line = lines[opening_line_no - 1]
    opening_body = opening_line.rstrip('\r\n')

    for quote in ('\"\"\"', chr(39) * 3):
        idx = opening_body.find(quote)
        if idx < 0:
            continue
        # A second identical delimiter on the same line already closes it.
        if opening_body.find(quote, idx + len(quote)) >= 0:
            continue

        prefix = opening_body[:idx]
        op = prefix.count('(') - prefix.count(')')
        ob = prefix.count('[') - prefix.count(']')
        oc = prefix.count('{') - prefix.count('}')
        if min(op, ob, oc) < 0:
            continue

        closers = ')' * op + ']' * ob + '}' * oc
        m = re.match(r'^(\s*)', opening_body)
        indent = m.group(1) if m else ''
        close_line = indent + quote + closers + '\n'

        base = raw_source if raw_source.endswith('\n') else raw_source + '\n'
        old_text = None
        for tail_len in (30, 60, 100, 200, 400, 800):
            candidate = base[-tail_len:] if len(base) > tail_len else base
            if raw_source.count(candidate) == 1:
                old_text = candidate
                break
        if old_text is None:
            continue

        new_text = old_text + close_line
        new_raw = raw_source.replace(old_text, new_text, 1)
        try:
            compile(new_raw, '<triple-quote-fix>', 'exec')
        except SyntaxError as exc:
            logger.debug(
                'Triple-quote fix line %s rejected: %s',
                opening_line_no, exc
            )
            continue

        return {
            'old_text': old_text,
            'new_text': new_text,
            'problem': f'Unterminated triple-quoted string opened at line {opening_line_no}',
            'confidence': 0.93,
            'error_line': opening_line_no,
            'reason': (
                f'Appended closing {quote}{closers} at end of file to terminate '
                f'the string opened at line {opening_line_no}. Full-file syntax '
                f're-validated before approval.'
            ),
            'source': 'local-triple-quote-fix',
        }

    return None


def _find_unterminated_triple_quote_line(raw_source):
    """Return tokenizer-reported 1-based opening line for an unterminated triple quote."""
    if not raw_source:
        return None
    try:
        import io, tokenize
        for _ in tokenize.generate_tokens(io.StringIO(raw_source).readline):
            pass
        return None
    except tokenize.TokenError as exc:
        msg = str(exc.args[0]).lower() if exc.args else ''
        if 'string' in msg or 'multi-line' in msg:
            try:
                return int(exc.args[1][0])
            except (IndexError, TypeError, ValueError):
                pass
    except Exception:
        logger.debug('Could not locate unterminated triple quote with tokenize', exc_info=True)
    return None


def _ai_propose_triple_quote_fix(runtime, project_dir, file_name, log_text, user_id=None):
    """Ask AI for a minimal, fully validated triple-quote repair using source context."""
    if str(runtime or '').lower().strip() != 'python':
        return None
    root = os.path.abspath(project_dir)
    candidate = _resolve_project_file(root, file_name)
    if not candidate or not os.path.isfile(candidate):
        return None
    try:
        raw = Path(candidate).read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return None

    exact_line = _find_unterminated_triple_quote_line(raw)
    if not exact_line:
        return None

    if len(raw) <= AI_CODE_MAX_CHARS:
        source_snapshot = '\n'.join(
            f'{i}: {line}' for i, line in enumerate(raw.splitlines(), 1)
        )
    else:
        lines = raw.splitlines()
        lo = max(1, exact_line - 120)
        hi = min(len(lines), exact_line + 120)
        head = min(120, len(lines))
        tail_start = max(1, len(lines) - 120 + 1)
        chunks = [
            '--- SOURCE_HEAD ---\n' + '\n'.join(f'{i}: {lines[i-1]}' for i in range(1, head + 1)),
            '--- TRIPLE_QUOTE_CONTEXT ---\n' + '\n'.join(f'{i}: {lines[i-1]}' for i in range(lo, hi + 1)),
            '--- SOURCE_TAIL ---\n' + '\n'.join(f'{i}: {lines[i-1]}' for i in range(tail_start, len(lines) + 1)),
        ]
        source_snapshot = '\n\n'.join(chunks)
        if len(source_snapshot) > AI_CODE_MAX_CHARS:
            source_snapshot = source_snapshot[:AI_CODE_MAX_CHARS] + '\n--- SNAPSHOT TRIMMED FOR AI CONTEXT ONLY ---'

    prompt = f"""
You are fixing one concrete Python syntax error in a production project.

FILE: {file_name}
TOTAL LINES: {len(raw.splitlines())}
TOKENIZER-REPORTED UNTERMINATED TRIPLE-QUOTE OPENING LINE: {exact_line}

ERROR / TRACEBACK:
{_redact_for_ai(str(log_text or '')[-AUTO_REPAIR_LOG_CHARS:])}

SOURCE CONTEXT:
{_redact_for_ai(source_snapshot)}

TASK:
Return the smallest exact source patch that makes this file syntactically valid.
The tokenizer indicates that a triple-quoted string starts at line {exact_line}
without a closing delimiter before EOF.

Choose the correct repair from the source context:
1. Close a docstring before the next code block/dedented declaration when clearly intended.
2. Close a multiline value at its logical end, including required bracket closure when clearly required.
3. If the opening itself is clearly a typo, correct only that opening.

Return ONLY valid JSON:
{{
  "problem": "short factual root cause",
  "confidence": 0.0,
  "error_line": {exact_line},
  "old_text": "EXACT unique source block",
  "new_text": "replacement block",
  "reason": "why this exact smallest change fixes the syntax error",
  "category": "syntax"
}}

RULES:
- old_text MUST exactly match the supplied source and occur exactly once.
- Prefer the smallest possible change; one added delimiter is ideal.
- Multi-line old_text/new_text are allowed only when necessary to place the delimiter correctly. There is no arbitrary 20-line restriction for this dedicated repair, but keep the change minimal.
- Do not reformat unrelated code or invent new application logic.
- Do not add, expose, copy, move, or replace credentials/tokens/secrets.
- Full-file compile() validation will be performed before approval.
- If a safe exact patch cannot be determined, return empty old_text/new_text.
"""

    content = call_ai_provider(int(user_id or 0), prompt)
    if not content or content == 'AI service temporarily unavailable':
        return None
    try:
        match = re.search(r'\{.*\}', _strip_think_tags(content), re.S)
        result = json.loads(match.group(0)) if match else None
        if not isinstance(result, dict):
            return None
        old_text = str(result.get('old_text') or '')
        new_text = str(result.get('new_text') or '')
        if not old_text or not new_text or old_text == new_text:
            return None
        if len(old_text) > 12000 or len(new_text) > 12000:
            return None
        if raw.count(old_text) != 1:
            logger.warning('AI triple-quote patch rejected: old_text match count=%s', raw.count(old_text))
            return None
        new_raw = raw.replace(old_text, new_text, 1)
        ok, details = _validate_source_candidate('python', raw, new_raw, file_name)
        if not ok:
            logger.warning('AI triple-quote patch failed syntax validation: %s', details)
            return None
        try:
            confidence = max(0.0, min(1.0, float(result.get('confidence', 0.0) or 0.0)))
        except Exception:
            confidence = 0.0
        try:
            error_line = int(result.get('error_line') or exact_line)
        except Exception:
            error_line = exact_line
        return {
            'file_path': candidate,
            'file_name': file_name,
            'runtime': 'python',
            'old_text': old_text,
            'new_text': new_text,
            'problem': str(result.get('problem') or 'Unterminated triple-quoted string')[:1200],
            'reason': str(result.get('reason') or 'AI placed the missing triple-quote delimiter and full-file syntax validation passed.')[:1800],
            'confidence': confidence,
            'error_line': error_line,
            'source': 'ai-triple-quote-fix',
        }
    except Exception as exc:
        logger.warning('AI triple-quote patch parsing failed: %s', exc)
        return None


def _deterministic_triple_quote_fix(raw_source):
    """Fallback: append the missing triple-quote at EOF, then require full compile().

    The replacement patch is always built from text that exists in the current
    on-disk source. This is important when the original file has no trailing
    newline: approval/apply must still be able to locate old_text exactly.
    """
    if not raw_source:
        return None
    exact_line = _find_unterminated_triple_quote_line(raw_source)
    if not exact_line:
        return None

    lines = raw_source.splitlines(keepends=True)
    if exact_line < 1 or exact_line > len(lines):
        return None
    opening = lines[exact_line - 1].rstrip('\r\n')

    for quote in ('"""', "'''"):
        idx = opening.find(quote)
        if idx < 0 or opening.find(quote, idx + len(quote)) >= 0:
            continue

        prefix = opening[:idx]
        op = prefix.count('(') - prefix.count(')')
        ob = prefix.count('[') - prefix.count(']')
        oc = prefix.count('{') - prefix.count('}')
        if min(op, ob, oc) < 0:
            continue

        closers = ')' * op + ']' * ob + '}' * oc
        m = re.match(r'^(\s*)', opening)
        indent = m.group(1) if m else ''
        close_line = indent + quote + closers + '\n'

        # IMPORTANT: old_text MUST be a unique substring of raw_source itself,
        # never of a temporary copy with an added newline.
        old_text = None
        for tail_len in (30, 60, 100, 200, 400, 800):
            candidate = raw_source[-tail_len:] if len(raw_source) > tail_len else raw_source
            if candidate and raw_source.count(candidate) == 1:
                old_text = candidate
                break
        if old_text is None:
            continue

        # Preserve the file's existing EOF shape while making the replacement
        # text match exactly what the approval/apply stage expects.
        separator = '' if raw_source.endswith(('\n', '\r')) else '\n'
        new_text = old_text + separator + close_line
        new_raw = raw_source.replace(old_text, new_text, 1)

        try:
            compile(new_raw, '<triple-quote-fallback>', 'exec')
        except SyntaxError as exc:
            logger.debug('Deterministic triple-quote fallback rejected: %s', exc)
            continue

        return {
            'old_text': old_text,
            'new_text': new_text,
            'problem': f'Unterminated triple-quoted string at line {exact_line}',
            'reason': (
                f'Appended closing {quote}{closers} at EOF after AI repair was unavailable; '
                f'full-file syntax validation passed.'
            ),
            'confidence': 0.90,
            'error_line': exact_line,
            'source': 'deterministic-triple-quote-fix',
        }
    return None


def _smart_triple_quote_fix(runtime, project_dir, file_name, log_text, user_id=None):
    """AI-first triple-quote repair with a deterministic validated fallback."""
    if str(runtime or '').lower().strip() != 'python':
        return None
    ai_result = _ai_propose_triple_quote_fix(
        runtime, project_dir, file_name, log_text, user_id
    )
    if ai_result:
        logger.info('AI triple-quote fix prepared: %s @ line %s', file_name, ai_result.get('error_line'))
        return ai_result

    root = os.path.abspath(project_dir)
    candidate = _resolve_project_file(root, file_name)
    if not candidate:
        return None
    try:
        raw = Path(candidate).read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return None
    det_result = _deterministic_triple_quote_fix(raw)
    if det_result:
        det_result.update({'file_path': candidate, 'file_name': file_name, 'runtime': 'python'})
        logger.info('Deterministic triple-quote fix prepared: %s @ line %s', file_name, det_result.get('error_line'))
        return det_result
    return None

def _smart_local_patch(runtime, project_dir, file_name, log_text):
    """Deterministic, conservative local fallback for common Python startup/crash errors.

    Covers:
      * Unterminated triple-quoted strings
      * Missing ':' on compound statements
      * Unclosed (), [], {}
      * NameError typo with Python's "Did you mean" suggestion
      * Import/module typo
      * Unterminated single/double quotes

    Every candidate is full-file syntax validated before it is returned.
    """
    if str(runtime or '').lower().strip() != 'python':
        return None
    root = os.path.abspath(project_dir)
    candidate = _resolve_project_file(root, file_name)
    if not candidate or not (candidate == root or candidate.startswith(root + os.sep)):
        return None
    try:
        raw = Path(candidate).read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return None

    low = str(log_text or '').lower()

    # 1) Triple-quoted strings: AI gets the relevant source first, then the
    # deterministic EOF fallback is used only if AI cannot produce a uniquely
    # matching, compile-valid patch.
    if (
        'unterminated triple-quoted string' in low
        or 'eof in multi-line string' in low
    ):
        triple_patch = _smart_triple_quote_fix(
            runtime, project_dir, file_name, log_text, None
        )
        if triple_patch:
            return triple_patch

    # 2) Normal per-line deterministic fixers.
    lines = raw.splitlines(keepends=True)
    line_no = _extract_error_location(log_text, file_name)
    if not line_no:
        return None

    fixers = []
    if 'did you mean:' in low and 'name ' in low and 'is not defined' in low:
        fixers.append(('nameerror_typo', lambda L, N: _fix_nameerror_typo(L, N, log_text)))
    if 'no module named' in low or 'cannot import' in low:
        fixers.append(('import_typo', lambda L, N: _fix_import_typo(L, N, log_text)))
    if "expected ':'" in low or 'expected an indented block' in low:
        fixers.append(('missing_colon', _fix_missing_colon))
    if (
        'was never closed' in low
        or 'unexpected eof' in low
        or 'unexpected end of file' in low
        or 'unmatched' in low
    ):
        fixers.extend([
            ('missing_bracket', _fix_missing_closing_bracket),
            ('missing_quote', _fix_missing_quote),
        ])

    for name, fixer in fixers:
        try:
            new_line = fixer(lines, line_no)
            if not new_line:
                continue
            new_raw = ''.join(lines[:line_no - 1] + [new_line] + lines[line_no:])
            ok, _details = _validate_source_candidate('python', raw, new_raw, file_name)
            if not ok:
                continue
            return {
                'file_path': candidate,
                'file_name': file_name,
                'runtime': 'python',
                'old_text': lines[line_no - 1],
                'new_text': new_line,
                'problem': f'Python error ({name}) on line {line_no}',
                'confidence': 0.95 if name in {'nameerror_typo', 'missing_colon'} else 0.85,
                'error_line': line_no,
                'reason': (
                    f'Local auto-fix ({name}) prepared and full-file syntax '
                    f'validated before approval.'
                ),
                'source': f'local-{name}',
            }
        except Exception:
            logger.debug('Smart local fixer %s failed', name, exc_info=True)

    # 3) Last-ditch EOF bracket closure. This is only accepted if the complete
    # source compiles after adding the exact required closing delimiters.
    if 'unexpected eof' in low or 'was never closed' in low or 'unmatched' in low:
        try:
            stack = []
            pairs = {'(': ')', '[': ']', '{': '}'}
            closers = {')': '(', ']': '[', '}': '{'}
            in_string = None
            triple = False
            i = 0
            while i < len(raw):
                ch = raw[i]
                if in_string:
                    if triple and raw.startswith(in_string * 3, i):
                        in_string = None
                        triple = False
                        i += 3
                        continue
                    if not triple and ch == in_string:
                        prev = raw[i - 1] if i > 0 else ''
                        if prev != '\\':
                            in_string = None
                    i += 1
                    continue
                if ch in ('"', "'"):
                    if raw.startswith(ch * 3, i):
                        in_string = ch
                        triple = True
                        i += 3
                        continue
                    in_string = ch
                    triple = False
                    i += 1
                    continue
                if ch in pairs:
                    stack.append(ch)
                elif ch in closers:
                    if stack and stack[-1] == closers[ch]:
                        stack.pop()
                    else:
                        return None
                i += 1
            if stack and not in_string:
                append = ''.join(pairs[ch] for ch in reversed(stack)) + '\n'
                base = raw if raw.endswith('\n') else raw + '\n'
                new_raw = base + append
                try:
                    compile(new_raw, '<eof-bracket-fix>', 'exec')
                except SyntaxError:
                    return None
                old_text = base[-min(len(base), 60):]
                if raw.count(old_text) == 1:
                    return {
                        'file_path': candidate,
                        'file_name': file_name,
                        'runtime': 'python',
                        'old_text': old_text,
                        'new_text': old_text + append,
                        'problem': f'Unclosed {len(stack)} bracket(s) at EOF',
                        'confidence': 0.90,
                        'error_line': len(lines),
                        'reason': (
                            f'Appended {append.strip()} at end of file to close '
                            f'unclosed brackets. Syntax re-validated before approval.'
                        ),
                        'source': 'local-eof-bracket-fix',
                    }
        except Exception:
            logger.debug('EOF bracket fixer failed', exc_info=True)

    return None


def _local_safe_syntax_patch(runtime, project_dir, file_name, log_text):
    """Prepare a conservative patch for a few unambiguous syntax errors.

    This is only a fallback when the external AI provider is unavailable.
    It never writes the file; the normal owner-approval flow still applies.
    """
    runtime = str(runtime or '').lower().strip()
    if runtime != 'python':
        return None

    candidate = os.path.abspath(os.path.join(project_dir, file_name))
    root = os.path.abspath(project_dir)
    if not (candidate == root or candidate.startswith(root + os.sep)):
        return None
    if not os.path.isfile(candidate):
        return None

    text = str(log_text or '')
    if 'expected' not in text.lower() or ':' not in text:
        return None

    line_no = _extract_error_location(text, file_name)
    if not line_no:
        return None

    try:
        lines = Path(candidate).read_text(
            encoding='utf-8', errors='ignore'
        ).splitlines(keepends=True)
    except OSError:
        return None

    if line_no < 1 or line_no > len(lines):
        return None

    raw_line = lines[line_no - 1]
    body = raw_line.rstrip('\r\n')
    newline = raw_line[len(body):] or '\n'
    stripped = body.strip()

    # Only repair a missing colon on Python compound-statement headers.
    # Do not touch arbitrary expressions or user data.
    compound = (
        stripped.startswith('def '),
        stripped.startswith('async def '),
        stripped.startswith('class '),
        stripped.startswith('if '),
        stripped.startswith('elif '),
        stripped == 'else',
        stripped.startswith('for '),
        stripped.startswith('while '),
        stripped == 'try',
        stripped.startswith('except'),
        stripped == 'finally',
        stripped.startswith('with '),
    )
    if not any(compound) or stripped.endswith(':'):
        return None

    # Python traceback text such as "expected ':'" is the required evidence.
    expected_colon = bool(re.search(r"expected\s+['\"]?:['\"]?", text, re.I))
    if not expected_colon:
        return None

    new_line = body + ':' + newline
    new_raw = ''.join(lines[:line_no - 1] + [new_line] + lines[line_no:])

    ok, details = _validate_source_candidate(
        'python',
        ''.join(lines),
        new_raw,
        file_name
    )
    if not ok:
        logger.warning(
            'Local syntax fallback rejected for %s: %s',
            candidate, details
        )
        return None

    return {
        'file_path': candidate,
        'file_name': file_name,
        'runtime': 'python',
        'old_text': raw_line,
        'new_text': new_line,
        'problem': "Python reported a missing ':' on the indicated compound statement.",
        'confidence': 0.99,
        'error_line': line_no,
        'reason': "Added the missing ':' only to the traceback-indicated Python statement; source was syntax-validated before approval.",
        'source': 'local-safe-syntax-fallback',
    }


def _ai_propose_code_fix(runtime, project_dir, file_name, log_text, user_id=None):
    """Prepare a minimal owner-approved patch for the concrete reported bug."""
    if runtime not in {'python', 'node', 'php'}:
        return None
    root = os.path.abspath(project_dir)
    candidate = _resolve_project_file(root, file_name)
    if not candidate or not (candidate == root or candidate.startswith(root + os.sep)):
        return None
    source = _ai_file_snapshot(candidate, log_text, context_lines=80)
    rich_context = _build_rich_error_context(user_id, file_name, project_dir, runtime, log_text)
    if source is None:
        return None
    line_no = _extract_error_location(log_text, file_name)
    location_text = f'Likely error line: {line_no}' if line_no else 'No exact error line was available; use traceback/source evidence.'
    prompt = f"""
You are a conservative production code debugger.
Runtime: {runtime}
File: {file_name}
{location_text}

ERROR / TRACEBACK:
{_redact_for_ai(log_text[-AUTO_REPAIR_LOG_CHARS:])}

PROJECT CONTEXT:
{rich_context}

SOURCE (numbered; may be the complete file for normal-sized files):
{source}

Return ONLY valid JSON:
{{
  "problem": "short factual root cause",
  "confidence": 0.0,
  "error_line": 0,
  "old_text": "EXACT existing line or smallest necessary contiguous block",
  "new_text": "replacement block",
  "reason": "why this exact change fixes the reported error",
  "category": "syntax|dependency|name_error|type_error|attribute_error|import_error|config|runtime|other"
}}

STRICT SAFETY/QUALITY RULES:
- Fix the DIRECT reported error only. Do not refactor unrelated code.
- For ImportError such as "cannot import name X from Y", inspect the import and the rest of this file. Change the import AND every usage of that name in the file when required; do not merely rename the import if usages would then fail.
- For library migrations (Telethon, aiogram, python-telegram-bot, discord.py),
  use the installed version and traceback evidence; update imports and all usages together.
  Never assume an API was removed without evidence and never solve a code ImportError by
  blindly reinstalling a package.
- Telethon-specific: for missing names from telethon.tl.types, do not blindly
  reinstall Telethon or assert a type was removed. Verify the target version/API
  from available source/log evidence. Use telethon.tl.custom.Button (e.g.
  Button.inline(text, data), Button.url(text, url)) only when appropriate for
  the actual code; update all usages and preserve callback behavior.
- Handle any concrete bug type supported by the traceback: syntax/parse,
  unterminated strings/triple quotes, indentation, brackets, NameError,
  ReferenceError, TypeError, AttributeError, ImportError, bad calls,
  undefined names, JSON/config parsing, and similar runtime failures.
- old_text MUST exactly match the supplied source and MUST be unique.
- Prefer the smallest safe patch. One line is preferred; use a contiguous
  multi-line block only when genuinely required (maximum 20 lines).
- If a triple-quoted string is unterminated, inspect surrounding lines and
  choose the correct delimiter/location; do not blindly append text at EOF.
- Do not invent, generate, reveal, copy, or replace a secret/token value.
- For token/config errors, a patch is allowed only for deterministic formatting/loading/endpoint mistakes (for example stripping accidental whitespace or correcting a malformed API URL) when the exact old/new source is visible and uniquely matchable.
- Never move a credential from one user's project to another user's project and never bypass Telegram authentication/restrictions.
- Do not change security, permissions, approval logic, billing, hosting controls, or unrelated features.
- Do not add secrets, shell commands, downloads, or destructive code.
- Do not invent a dependency when the traceback does not show one.
- If evidence is insufficient for a safe exact patch, return empty old_text and
  new_text.
"""
    content = call_ai_provider(int(user_id or 0), prompt)
    if not content or content == 'AI service temporarily unavailable':
        return None
    try:
        match = re.search(r'\{.*\}', _strip_think_tags(content), re.S)
        result = json.loads(match.group(0)) if match else None
        if not isinstance(result, dict):
            return None
        old_text = str(result.get('old_text') or '')
        new_text = str(result.get('new_text') or '')
        if not old_text or not new_text or old_text == new_text or len(old_text) > 16000 or len(new_text) > 16000:
            return None
        # Allow genuinely multi-line repairs (large syntax blocks, indentation
        # repairs, callback/signature fixes, etc.) while still bounding the patch.
        # The source is compile-validated and the approval flow remains mandatory.
        if len(old_text.splitlines()) > 150 or len(new_text.splitlines()) > 150:
            logger.warning('AI patch rejected: patch exceeds 150 lines for %s', candidate)
            return None
        raw = Path(candidate).read_text(encoding='utf-8', errors='ignore')
        if raw.count(old_text) != 1:
            logger.warning('AI patch rejected: old_text match count=%s for %s', raw.count(old_text), candidate)
            return None
        new_raw = raw.replace(old_text, new_text, 1)
        ok, details = _validate_source_candidate(runtime, raw, new_raw, file_name)
        if not ok:
            logger.warning('AI patch rejected by syntax validation for %s: %s', candidate, details)
            return None
        result['problem'] = str(result.get('problem') or 'Code error')[:1200]
        result['reason'] = str(result.get('reason') or 'Targeted local source correction')[:1800]
        result['category'] = str(result.get('category') or 'runtime')[:40]
        try:
            result['confidence'] = max(0.0, min(1.0, float(result.get('confidence', 0.0) or 0.0)))
        except Exception:
            result['confidence'] = 0.0
        try:
            result['error_line'] = int(result.get('error_line') or line_no or 0)
        except Exception:
            result['error_line'] = line_no or 0
        result.update({'file_path': candidate, 'file_name': file_name, 'runtime': runtime})
        return result
    except Exception as exc:
        logger.warning('AI code patch parsing failed: %s', exc)
        return None


def _queue_ai_repair_approval(owner_id, message_obj, runtime, user_folder, file_name,
                              retry_count, diagnosis, packages=None, patch=None):
    repair_id = uuid.uuid4().hex[:12]
    provider = _friendly_ai_provider(_last_ai_provider_used.get(int(owner_id), _provider_for_user(owner_id)))
    pending_ai_repairs[repair_id] = {
        'owner_id': int(owner_id), 'chat_id': int(getattr(message_obj.chat, 'id', owner_id)),
        'runtime': runtime, 'user_folder': user_folder, 'file_name': file_name,
        'retry_count': int(retry_count), 'diagnosis': diagnosis, 'packages': list(packages or []),
        'patch': patch, 'created_at': time.time(), 'provider': provider,
    }
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Provider selection is available directly on the repair card.
    for _provider_key, _provider_label in (
        ('wormgpt', '💀 WormGPT'),
        ('deepseek', '⚡ DeepSeek'),
        ('qwen', '🧠 Qwen'),
        ('router', '🔀 Router'),
    ):
        markup.add(types.InlineKeyboardButton(
            _provider_label, callback_data=f'user_ai_provider_select_{_provider_key}'
        ))
    markup.row(types.InlineKeyboardButton('✅ Approve', callback_data=f'ai_fix_yes_{repair_id}'),
               types.InlineKeyboardButton('❌ Reject', callback_data=f'ai_fix_no_{repair_id}'))
    problem = str(diagnosis.get('problem') or 'Runtime error')[:500]
    action = str(diagnosis.get('action') or diagnosis.get('reason') or 'Targeted repair prepared.')[:500]
    category = str(diagnosis.get('category') or (patch or {}).get('category') or 'runtime')
    confidence = diagnosis.get('confidence', (patch or {}).get('confidence', 0.0))
    try:
        confidence_text = f'{float(confidence) * 100:.0f}%'
    except Exception:
        confidence_text = '—'
    lines = ['🛡️ <b>Darkwest AI Fixing</b>', f'Analyzed by: {_html_escape(provider)}', '',
             f'📦 <code>{_html_escape(file_name)}</code>', f'⚙️ {_html_escape(runtime)}',
             f'🧩 Type: <b>{_html_escape(category)}</b>  |  Confidence: <b>{_html_escape(confidence_text)}</b>',
             f'❌ {_html_escape(problem)}', f'🔧 {_html_escape(action)}']
    if category.startswith('token'):
        lines.append('🔐 <b>Credential safety:</b> token values are hidden; no credential is generated or copied automatically.')
    if packages:
        lines.append('📦 Install: <code>' + ', '.join(_html_escape(x) for x in packages[:5]) + '</code>')
    if patch:
        error_line = int(patch.get('error_line') or diagnosis.get('error_line') or 0)
        if error_line: lines.append(f'📍 Line: <code>{error_line}</code>')
        old_preview = _redact_for_ai(str(patch.get('old_text') or ''))[:1200]
        new_preview = _redact_for_ai(str(patch.get('new_text') or ''))[:1200]
        if old_preview:
            lines.append('📝 <b>Old:</b>\n<pre>' + _html_escape(old_preview) + '</pre>')
        if new_preview:
            lines.append('➡️ <b>New:</b>\n<pre>' + _html_escape(new_preview) + '</pre>')
        lines.append('🛡️ Source change will be validated again before replacement.')
    lines += ['', '🛡️ Approval required']
    try:
        sent=bot.send_message(owner_id, '\n'.join(lines), parse_mode='HTML', reply_markup=markup)
        pending_ai_repairs[repair_id]['approval_message_id']=sent.message_id
    except Exception as exc:
        logger.error('Failed to send AI repair approval to owner %s: %s', owner_id, exc, exc_info=True)
        pending_ai_repairs.pop(repair_id,None)
        return None
    return repair_id


def _cleanup_expired_ai_repairs():
    now = time.time()
    for rid, item in list(pending_ai_repairs.items()):
        if now - float(item.get('created_at', now)) > AI_REPAIR_TTL_SECONDS:
            pending_ai_repairs.pop(rid, None)


def _match_patch_old_text(raw, old_text):
    """Find exact patch text, or a unique whitespace-normalized/fuzzy match."""
    if not old_text:
        return None
    if raw.count(old_text) == 1:
        return old_text
    if raw.count(old_text) > 1:
        return None
    # First try whitespace-normalized line matching while retaining exact source slice.
    lines = raw.splitlines(keepends=True)
    target = old_text.splitlines()
    if target:
        norm = lambda x: ' '.join(x.strip().split())
        target_norm = [norm(x) for x in target]
        candidates = []
        for i in range(max(0, len(lines)-len(target)+1)):
            chunk = lines[i:i+len(target)]
            if [norm(x) for x in chunk] == target_norm:
                candidates.append(''.join(chunk))
        if len(candidates) == 1:
            return candidates[0]
    # Conservative fuzzy fallback: only accept one high-confidence block match.
    old_lines = old_text.splitlines()
    if len(old_lines) == 1:
        target_norm = ' '.join(old_lines[0].strip().split())
        candidates = []
        for line in lines:
            if difflib.SequenceMatcher(None, target_norm, ' '.join(line.strip().split())).ratio() >= 0.96:
                candidates.append(line)
        if len(candidates) == 1:
            return candidates[0]
    return None


def _apply_ai_repair(repair_id, approved_by):
    """Apply an owner-approved dependency install or exact source patch."""
    _cleanup_expired_ai_repairs()
    item = pending_ai_repairs.get(repair_id)
    if not item:
        return False, 'Repair request expired or was already handled.'
    if int(approved_by) != int(item['owner_id']):
        return False, 'Only the file owner can approve this repair.'

    patch = item.get('patch')
    if patch:
        path = os.path.abspath(patch['file_path'])
        root = os.path.abspath(item['user_folder'])
        if not (path == root or path.startswith(root + os.sep)):
            return False, 'Unsafe repair path.'
        try:
            raw = Path(path).read_text(encoding='utf-8', errors='ignore')
            old_text = patch['old_text']
            matched_text = _match_patch_old_text(raw, old_text)
            if matched_text is None:
                return False, 'Could not uniquely match the original code safely. Re-run the project to generate a fresh proposal.'
            new_raw = raw.replace(matched_text, patch['new_text'], 1)
            ok, details = _validate_source_candidate(item['runtime'], raw, new_raw, item['file_name'])
            if not ok:
                return False, f'Syntax validation failed: {details}'
            # Every approved repair gets its own immutable backup; never overwrite
            # a previous AI backup for the same source file.
            backup = f"{path}.ai_backup.{repair_id}"
            shutil.copy2(path, backup)
            tmp = f"{path}.ai_tmp.{repair_id}"
            try:
                Path(tmp).write_text(new_raw, encoding='utf-8')
                os.replace(tmp, path)
            finally:
                # os.replace removes the temp path on success. If anything fails,
                # remove the leftover temp artifact so projects stay clean.
                if os.path.lexists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        logger.warning('Could not remove AI temp file: %s', tmp)
            return True, f"Applied source fix to {item['file_name']}. Backup: {os.path.basename(backup)}"
        except Exception as exc:
            return False, str(exc)

    packages = item.get('packages') or []
    if packages:
        ok, result = _install_ai_packages(item['runtime'], item['user_folder'], packages)
        return ok, result
    return False, 'No actionable AI repair was stored.'


def _start_ai_repair_retry(repair_id, item):
    """Restart the owner project after an approved repair."""
    owner_id = int(item['owner_id'])
    user_folder = item['user_folder']
    file_name = item['file_name']
    runtime = item['runtime']
    retry_count = int(item.get('retry_count', 0)) + 1
    try:
        message_obj = _send_temp_message(owner_id, f'🔄 <b>Darkwest AI Fixing</b>\n📦 <code>{_html_escape(file_name)}</code>\n🔧 Applying repair...\n🔢 Retry {retry_count}/{AUTO_REPAIR_MAX_RETRIES}', parse_mode='HTML')
    except Exception:
        message_obj = None
    if message_obj is None:
        return False
    if runtime == 'python':
        threading.Thread(target=run_script, args=(os.path.join(user_folder, file_name), owner_id, user_folder, file_name, message_obj, 1, retry_count), daemon=True).start()
    elif runtime == 'node':
        if file_name == 'npm_start':
            threading.Thread(target=run_npm_start, args=(user_folder, owner_id, message_obj, retry_count), daemon=True).start()
        else:
            threading.Thread(target=run_js_script, args=(os.path.join(user_folder, file_name), owner_id, user_folder, file_name, message_obj, 1, retry_count), daemon=True).start()
    elif runtime == 'php':
        threading.Thread(target=run_php_script, args=(os.path.join(user_folder, file_name), owner_id, user_folder, file_name, message_obj, retry_count), daemon=True).start()
    else:
        return False
    return True


def _auto_install_runtime_missing_dependency(runtime, user_folder, file_name, log_text):
    """Install only an explicitly named missing Python/Node package from a crash log."""
    text = str(log_text or '')
    root = os.path.abspath(user_folder)
    if runtime == 'python':
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", text)
        if not match:
            return None
        module = match.group(1).split('.')[0]
        # If the project itself contains the module, this is likely a project-path
        # or packaging issue; don't install an unrelated package from PyPI.
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
            if module + '.py' in files or module in dirs:
                return None
        script_path = os.path.join(root, file_name) if file_name != 'npm_start' else ''
        if not script_path or not os.path.isfile(script_path):
            script_path = next((os.path.join(base, f) for base, dirs, files in os.walk(root)
                                for f in files if f.endswith('.py')), '')
        if script_path and _auto_install_missing_python_module(module, script_path, 0, root):
            return module
        return None

    if runtime == 'node':
        match = re.search(r"Cannot find module ['\"]([^'\"]+)['\"]", text, re.I)
        if not match:
            return None
        module = match.group(1).strip()
        # Ignore local/absolute paths and Node built-ins; only install named packages.
        if (module.startswith(('.', '/', '\\')) or re.match(r'^[A-Za-z]:[\\/]', module)
                or module.startswith('node:')):
            return None
        try:
            builtins_result = subprocess.run(
                ['node', '-e', "console.log(JSON.stringify(require('module').builtinModules))"],
                cwd=root, capture_output=True, text=True, timeout=10
            )
            builtins = set(json.loads(builtins_result.stdout)) if builtins_result.returncode == 0 else set()
        except Exception:
            builtins = set()
        if module in builtins or module.removeprefix('node:') in builtins:
            return None
        # Scoped packages are valid; reject shell metacharacters and malformed names.
        if not re.fullmatch(r'@?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?', module):
            return None
        npm = shutil.which('npm')
        if not npm:
            return None
        try:
            result = _run_checked([npm, 'install', '--save', '--no-audit', '--no-fund', module],
                                  root, 'automatic missing Node dependency ' + module)
            if result.returncode == 0:
                logger.info('AUTO-REPAIR: installed missing Node package %s', module)
                return module
            logger.warning('AUTO-REPAIR: Node package install failed for %s: %s', module,
                           (result.stderr or result.stdout)[-1600:])
        except Exception:
            logger.exception('AUTO-REPAIR: Node package install exception for %s', module)
    return None


def _auto_repair_started_process(script_key, process, user_folder, log_file_path,
                                 message_obj, file_name, file_type, retry_count):
    """Diagnose an early failure and queue an owner-approved AI repair; never mutate automatically."""
    runtime = _runtime_from_type(file_type)
    if runtime == 'static':
        return False
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_text = f.read()[-AUTO_REPAIR_LOG_CHARS:]
    except Exception:
        log_text = ''
    if not log_text.strip() or retry_count >= AUTO_REPAIR_MAX_RETRIES:
        return False

    # Deterministic repair first: when a crash explicitly names a missing Python or
    # Node package, install it and schedule one bounded restart. Code changes still
    # go through the existing owner-approval workflow below.
    try:
        missing_package = _auto_install_runtime_missing_dependency(
            runtime, user_folder, file_name, log_text
        )
    except Exception:
        logger.exception('Runtime missing-dependency auto repair failed for %s', file_name)
        missing_package = None
    if missing_package:
        info = bot_scripts.get(script_key, {})
        if isinstance(info, dict):
            info['auto_restart_after_repair'] = True
            info['auto_restart_retry'] = retry_count + 1
            info['auto_restart_runtime'] = runtime
            info['auto_restart_file_type'] = file_type
            info['auto_restart_package'] = missing_package
        try:
            bot.reply_to(message_obj,
                         f'✅ Missing package `{missing_package}` installed. Retrying project automatically...',
                         parse_mode='Markdown')
        except Exception:
            pass
        return True

    owner_id = int(bot_scripts.get(script_key, {}).get('script_owner_id', getattr(message_obj.chat, 'id', 0)))
    low_err = str(log_text or '').lower()
    known_source_error = (
        runtime == 'python' and (
            'syntaxerror' in low_err
            or 'unterminated' in low_err
            or 'was never closed' in low_err
            or 'unexpected eof' in low_err
            or 'unexpected end of file' in low_err
            or 'expected :' in low_err
            or 'did you mean:' in low_err
        )
    )
    diagnosis = None
    if not known_source_error:
        diagnosis = _token_error_diagnosis(log_text, user_folder)
        if not diagnosis:
            diagnosis = _openrouter_diagnose_dependency_error(runtime, user_folder, log_text, owner_id)
    if not diagnosis:
        pkg, problem = _fallback_dependency_from_error(runtime, log_text)
        diagnosis = {'problem': problem, 'packages': [pkg] if pkg else [], 'confidence': 0.5 if pkg else 0.0,
                     'action': 'Install the detected dependency and retry after owner approval.'}

    packages = diagnosis.get('packages', [])
    if 'cannot import name' in low_err or 'importerror' in low_err:
        packages = []  # Symbol/API incompatibility is a code migration unless a missing module is explicit.
    patch = None
    if not packages and runtime in {'python', 'node', 'php'} and file_name != 'npm_start':
        # Known Python syntax errors use the deterministic local fixer first.
        # This avoids an unnecessary AI/API call for unambiguous parser errors.
        if runtime == 'python':
            low_err = str(log_text or '').lower()
            local_first = (
                'unterminated triple-quoted string' in low_err
                or 'eof in multi-line string' in low_err
                or 'unterminated string literal' in low_err
                or "expected ':'" in low_err
                or 'expected an indented block' in low_err
                or 'was never closed' in low_err
                or 'unexpected eof' in low_err
                or 'unexpected end of file' in low_err
                or 'did you mean:' in low_err
                or 'no module named' in low_err
                or 'cannot import' in low_err
            )
            if local_first:
                patch = _smart_local_patch(runtime, user_folder, file_name, log_text)
        if not patch:
            patch = _ai_propose_code_fix(runtime, user_folder, file_name, log_text, owner_id)
        if not patch and runtime == 'python':
            patch = _smart_local_patch(runtime, user_folder, file_name, log_text)
        if not patch and runtime == 'python':
            patch = _local_safe_syntax_patch(runtime, user_folder, file_name, log_text)
        if patch:
            candidate_raw = Path(patch['file_path']).read_text(encoding='utf-8', errors='ignore')
            new_raw = candidate_raw.replace(patch['old_text'], patch['new_text'], 1)
            ok, details = _validate_source_candidate(runtime, candidate_raw, new_raw, file_name)
            if not ok:
                logger.warning('AI source patch failed syntax check: %s', details)
                patch = None
            else:
                diagnosis['action'] = patch.get('reason', 'Targeted source correction')
    if not packages and not patch:
        _professional_error_card(message_obj, runtime, diagnosis.get('problem', 'Unknown startup error'),
                                 'AI could not produce a safe, reviewable fix. No project files were changed.')
        return False

    owner_id = int(bot_scripts.get(script_key, {}).get('script_owner_id', getattr(message_obj.chat, 'id', 0)))
    repair_id = _queue_ai_repair_approval(owner_id, message_obj, runtime, user_folder, file_name,
                                          retry_count, diagnosis, packages=packages, patch=patch)
    if repair_id:
        return True
    return False

def _local_library_migration_fix(project_dir, file_name, log_text):
    """Prepare a conservative Telethon keyboard-helper migration for owner approval."""
    text = str(log_text or '')
    if 'cannot import name' not in text.lower() or 'telethon.tl.types' not in text:
        return None
    root = os.path.abspath(project_dir)
    candidate = _resolve_project_file(root, file_name)
    if not candidate or not os.path.isfile(candidate):
        return None
    try:
        raw = Path(candidate).read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return None

    mapping = {
        'KeyboardButtonCallback': 'inline',
        'KeyboardButtonUrl': 'url',
        'KeyboardButtonSwitchInline': 'switch_inline',
        'KeyboardButtonWebView': 'web_view',
    }
    pattern = re.compile(r'from\s+telethon\.tl\.types\s+import\s*\(([^)]*)\)|from\s+telethon\.tl\.types\s+import\s*([^\n]+)', re.S)
    match = pattern.search(raw)
    if not match:
        return None
    body = match.group(1) if match.group(1) is not None else match.group(2)
    names = [x.strip().strip(',') for x in body.split(',') if x.strip()]
    migrated = [n for n in names if n in mapping]
    if not migrated:
        return None
    # Only migrate constructor calls. If the symbol is used in another context
    # (e.g. isinstance/type checks), bail out rather than silently changing semantics.
    for name in migrated:
        other_refs = re.findall(r'\b' + re.escape(name) + r'\b', raw)
        constructor_refs = re.findall(r'\b' + re.escape(name) + r'\s*\(', raw)
        import_refs = len(other_refs) - len(constructor_refs)
        if import_refs > 1:
            logger.warning('Local Telethon migration skipped: non-constructor use of %s', name)
            return None
    kept = [n for n in names if n not in migrated]
    lines = []
    if kept:
        lines.append('from telethon.tl.types import (\n    ' + ',\n    '.join(kept) + ',\n)')
    lines.append('from telethon.tl.custom import Button')
    new_import = '\n'.join(lines)
    new_raw = raw[:match.start()] + new_import + raw[match.end():]
    for name in migrated:
        new_raw = re.sub(r'\b' + re.escape(name) + r'\s*\(', 'Button.' + mapping[name] + '(', new_raw)
    if new_raw == raw:
        return None
    try:
        compile(new_raw, candidate, 'exec')
    except SyntaxError as exc:
        logger.warning('Local Telethon migration rejected (syntax): %s', exc)
        return None
    # Approval machinery applies one exact old_text/new_text replacement. Full-file
    # replacement ensures both imports and constructor call sites are included.
    return {
        'file_path': candidate, 'file_name': file_name, 'runtime': 'python',
        'old_text': raw, 'new_text': new_raw,
        'problem': 'Telethon keyboard button import is incompatible with the installed API',
        'reason': 'Prepared a syntax-validated migration to telethon.tl.custom.Button helpers; review constructor semantics before approval.',
        'confidence': 0.78, 'error_line': 1, 'source': 'local-telethon-migration'
    }


def _ai_handle_direct_error(owner_id, message_obj, runtime, user_folder, file_name, error_text, retry_count=0):
    """Diagnose one concrete startup/syntax error and send one owner-approval card."""
    if runtime not in {'python', 'node', 'php'} or retry_count >= AUTO_REPAIR_MAX_RETRIES:
        return False
    low_err = str(error_text or '').lower()
    _save_error_to_history(owner_id, file_name, 'detected', error_text)
    known_source_error = (
        runtime == 'python' and (
            'syntaxerror' in low_err
            or 'unterminated' in low_err
            or 'was never closed' in low_err
            or 'unexpected eof' in low_err
            or 'unexpected end of file' in low_err
            or 'expected :' in low_err
            or 'did you mean:' in low_err
        )
    )
    diagnosis = None
    if not known_source_error:
        diagnosis = _token_error_diagnosis(error_text, user_folder)
        if not diagnosis:
            diagnosis = _openrouter_diagnose_dependency_error(runtime, user_folder, error_text, owner_id)
    if not diagnosis:
        diagnosis = {'problem': 'Runtime/syntax error detected; AI diagnosis was unavailable.', 'packages': [], 'confidence': 0.0}
    packages = diagnosis.get('packages') or []
    if 'cannot import name' in low_err or ('importerror' in low_err and 'no module named' not in low_err):
        packages = []  # Avoid installing unrelated packages for an API/symbol mismatch.
    patch = None
    target_file = file_name
    # npm start is a launcher, not the source file. Resolve the actual start/main file
    # so AI can propose a patch only where the traceback points.
    if file_name == 'npm_start':
        try:
            manifest = Path(user_folder) / 'package.json'
            if manifest.is_file():
                pkg = json.loads(manifest.read_text(encoding='utf-8', errors='ignore'))
                start_cmd = str((pkg.get('scripts') or {}).get('start') or '')
                main = str(pkg.get('main') or '')
                candidates = []
                m = re.search(r'(?:(?:node|tsx|ts-node)\s+)?(?:\./)?([A-Za-z0-9_./-]+\.(?:js|mjs|cjs|ts|tsx))', start_cmd)
                if m: candidates.append(m.group(1))
                if main: candidates.append(main)
                candidates += ['index.js', 'main.js', 'app.js', 'server.js', 'bot.js']
                for candidate in candidates:
                    candidate = candidate.lstrip('./')
                    if os.path.isfile(os.path.join(user_folder, candidate)):
                        target_file = candidate
                        break
        except Exception as exc:
            logger.debug('Could not resolve npm start source file: %s', exc)
    # A missing package is a dependency repair. For every other concrete error,
    # prepare an exact source patch proposal and keep the file untouched until approval.
    if not packages and target_file != 'npm_start':
        if runtime == 'python' and not patch:
            patch = _local_library_migration_fix(user_folder, target_file, error_text)
        if runtime == 'python' and known_source_error:
            if ('unterminated triple-quoted string' in low_err
                    or 'eof in multi-line string' in low_err):
                patch = _smart_triple_quote_fix(
                    runtime, user_folder, target_file, error_text, owner_id
                )
            if not patch:
                patch = _smart_local_patch(runtime, user_folder, target_file, error_text)
        if not patch:
            patch = _ai_propose_code_fix(runtime, user_folder, target_file, error_text, owner_id)
        if not patch and runtime == 'python':
            patch = _smart_local_patch(runtime, user_folder, target_file, error_text)
        if not patch:
            patch = _local_safe_syntax_patch(
                runtime, user_folder, target_file, error_text
            )
            if patch:
                diagnosis['problem'] = patch.get('problem', diagnosis.get('problem', 'Syntax error'))
                diagnosis['confidence'] = patch.get('confidence', diagnosis.get('confidence', 0.0))
                diagnosis['action'] = patch.get('reason', 'Safe local syntax correction prepared.')
                diagnosis['error_line'] = patch.get('error_line') or _extract_error_location(error_text, target_file) or 0
        if patch:
            candidate_raw = Path(patch['file_path']).read_text(encoding='utf-8', errors='ignore')
            new_raw = candidate_raw.replace(patch['old_text'], patch['new_text'], 1)
            ok, details = _validate_source_candidate(runtime, candidate_raw, new_raw, file_name)
            if not ok:
                logger.warning('AI direct-error patch failed syntax check: %s', details)
                patch = None
            else:
                diagnosis['action'] = patch.get('reason', 'Change only the reported error line/block.')
                diagnosis['error_line'] = patch.get('error_line') or _extract_error_location(error_text, file_name) or 0
    if not packages and not patch:
        category = diagnosis.get('category', 'unknown')
        line_no = diagnosis.get('error_line') or _extract_error_location(error_text, file_name) or 0
        detail = f'Category: {category}' + (f' | Line: {line_no}' if line_no else '')
        _professional_error_card(message_obj, runtime, diagnosis.get('problem', 'Unknown error'),
                                 detail + '. AI could not prepare a uniquely validated patch. No code was changed.')
        return False
    repair_id = _queue_ai_repair_approval(
        owner_id, message_obj, runtime, user_folder, file_name, retry_count,
        diagnosis, packages=packages, patch=patch
    )
    if repair_id:
        # The approval card itself contains the exact affected source line/block and reason.
        return True
    return False


def _watch_started_process(script_key, process, user_folder, log_file_path,
                            message_obj, file_name, file_type=None, retry_count=0):
    """Monitor a hosted process for its entire lifetime and diagnose crashes.

    The previous watcher only observed the first ~30 seconds. This watcher stays
    alive until the process exits, so later crashes are also detected. It never
    blindly edits source: the repair path still validates a candidate and sends
    it through the existing owner-approval/apply flow.
    """
    try:
        # Do not impose a short startup deadline: a healthy long-running process
        # may take more than 30 seconds to initialize.
        last_log_size = 0
        runtime_error_triggered = False
        error_markers = ('traceback (most recent call last)', 'syntaxerror', 'importerror',
                         'modulenotfounderror', 'nameerror', 'typeerror', 'attributeerror',
                         'keyerror', 'valueerror', 'file not found', 'connectionerror',
                         'timeouterror', '401 unauthorized', '409 conflict')
        while True:
            if process.poll() is not None:
                break
            # Runtime log monitor: trigger one owner-approval diagnosis for a newly
            # observed traceback/error while the process remains alive. Never edit code here.
            if not runtime_error_triggered:
                try:
                    if os.path.isfile(log_file_path):
                        size = os.path.getsize(log_file_path)
                        if size > last_log_size:
                            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as lf:
                                lf.seek(last_log_size)
                                new_text = lf.read()
                            last_log_size = size
                            low_new = new_text.lower()
                            if any(marker in low_new for marker in error_markers):
                                runtime_error_triggered = True
                                runtime = _runtime_from_type(file_type or bot_scripts.get(script_key, {}).get('type', 'unknown'))
                                owner_for_repair = int(bot_scripts.get(script_key, {}).get('script_owner_id', getattr(message_obj.chat, 'id', 0)))
                                threading.Thread(target=_ai_handle_direct_error,
                                    args=(owner_for_repair, message_obj, runtime, user_folder, file_name,
                                          new_text[-AUTO_REPAIR_LOG_CHARS:], retry_count), daemon=True).start()
                except Exception:
                    logger.debug('Continuous log monitor failed for %s', script_key, exc_info=True)
            time.sleep(2)

        rc = process.returncode
        # A manual stop/reset removes the key from bot_scripts. In that case the
        # watcher must not report a crash or create a repair request.
        if script_key not in bot_scripts:
            return

        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                tail = f.read()[-AUTO_REPAIR_LOG_CHARS:]
        except Exception:
            tail = ''

        if file_type is None:
            info = bot_scripts.get(script_key, {})
            file_type = info.get('type', 'unknown')

        _watch_log_handle = None
        try:
            info = bot_scripts.get(script_key, {})
            _watch_log_handle = info.get('log_file') if isinstance(info, dict) else None
        except Exception:
            _watch_log_handle = None

        repaired = False
        if rc != 0:
            try:
                repaired = _auto_repair_started_process(
                    script_key, process, user_folder, log_file_path,
                    message_obj, file_name, file_type, retry_count
                )
            except Exception:
                logger.exception("Auto-repair watcher failed for %s", script_key)

        restart_info = dict(bot_scripts.get(script_key, {})) if repaired else {}
        bot_scripts.pop(script_key, None)

        if repaired:
            if restart_info.get('auto_restart_after_repair'):
                next_retry = int(restart_info.get('auto_restart_retry', retry_count + 1))
                runtime = restart_info.get('auto_restart_runtime')
                try:
                    if runtime == 'python':
                        entry = os.path.join(user_folder, file_name)
                        threading.Thread(target=run_script,
                            args=(entry, int(restart_info.get('script_owner_id', 0)), user_folder,
                                  file_name, message_obj, 1, next_retry), daemon=True).start()
                    elif runtime == 'node':
                        if file_name == 'npm_start':
                            threading.Thread(target=run_npm_start,
                                args=(user_folder, int(restart_info.get('script_owner_id', 0)),
                                      message_obj, next_retry), daemon=True).start()
                        else:
                            entry = os.path.join(user_folder, file_name)
                            threading.Thread(target=run_js_script,
                                args=(entry, int(restart_info.get('script_owner_id', 0)), user_folder,
                                      file_name, message_obj, 1, next_retry), daemon=True).start()
                except Exception:
                    logger.exception('Automatic restart after dependency repair failed for %s', file_name)
            return

        if rc != 0:
            runtime = _runtime_from_type(file_type)
            if _token_error_from_log(tail):
                token_config = _find_project_token_config(user_folder, file_name)
                owner_for_token = int(bot_scripts.get(script_key, {}).get('script_owner_id', getattr(message_obj.chat, 'id', 0)))
                if token_config and _ask_for_project_bot_token(message_obj, bot_scripts.get(script_key, {}).get('script_path', ''), owner_for_token,
                        user_folder, file_name, 1, retry_count, token_config):
                    bot_scripts.pop(script_key, None)
                    return
            detail = f'{file_name} crashed/stopped unexpectedly (exit code {rc}).'
            if tail.strip():
                detail += "\n\n📋 <b>Crash log:</b>\n<pre>" + _redact_for_ai(tail)[-2200:] + "</pre>"
            try:
                bot.reply_to(message_obj, detail[:4000], parse_mode='HTML')
            except Exception:
                try:
                    bot.reply_to(message_obj, f'❌ {file_name} crashed. Check View Logs.')
                except Exception:
                    pass
        else:
            logger.info('Hosted process %s exited normally with code 0.', script_key)
    finally:
        # Close the inherited log handle captured before bookkeeping is removed.
        try:
            log_handle = locals().get('_watch_log_handle')
            if log_handle and hasattr(log_handle, 'close'):
                log_handle.close()
        except Exception:
            pass



# --- Logic functions ---
def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    logger.info(f"Welcome request from user_id: {user_id}")
    if is_user_banned(user_id):
        bot.send_message(chat_id, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot locked by admin. Try later.")
        return
    if user_id not in active_users:
        add_active_user(user_id)
        try:
            owner_notification = (f"🎉 New user!\n👤 Name: {user_name}\n🆔 ID: `{user_id}`")
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"⚠️ Failed to notify owner about new user {user_id}: {e}")
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Owner"
    elif user_id in admin_ids:
        user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ Subscription expires in: {days_left} days"
        else:
            user_status = "🆓 Free User (Expired Sub)"
            remove_subscription_db(user_id)
    else:
        user_status = "🆓 Free User"
    welcome_msg_text = (
        f"👑  DARKWEST HOSTING\n━━━━━━━━━━━━━━━━━━\n✨ Welcome, {user_name}!\n\n"
        f"🆔 Your User ID: `{user_id}`\n🔰 Your Status: {user_status}{expiry_info}\n"
        f"📁 Projects: {current_files} / {limit_str}\n\n"
        "💎 Python • Node.js • PHP • ZIP Hosting\n"
        "📦 Automatic dependency setup where supported\n\n"
        "━━━━━━━━━━━━━━━━━━\n👇 Neeche dashboard se option select karein."
    )
    main_reply_markup = create_reply_keyboard_main_menu(user_id)
    try:
        welcome_media = _load_welcome_media()
        if welcome_media.get('type') == 'photo' and welcome_media.get('file_id'):
            bot.send_photo(chat_id, welcome_media['file_id'], caption=welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
        elif welcome_media.get('type') == 'video' and welcome_media.get('file_id'):
            bot.send_video(chat_id, welcome_media['file_id'], caption=welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending welcome to {user_id}: {e}", exc_info=True)

def _logic_updates_channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📢 Updates Channel', url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'))
    bot.reply_to(message, "Visit our Updates Channel:", reply_markup=markup)

def _logic_upload_file(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin, cannot accept files.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ File limit ({current_files}/{limit_str}) reached. Delete files first.")
        return
    bot.reply_to(message, "📤 Send `.py`, `.js`, `.php`, `.html`, or `.zip` project.")

def _format_uptime(start_time):
    """Return a compact human-readable uptime for a running project."""
    if not isinstance(start_time, datetime):
        return "Unknown"
    total = max(0, int((datetime.now() - start_time).total_seconds()))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def _project_runtime_info(owner_id, file_name):
    """Return runtime/status details without starting or stopping anything."""
    script_key = f"{owner_id}_{file_name}"
    info = bot_scripts.get(script_key, {})
    running = is_bot_running(owner_id, file_name)
    proc = info.get('process')
    pid = getattr(proc, 'pid', None) if proc else None
    start_time = info.get('start_time') if running else None
    now = datetime.now()
    info['last_check_time'] = now
    if info and script_key in bot_scripts:
        bot_scripts[script_key]['last_check_time'] = now
    return running, pid, start_time, now, info


def _project_last_update_time(owner_id, file_name):
    """Return the newest modification time belonging to this hosted project."""
    folder = get_user_folder(owner_id)
    marker = _read_zip_project_marker(folder)
    is_zip_project = bool(marker and marker.get('entry_name') == file_name)
    candidates = []
    if is_zip_project:
        candidates.append(folder)
    else:
        if file_name == 'npm_start':
            candidates.append(folder)
        else:
            candidates.append(os.path.join(folder, file_name))
    newest = None
    try:
        for base in candidates:
            if os.path.isfile(base):
                try:
                    return datetime.fromtimestamp(os.path.getmtime(base))
                except OSError:
                    return None
            if os.path.isdir(base):
                for root, dirs, files in os.walk(base):
                    dirs[:] = [d for d in dirs if d not in {'__pycache__', 'node_modules'}]
                    for name in files:
                        if name.endswith('.log') or name == ZIP_PROJECT_MARKER:
                            continue
                        path_ = os.path.join(root, name)
                        try:
                            ts = datetime.fromtimestamp(os.path.getmtime(path_))
                            if newest is None or ts > newest:
                                newest = ts
                        except OSError:
                            continue
    except OSError:
        pass
    return newest


def _live_project_card(owner_id, file_name, file_type):
    running, pid, start_time, checked_at, info = _project_runtime_info(owner_id, file_name)
    status = "🟢 ONLINE" if running else "🔴 OFFLINE"
    if running and start_time:
        uptime = _format_uptime(start_time)
        started = start_time.strftime('%d %b %Y, %I:%M:%S %p')
    else:
        uptime = "—"
        started = "Not running"
    pid_text = str(pid) if pid else "—"
    checked = checked_at.strftime('%d %b %Y, %I:%M:%S %p')
    updated_dt = _project_last_update_time(owner_id, file_name)
    updated = updated_dt.strftime('%d %b %Y, %I:%M:%S %p') if updated_dt else "Unknown"
    return (
        "╭─ ⚡ LIVE PROJECT ─────────────────╮\n"
        f"│  🚀 `{file_name}`\n"
        f"│  {status}  •  `{file_type}`\n"
        f"│  🆔 PID: `{pid_text}`\n"
        f"│  ⏱ Uptime: `{uptime}`\n"
        f"│  ▶️ Started: `{started}`\n"
        f"│  📝 Updated: `{updated}`\n"
        f"│  🔎 Checked: `{checked}`\n"
        "╰──────────────────────────────────╯"
    )


def _live_projects_markup(owner_id, file_name, running):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("📡 HTTP Check", callback_data=f'livehttp_{owner_id}_{file_name}'),
        types.InlineKeyboardButton("🔄 Refresh", callback_data=f'live_{owner_id}_{file_name}')
    )
    if running:
        markup.row(
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{owner_id}_{file_name}'),
            types.InlineKeyboardButton("⏹ Stop", callback_data=f'stop_{owner_id}_{file_name}')
        )
    else:
        markup.row(types.InlineKeyboardButton("🟢 Start", callback_data=f'start_{owner_id}_{file_name}'))
    markup.row(
        types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{owner_id}_{file_name}'),
        types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{owner_id}_{file_name}')
    )
    markup.row(types.InlineKeyboardButton("🔙 Back to Files", callback_data='check_files'))
    return markup


def _get_listening_ports(pid):
    ports = []
    if not pid:
        return ports
    try:
        proc = psutil.Process(int(pid))
        for conn in proc.net_connections(kind='inet'):
            if conn.status == psutil.CONN_LISTEN and conn.laddr:
                port = getattr(conn.laddr, 'port', None)
                if port and port not in ports:
                    ports.append(port)
    except psutil.AccessDenied as e:
        logger.debug("Access denied while inspecting listening ports for PID %s: %s", pid, e)
    except psutil.NoSuchProcess as e:
        logger.debug("Process %s disappeared while inspecting listening ports: %s", pid, e)
    except Exception as e:
        logger.debug("Could not inspect listening ports for PID %s: %s", pid, e)
    return sorted(ports)


def live_http_callback(call):
    """Check whether a running project's process exposes a local HTTP service."""
    try:
        _, owner_id_str, file_name = call.data.split('_', 2)
        owner_id = int(owner_id_str)
        requester = call.from_user.id
        if not (requester == owner_id or requester in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        info = bot_scripts.get(f"{owner_id}_{file_name}", {})
        pid = getattr(info.get('process'), 'pid', None)
        if not pid or not is_bot_running(owner_id, file_name):
            bot.answer_callback_query(call.id, "🔴 Project is not running.", show_alert=True)
            return
        ports = _get_listening_ports(pid)
        if not ports:
            bot.answer_callback_query(call.id, "ℹ️ No listening HTTP port detected for this process.", show_alert=True)
            return
        results = []
        import urllib.request
        for port in ports[:3]:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/", method='GET')
                with urllib.request.urlopen(req, timeout=2) as resp:
                    results.append(f"Port {port}: HTTP {resp.status}")
            except Exception as e:
                code = getattr(e, 'code', None)
                if code:
                    results.append(f"Port {port}: HTTP {code}")
                else:
                    results.append(f"Port {port}: TCP listening / HTTP check failed")
        bot.answer_callback_query(call.id, "📡 " + " | ".join(results), show_alert=True)
    except Exception as e:
        logger.error("HTTP live check failed: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "❌ HTTP check failed.", show_alert=True)


def live_project_callback(call):
    try:
        _, owner_id_str, file_name = call.data.split('_', 2)
        owner_id = int(owner_id_str)
        requester = call.from_user.id
        if not (requester == owner_id or requester in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        record = next((f for f in user_files.get(owner_id, []) if f[0] == file_name), None)
        if not record:
            bot.answer_callback_query(call.id, "⚠️ Project not found.", show_alert=True)
            return
        file_type = record[1]
        running, *_ = _project_runtime_info(owner_id, file_name)
        bot.answer_callback_query(call.id, "🔎 Live status refreshed.")
        text = _live_project_card(owner_id, file_name, file_type)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=_live_projects_markup(owner_id, file_name, running),
                              parse_mode='Markdown')
    except Exception as e:
        logger.error("Live project callback failed: %s", e, exc_info=True)
        bot.answer_callback_query(call.id, "❌ Live check failed.", show_alert=True)


def _logic_live_projects(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    records = user_files.get(user_id, [])
    if not records:
        bot.reply_to(message, "🔎 No projects found.\n\n📤 Upload a project first.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(records):
        running = is_bot_running(user_id, file_name)
        icon = "🟢" if running else "🔴"
        markup.add(types.InlineKeyboardButton(
            f"{icon} {file_name} • {file_type}",
            callback_data=f'live_{user_id}_{file_name}'
        ))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    bot.reply_to(message, "👑 **DARKWEST • LIVE PROJECTS**\n━━━━━━━━━━━━━━━━━━\n🌐 Live status dekhne ke liye project select karein.",
                 reply_markup=markup, parse_mode='Markdown')


def _logic_check_files(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.reply_to(message, "👑 DARKWEST • MY PROJECTS\n━━━━━━━━━━━━━━━━━━\n📂 Abhi koi project upload nahi hua.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Running" if is_running else "🔴 Stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    bot.reply_to(message, "👑 DARKWEST • MY PROJECTS\n━━━━━━━━━━━━━━━━━━\nProject manage karne ke liye select karein.", reply_markup=markup, parse_mode='Markdown')

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, "🏃 Testing speed...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID: user_level = "👑 Owner"
        elif user_id in admin_ids: user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now(): user_level = "⭐ Premium"
        else: user_level = "🆓 Free User"
        speed_msg = (f"👑 DARKWEST • SYSTEM STATUS\n━━━━━━━━━━━━━━━━━━\n⚡ Bot Speed & Status:\n\n⏱️ API Response Time: {response_time} ms\n"
                     f"🚦 Bot Status: {status}\n"
                     f"👤 Your Level: {user_level}")
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id)
    except Exception as e:
        logger.error(f"Error during speed test (cmd): {e}", exc_info=True)
        bot.edit_message_text("❌ Error during speed test.", chat_id, wait_msg.message_id)

def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📞 Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    bot.reply_to(message, "Click to contact Owner:", reply_markup=markup)

def _logic_manual_install(message):
    manual_install_module_init(message)

def _logic_help(message):
    help_text = """
🤖 **Digital World Hosting Bot Help Guide**

**📌 Basic Commands:**
• /start - Start the bot
• /help - Show this help message
• /status - Show bot statistics

**📁 File Management:**
• Upload `.py` or `.js` files directly
• Upload `.zip` archives with multiple files
• Auto-installs dependencies from `requirements.txt` or `package.json`
• Supports `npm start` for Node.js projects
• Maximum configured upload size: **50 MB** (Telegram direct download limit is 20 MB)

**📦 Module Installation:**
• Auto-install missing Python/Node modules
• Manual install via "📦 Manual Install" button
• Admin can install modules for users

**👑 Admin Features:**
• User management (ban/unban)
• Set custom file limits
• Manage mandatory channels
• Broadcast messages
• Run all user scripts

**⚙️ Tips:**
1. Make sure your scripts don't contain dangerous commands
2. Join all required channels
3. Contact owner for subscription upgrades

**👤 Owner:** @syedmuhammadakash
**📢 Updates:** @Darkwestcriminals187
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

def _logic_subscriptions_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "💳 Subscription Management\nUse inline buttons from /start or admin command menu.", reply_markup=create_subscription_menu())

def _logic_statistics(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    total_users = len(active_users)
    total_files_records = sum(len(files) for files in user_files.values())
    running_bots_count = 0
    user_running_bots = 0
    for script_key_iter, script_info_iter in list(bot_scripts.items()):
        s_owner_id, _ = script_key_iter.split('_', 1)
        if is_bot_running(int(s_owner_id), script_info_iter['file_name']):
            running_bots_count += 1
            if int(s_owner_id) == user_id:
                user_running_bots +=1
    stats_msg_base = (f"👑 DARKWEST • STATISTICS\n━━━━━━━━━━━━━━━━━━\n📊 Bot Statistics:\n\n"
                      f"👥 Total Users: {total_users}\n"
                      f"🚫 Banned Users: {len(banned_users)}\n"
                      f"📂 Total File Records: {total_files_records}\n"
                      f"🟢 Total Active Bots: {running_bots_count}\n")
    if user_id in admin_ids:
        stats_msg_admin = (f"🔒 Bot Status: {'🔴 Locked' if bot_locked else '🟢 Unlocked'}\n"
                           f"📢 Mandatory Channels: {len(mandatory_channels)}\n"
                           f"⚙️ Custom Limits: {len(user_limits)}\n"
                           f"🤖 Your Running Bots: {user_running_bots}")
        stats_msg = stats_msg_base + stats_msg_admin
    else:
        stats_msg = stats_msg_base + f"🤖 Your Running Bots: {user_running_bots}"
    bot.reply_to(message, stats_msg)

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message, "📢 Send message to broadcast to all active users.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    global bot_locked
    bot_locked = not bot_locked
    status = "locked" if bot_locked else "unlocked"
    logger.warning(f"Bot {status} by Admin {message.from_user.id} via command/button.")
    bot.reply_to(message, f"🔒 Bot has been {status}.")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "👑 Admin Panel\nManage admins. Use inline buttons from /start or admin menu.",
                 reply_markup=create_admin_panel())

def _logic_user_management(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "👥 User Management\nManage users, set limits, ban/unban.", 
                 reply_markup=create_user_management_menu())

def _logic_admin_settings(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "⚙️ Admin Settings\nSystem information and management.", 
                 reply_markup=create_admin_settings_menu())

def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, telebot.types.Message):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.chat.id
        reply_func = lambda text, **kwargs: bot.reply_to(message_or_call, text, **kwargs)
        admin_message_obj_for_script_runner = message_or_call
    elif isinstance(message_or_call, telebot.types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kwargs: bot.send_message(admin_chat_id, text, **kwargs)
        admin_message_obj_for_script_runner = message_or_call.message 
    else:
        logger.error("Invalid argument for _logic_run_all_scripts")
        return
    if admin_user_id not in admin_ids:
        reply_func("⚠️ Admin permissions required.")
        return
    reply_func("⏳ Starting process to run all user scripts. This may take a while...")
    logger.info(f"Admin {admin_user_id} initiated 'run all scripts' from chat {admin_chat_id}.")
    started_count = 0; attempted_users = 0; skipped_files = 0; error_files_details = []
    all_user_files_snapshot = dict(user_files)
    for target_user_id, files_for_user in all_user_files_snapshot.items():
        if not files_for_user: continue
        attempted_users += 1
        logger.info(f"Processing scripts for user {target_user_id}...")
        user_folder = get_user_folder(target_user_id)
        for file_name, file_type in files_for_user:
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    logger.info(f"Admin {admin_user_id} attempting to start '{file_name}' ({file_type}) for user {target_user_id}.")
                    try:
                        if file_type == 'py':
                            threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        elif file_type == 'js':
                            threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        elif file_type == 'npm':
                            threading.Thread(target=run_npm_start, args=(user_folder, target_user_id, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        elif file_type == 'php':
                            threading.Thread(target=run_php_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner), daemon=True).start()
                            started_count += 1
                        elif file_type == 'static':
                            threading.Thread(target=run_static_site, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner), daemon=True).start()
                            started_count += 1
                        else:
                            logger.warning(f"Unknown file type '{file_type}' for {file_name} (user {target_user_id}). Skipping.")
                            error_files_details.append(f"`{file_name}` (User {target_user_id}) - Unknown type")
                            skipped_files += 1
                        time.sleep(0.7)
                    except Exception as e:
                        logger.error(f"Error queueing start for '{file_name}' (user {target_user_id}): {e}")
                        error_files_details.append(f"`{file_name}` (User {target_user_id}) - Start error")
                        skipped_files += 1
                else:
                    logger.warning(f"File '{file_name}' for user {target_user_id} not found at '{file_path}'. Skipping.")
                    error_files_details.append(f"`{file_name}` (User {target_user_id}) - File not found")
                    skipped_files += 1
    summary_msg = (f"✅ All Users' Scripts - Processing Complete:\n\n"
                   f"▶️ Attempted to start: {started_count} scripts.\n"
                   f"👥 Users processed: {attempted_users}.\n")
    if skipped_files > 0:
        summary_msg += f"⚠️ Skipped/Error files: {skipped_files}\n"
        if error_files_details:
             summary_msg += "Details (first 5):\n" + "\n".join([f"  - {err}" for err in error_files_details[:5]])
             if len(error_files_details) > 5: summary_msg += "\n  ... and more (check logs)."
    reply_func(summary_msg, parse_mode='Markdown')
    logger.info(f"Run all scripts finished. Admin: {admin_user_id}. Started: {started_count}. Skipped/Errors: {skipped_files}")

def _logic_manage_mandatory_channels(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "📢 Manage Mandatory Channels\nUse the buttons below:", reply_markup=create_mandatory_channels_menu())

def _logic_admin_install(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message, "🛠️ Admin Module Installation\nSend user ID and module name (e.g., `12345678 requests`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_admin_install)

def process_admin_install(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Installation cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Format: `user_id module_name`\nExample: `12345678 requests`")
            return
        user_id = int(parts[0])
        module_name = ' '.join(parts[1:])
        if module_name.lower().startswith('npm:'):
            module_name = module_name[4:].strip()
            user_folder = get_user_folder(user_id)
            success, log = attempt_install_npm(module_name, user_folder, message, manual_request=True)
        else:
            success, log = attempt_install_pip(module_name, message, manual_request=True)
        if success:
            logger.info(f"Admin {admin_id} installed module {module_name} for user {user_id}")
            try:
                bot.send_message(user_id, f"📦 Admin installed module `{module_name}` for you.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error in admin install: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

# --- Command handlers ---
@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message): 
    if message.text == '/help':
        _logic_help(message)
    else:
        _logic_send_welcome(message)

@bot.message_handler(commands=['status'])
def command_show_status(message): _logic_statistics(message)

BUTTON_TEXT_TO_LOGIC = {
    "📢 Updates Channel": _logic_updates_channel,
    "📤 Upload File": _logic_upload_file,
    "📂 Check Files": _logic_check_files,
    "🔎 Check Live": _logic_live_projects,
    "⚡ Bot Speed": _logic_bot_speed,
    "📞 Contact Owner": _logic_contact_owner,
    "📊 Statistics": _logic_statistics, 
    "💳 Subscriptions": _logic_subscriptions_panel,
    "📢 Broadcast": _logic_broadcast_init,
    "🔒 Lock Bot": _logic_toggle_lock_bot, 
    "🟢 Running All Code": _logic_run_all_scripts,
    "👑 Admin Panel": _logic_admin_panel,
    "📢 Channel Add": _logic_manage_mandatory_channels,
    "👥 User Management": _logic_user_management,
    "🛠️ Manual Install": _logic_manual_install,
    "⚙️ Settings": _logic_admin_settings,
    "📦 Manual Install": _logic_manual_install,
    "🆘 Help": _logic_help
}

@bot.message_handler(func=lambda message: message.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    logic_func = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if logic_func: logic_func(message)
    else: logger.warning(f"Button text '{message.text}' matched but no logic func.")

@bot.message_handler(commands=['updateschannel'])
def command_updates_channel(message): _logic_updates_channel(message)
@bot.message_handler(commands=['uploadfile'])
def command_upload_file(message): _logic_upload_file(message)
@bot.message_handler(commands=['checkfiles'])
def command_check_files(message): _logic_check_files(message)
@bot.message_handler(commands=['botspeed'])
def command_bot_speed(message): _logic_bot_speed(message)
@bot.message_handler(commands=['checklive'])
def command_check_live(message): _logic_live_projects(message)
@bot.message_handler(commands=['contactowner'])
def command_contact_owner(message): _logic_contact_owner(message)
@bot.message_handler(commands=['subscriptions'])
def command_subscriptions(message): _logic_subscriptions_panel(message)
@bot.message_handler(commands=['statistics'])
def command_statistics(message): _logic_statistics(message)
@bot.message_handler(commands=['broadcast'])
def command_broadcast(message): _logic_broadcast_init(message)
@bot.message_handler(commands=['lockbot']) 
def command_lock_bot(message): _logic_toggle_lock_bot(message)
@bot.message_handler(commands=['adminpanel'])
def command_admin_panel(message): _logic_admin_panel(message)
@bot.message_handler(commands=['runningallcode'])
def command_run_all_code(message): _logic_run_all_scripts(message)
@bot.message_handler(commands=['managechannels'])
def command_manage_channels(message): _logic_manage_mandatory_channels(message)
@bot.message_handler(commands=['usermanagement'])
def command_user_management(message): _logic_user_management(message)
@bot.message_handler(commands=['manualinstall'])
def command_manual_install(message): _logic_manual_install(message)
@bot.message_handler(commands=['admininstall'])
def command_admin_install(message): _logic_admin_install(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    start_ping_time = time.time() 
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! Latency: {latency} ms", message.chat.id, msg.message_id)

# --- File upload handler ---
@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    doc = message.document
    logger.info(f"Doc from {user_id}: {doc.file_name} ({doc.mime_type}), Size: {doc.file_size}")
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked, cannot accept files.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ File limit ({current_files}/{limit_str}) reached. Delete files via /checkfiles.")
        return
    raw_file_name = doc.file_name
    if not raw_file_name: bot.reply_to(message, "⚠️ No file name. Ensure file has a name."); return
    file_name = os.path.basename(raw_file_name).replace('\\', '_')
    if file_name in ('.', '..') or not file_name:
        bot.reply_to(message, "⚠️ Invalid file name."); return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.mjs', '.cjs', '.php', '.zip']:
        bot.reply_to(message, "⚠️ Unsupported type! Allowed: `.py`, `.js`, `.mjs`, `.cjs`, `.php`, `.zip`.")
        return
    max_file_size = int(os.getenv('MAX_UPLOAD_MB', '50')) * 1024 * 1024
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"⚠️ File too large (Max: {max_file_size // 1024 // 1024} MB)."); return
    # Telegram's Bot API download_file() has a 20 MB download limit.
    if doc.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "⚠️ Telegram Bot API download_file() cannot download files larger than 20 MB. The bot limit is configured at 50 MB, but Telegram direct downloads above 20 MB are not supported.")
        return
    try:
        admin_msg = f"📥 **New file uploaded!**\n\n👤 **User:** {message.from_user.first_name} (ID: `{user_id}`)\n📄 **File:** `{file_name}`\n📦 **Size:** {doc.file_size} bytes\n📂 **Type:** {file_ext}\n🕒 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        # Actual uploaded files are forwarded ONLY to the Owner.
        # Added Admins receive notification + approval buttons only; they
        # never receive the uploaded file/document itself.
        for admin_id in admin_ids:
            if admin_id == OWNER_ID:
                continue
            try:
                bot.send_message(admin_id, admin_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        try:
            forwarded_msg = bot.forward_message(OWNER_ID, chat_id, message.message_id)

            # Save the forwarded message ID so the Owner can delete it later.
            with forwarded_files_lock:
                forwarded_files.append({
                    "chat_id": OWNER_ID,
                    "message_id": forwarded_msg.message_id,
                    "file_name": file_name,
                    "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                save_forwarded_files(forwarded_files)
        except Exception as e:
            logger.error(f"Failed to forward uploaded file to Owner {OWNER_ID}: {e}")
        download_wait_msg = bot.reply_to(message, f"⏳ Downloading `{file_name}`...")
        file_info_tg_doc = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg_doc.file_path)
        bot.edit_message_text(f"✅ Downloaded `{file_name}`. Processing...", chat_id, download_wait_msg.message_id)
        logger.info(f"Downloaded {file_name} for user {user_id}")
        user_folder = get_user_folder(user_id)
        if file_ext == '.zip':
            handle_zip_file(downloaded_file_content, file_name, message)
        else:
            # Normalize any legacy nested upload_bots/<user_id> wrapper before saving.
            _flatten_nested_hosting_wrapper(user_folder, user_id)
            if user_id in user_files:
                stale = [fn for fn, ft in user_files[user_id]
                         if os.path.basename(fn) == file_name and fn != file_name]
                for stale_name in stale:
                    remove_user_file_db(user_id, stale_name)
                    stale_path = os.path.join(user_folder, stale_name)
                    if os.path.lexists(stale_path):
                        try:
                            _delete_path_force(stale_path)
                        except Exception:
                            logger.debug('Could not remove stale uploaded path %s', stale_path, exc_info=True)
                    logger.info('Cleaned stale nested entry: %s', stale_name)
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f: f.write(downloaded_file_content)
            logger.info(f"Saved single file to {file_path}")
            is_safe, security_msg = check_code_security(file_path, file_ext[1:], user_id)
            if user_id not in TRUSTED_USERS and approval_settings.get('file_requires_approval', True):
                security_warning_msg = f"⚠️ New file needs approval:\n👤 User: {user_id}\n📁 File: {file_name}\n🟢 Status: {security_msg}"
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_file_{user_id}_{file_name}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_file_{user_id}_{file_name}")
                )
                for admin_id in admin_ids:
                    try:
                        bot.send_message(admin_id, security_warning_msg, reply_markup=markup)
                    except Exception as e:
                        logger.error(f"Failed to send approval request to admin {admin_id}: {e}")
                if user_id not in pending_files:
                    pending_files[user_id] = []
                pending_files[user_id].append([file_path, file_name, file_ext[1:]])
                bot.reply_to(message, f"⏳ File sent for admin approval. You'll be notified when approved.")
                return
            else:
                if file_ext in ('.js', '.mjs', '.cjs'): handle_js_file(file_path, user_id, user_folder, file_name, message)
                elif file_ext == '.py': handle_py_file(file_path, user_id, user_folder, file_name, message)
                elif file_ext == '.php': save_user_file(user_id, file_name, 'php'); threading.Thread(target=run_php_script, args=(file_path, user_id, user_folder, file_name, message), daemon=True).start()
    except telebot.apihelper.ApiTelegramException as e:
         logger.error(f"Telegram API Error handling file for {user_id}: {e}", exc_info=True)
         if "file is too big" in str(e).lower():
              bot.reply_to(message, f"❌ Telegram API Error: File too large to download (~20MB limit).")
         else: bot.reply_to(message, f"❌ Telegram API Error: {str(e)}. Try later.")
    except Exception as e:
        logger.error(f"❌ General error handling file for {user_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Unexpected error: {str(e)}")

# --- Callback query handler ---
@bot.callback_query_handler(func=lambda call: True) 
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data
    logger.info(f"Callback: User={user_id}, Data='{data}'")
    # Handle user-pagination here so it cannot conflict with another
    # catch-all callback handler.
    if data.startswith('users_page_'):
        handle_users_page(call)
        return
    if is_user_banned(user_id) and data not in ['back_to_main']:
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    if data not in ['check_subscription_status', 'back_to_main', 'manual_install']:
        is_subscribed, not_joined = check_mandatory_subscription(user_id)
        if not is_subscribed and user_id not in admin_ids:
            subscription_message, markup = create_subscription_check_message(not_joined)
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            except:
                bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
            return
    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats', 'check_subscription_status', 'manual_install']:
        bot.answer_callback_query(call.id, "⚠️ Bot locked by admin.", show_alert=True)
        return
    try:
        if data == 'project_token_set': _handle_project_token_callback(call, 'set')
        elif data == 'project_token_edit': _handle_project_token_callback(call, 'edit')
        elif data == 'project_admin_set': _handle_project_admin_config_callback(call, 'set')
        elif data == 'project_admin_edit': _handle_project_admin_config_callback(call, 'edit')
        elif data == 'project_admin_restart': _restart_after_manual_project_admin_edit(call)
        elif data == 'upload': upload_callback(call)
        elif data == 'check_files': check_files_callback(call)
        elif data == 'live_projects': _logic_live_projects(call.message)
        elif data.startswith('livehttp_'): live_http_callback(call)
        elif data.startswith('live_'): live_project_callback(call)
        elif data == 'noop':
            # Page-number button: intentionally does nothing.
            bot.answer_callback_query(call.id)
        elif data.startswith('file_'): file_control_callback(call)
        elif data.startswith('start_'): start_bot_callback(call)
        elif data.startswith('stop_'): stop_bot_callback(call)
        elif data.startswith('restart_'): restart_bot_callback(call)
        elif data == 'delete_forwarded_files':
            # IMPORTANT: handle this BEFORE the generic delete_* handler,
            # otherwise it is incorrectly treated as a hosted-file delete.
            owner_required_callback(call, delete_forwarded_files_callback)
        elif data.startswith('delete_'): delete_bot_callback(call)
        elif data.startswith('logs_'): logs_bot_callback(call)
        elif data == 'speed': speed_callback(call)
        elif data == 'back_to_main': back_to_main_callback(call)
        elif data.startswith('confirm_broadcast_'): handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast': handle_cancel_broadcast(call)
        elif data == 'manual_install': manual_install_callback(call)
        elif data == 'subscription': admin_required_callback(call, subscription_management_callback)
        elif data == 'stats': stats_callback(call)
        elif data == 'lock_bot': admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot': admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts': admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast': admin_required_callback(call, broadcast_init_callback) 
        elif data == 'admin_panel': admin_required_callback(call, admin_panel_callback)
        elif data == 'welcome_media_set': admin_required_callback(call, welcome_media_set_callback)
        elif data == 'welcome_media_delete': admin_required_callback(call, welcome_media_delete_callback)
        elif data == 'user_ai_provider_menu': user_ai_provider_menu_callback(call)
        elif data.startswith('user_ai_provider_select_'): user_ai_provider_select_callback(call)
        elif data == 'ai_settings': admin_required_callback(call, ai_settings_callback)
        elif data == 'ai_toggle': admin_required_callback(call, ai_toggle_callback)
        elif data == 'ai_set_key': owner_required_callback(call, ai_set_key_callback)
        elif data == 'ai_provider_menu': admin_required_callback(call, ai_provider_menu_callback)
        elif data.startswith('ai_provider_'): admin_required_callback(call, ai_provider_select_callback)
        elif data == 'ai_models': admin_required_callback(call, ai_models_callback)
        elif data.startswith('ai_model_'): admin_required_callback(call, ai_model_select_callback)
        elif data == 'ai_test': admin_required_callback(call, ai_test_callback)
        elif data.startswith('ai_test_provider_'): admin_required_callback(call, ai_test_provider_callback)
        elif data == 'approval_settings': admin_required_callback(call, approval_settings_callback)
        elif data == 'toggle_zip_approval': admin_required_callback(call, toggle_zip_approval_callback)
        elif data == 'toggle_file_approval': admin_required_callback(call, toggle_file_approval_callback)
        elif data == 'clear_all_data_confirm': owner_required_callback(call, clear_all_data_confirm_callback)
        elif data == 'clear_all_data_execute': owner_required_callback(call, clear_all_data_execute_callback)
        elif data == 'clear_all_data_cancel': admin_required_callback(call, admin_panel_callback)
        elif data == 'all_files': admin_required_callback(call, all_files_callback)
        elif data == 'add_admin': owner_required_callback(call, add_admin_init_callback) 
        elif data == 'remove_admin': owner_required_callback(call, remove_admin_init_callback) 
        elif data == 'list_admins': admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription': admin_required_callback(call, add_subscription_init_callback) 
        elif data == 'remove_subscription': admin_required_callback(call, remove_subscription_init_callback) 
        elif data == 'check_subscription': admin_required_callback(call, check_subscription_init_callback)
        elif data == 'user_management': admin_required_callback(call, user_management_callback)
        elif data == 'ban_user': admin_required_callback(call, ban_user_callback)
        elif data == 'unban_user': admin_required_callback(call, unban_user_callback)
        elif data == 'user_info': admin_required_callback(call, user_info_callback)
        elif data == 'all_users': admin_required_callback(call, all_users_callback)
        elif data == 'set_user_limit': admin_required_callback(call, set_user_limit_callback)
        elif data == 'remove_user_limit': admin_required_callback(call, remove_user_limit_callback)
        elif data == 'admin_settings': admin_required_callback(call, admin_settings_callback)
        elif data == 'system_info': admin_required_callback(call, system_info_callback)
        elif data == 'bot_performance': admin_required_callback(call, bot_performance_callback)
        elif data == 'cleanup_files': admin_required_callback(call, cleanup_files_callback)
        elif data == 'install_logs': admin_required_callback(call, install_logs_callback)
        elif data == 'admin_install': admin_required_callback(call, admin_install_callback)
        elif data == 'manage_mandatory_channels': admin_required_callback(call, manage_mandatory_channels_callback)
        elif data == 'add_mandatory_channel': admin_required_callback(call, add_mandatory_channel_callback)
        elif data == 'remove_mandatory_channel': admin_required_callback(call, remove_mandatory_channel_callback)
        elif data == 'list_mandatory_channels': admin_required_callback(call, list_mandatory_channels_callback)
        elif data.startswith('remove_channel_'): admin_required_callback(call, process_remove_channel)
        elif data == 'check_subscription_status': check_subscription_status_callback(call)
        elif data.startswith('approve_file_'): admin_required_callback(call, process_approve_file)
        elif data.startswith('reject_file_'): admin_required_callback(call, process_reject_file)
        elif data.startswith('approve_zip_'): admin_required_callback(call, process_approve_zip)
        elif data.startswith('reject_zip_'): admin_required_callback(call, process_reject_zip)
        elif data.startswith('ai_fix_yes_'): process_ai_fix_approve(call)
        elif data.startswith('ai_fix_no_'): process_ai_fix_reject(call)
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
            logger.warning(f"Unhandled callback data: {data} from user {user_id}")
    except Exception as e:
        logger.error(f"Error handling callback '{data}' for {user_id}: {e}", exc_info=True)
        try: bot.answer_callback_query(call.id, "Error processing request.", show_alert=True)
        except Exception as e_ans: logger.error(f"Failed to answer callback after error: {e_ans}")

# --- Helper callback functions ---
def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin permissions required.", show_alert=True)
        return
    func_to_run(call) 

def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Owner permissions required.", show_alert=True)
        return
    func_to_run(call)

def manual_install_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    manual_install_module_init(call.message)

def upload_callback(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.answer_callback_query(call.id, f"⚠️ File limit ({current_files}/{limit_str}) reached.", show_alert=True)
        return
    bot.answer_callback_query(call.id) 
    bot.send_message(call.message.chat.id, "📤 Send `.py`, `.js`, `.php`, `.html`, or `.zip` project.")

def check_files_callback(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    chat_id = call.message.chat.id 
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id, "⚠️ No files uploaded.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
            bot.edit_message_text("📂 Your files:\n\n(No files uploaded)", chat_id, call.message.message_id, reply_markup=markup)
        except Exception as e: logger.error(f"Error editing msg for empty file list: {e}")
        return
    bot.answer_callback_query(call.id) 
    markup = types.InlineKeyboardMarkup(row_width=1) 
    for file_name, file_type in sorted(user_files_list): 
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Running" if is_running else "🔴 Stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    try:
        bot.edit_message_text("👑 DARKWEST • MY PROJECTS\n━━━━━━━━━━━━━━━━━━\nProject manage karne ke liye select karein.", chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
         if "message is not modified" in str(e): logger.warning("Msg not modified (files).")
         else: logger.error(f"Error editing msg for file list: {e}")
    except Exception as e: logger.error(f"Unexpected error editing msg for file list: {e}", exc_info=True)

def all_files_callback(call):
    admin_id = call.from_user.id
    if admin_id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    if not user_files:
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Panel", callback_data='admin_panel'))
            bot.edit_message_text("📁 All Users Files:\n\n(No files uploaded by anyone yet)", chat_id, call.message.message_id, reply_markup=markup)
        except Exception as e: logger.error(f"Error editing empty all-files list: {e}")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for owner_id, files_list in sorted(user_files.items()):
        for file_name, file_type in sorted(files_list):
            is_running = is_bot_running(owner_id, file_name)
            status_icon = "🟢" if is_running else "🔴"
            btn_text = f"{status_icon} [{owner_id}] {file_name} ({file_type})"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{owner_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Panel", callback_data='admin_panel'))
    try:
        bot.edit_message_text("📁 All Users Files:\nClick any file to manage it.", chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e): logger.warning("Msg not modified (all-files).")
        else: logger.error(f"Error editing all-files list: {e}")
    except Exception as e: logger.error(f"Unexpected error editing all-files list: {e}", exc_info=True)

def file_control_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            logger.warning(f"User {requesting_user_id} tried to access file '{file_name}' of user {script_owner_id} without permission.")
            bot.answer_callback_query(call.id, "⚠️ You can only manage your own files.", show_alert=True)
            check_files_callback(call)
            return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            logger.warning(f"File '{file_name}' not found for user {script_owner_id} during control.")
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call) 
            return
        bot.answer_callback_query(call.id) 
        is_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_running else '🔴 Stopped'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), '?') 
        try:
            if is_running:
                script_key = f"{script_owner_id}_{file_name}"
                info = bot_scripts.get(script_key, {})
                st = info.get('start_time')
                uptime = _format_uptime(st) if st else 'Unknown'
                started = st.strftime('%d %b %Y, %I:%M:%S %p') if isinstance(st, datetime) else 'Unknown'
                controls_text = (f"⚙️ Controls for: `{file_name}` ({file_type})\n"
                                 f"Status: {status_text}\n"
                                 f"⏱ Uptime: `{uptime}`\n"
                                 f"▶️ Started: `{started}`")
            else:
                controls_text = f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: {status_text}"
            bot.edit_message_text(
                controls_text,
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_running),
                parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified (controls for {file_name})")
             else: raise 
    except (ValueError, IndexError) as ve:
        logger.error(f"Error parsing file control callback: {ve}. Data: '{call.data}'")
        bot.answer_callback_query(call.id, "Error: Invalid action data.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in file_control_callback for data '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "An error occurred.", show_alert=True)

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        logger.info(f"Start request: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied to start this script.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Error: File `{file_name}` missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name); check_files_callback(call); return
        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' already running.", show_alert=True)
            try: bot.edit_message_reply_markup(chat_id_for_reply, call.message.message_id, reply_markup=create_control_buttons(script_owner_id, file_name, True))
            except Exception as e: logger.error(f"Error updating buttons (already running): {e}")
            return
        bot.answer_callback_query(call.id, f"⏳ Attempting to start {file_name} for user {script_owner_id}...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'npm':
            threading.Thread(target=run_npm_start, args=(user_folder, script_owner_id, call.message)).start()
        elif file_type == 'php':
            threading.Thread(target=run_php_script, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_type == 'static':
            threading.Thread(target=run_static_site, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_type in {'go','rust','java','ruby','kotlin','swift','ts'}:
            threading.Thread(target=run_universal_project, args=(user_folder, script_owner_id, file_name, call.message, file_type, file_name), daemon=True).start()
        else:
             bot.send_message(chat_id_for_reply, f"❌ Error: Unknown file type '{file_type}' for '{file_name}'."); return 
        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name) 
        status_text = '🟢 Running' if is_now_running else '🟡 Starting (or failed, check logs)'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified after starting {file_name}")
             else: raise
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing start callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid start command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in start_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error starting script.", show_alert=True)
        try:
            _, script_owner_id_err_str, file_name_err = call.data.split('_', 2)
            script_owner_id_err = int(script_owner_id_err_str)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(script_owner_id_err, file_name_err, False))
        except Exception as e_btn: logger.error(f"Failed to update buttons after start error: {e_btn}")

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        logger.info(f"Stop request: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1] 
        script_key = f"{script_owner_id}_{file_name}"
        if not is_bot_running(script_owner_id, file_name): 
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' already stopped.", show_alert=True)
            try:
                 bot.edit_message_text(
                     f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: 🔴 Stopped",
                     chat_id_for_reply, call.message.message_id,
                     reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown')
            except Exception as e: logger.error(f"Error updating buttons (already stopped): {e}")
            return
        bot.answer_callback_query(call.id, f"⏳ Stopping {file_name} for user {script_owner_id}...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]; logger.info(f"Removed {script_key} from running after stop.")
        else: logger.warning(f"Script {script_key} running by psutil but not in bot_scripts dict.")
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: 🔴 Stopped",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified after stopping {file_name}")
             else: raise
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing stop callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid stop command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in stop_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error stopping script.", show_alert=True)

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        logger.info(f"Restart: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]; user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name); script_key = f"{script_owner_id}_{file_name}"
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Error: File `{file_name}` missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            if script_key in bot_scripts: del bot_scripts[script_key]
            check_files_callback(call); return
        bot.answer_callback_query(call.id, f"⏳ Restarting {file_name} for user {script_owner_id}...")
        if is_bot_running(script_owner_id, file_name):
            logger.info(f"Restart: Stopping existing {script_key}...")
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(1.5) 
        logger.info(f"Restart: Starting script {script_key}...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'npm':
            threading.Thread(target=run_npm_start, args=(user_folder, script_owner_id, call.message)).start()
        elif file_type == 'php':
            threading.Thread(target=run_php_script, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_type == 'static':
            threading.Thread(target=run_static_site, args=(file_path, script_owner_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_type in {'go','rust','java','ruby','kotlin','swift','ts'}:
            threading.Thread(target=run_universal_project, args=(user_folder, script_owner_id, file_name, call.message, file_type, file_name), daemon=True).start()
        else:
             bot.send_message(chat_id_for_reply, f"❌ Unknown type '{file_type}' for '{file_name}'."); return
        time.sleep(1.5) 
        is_now_running = is_bot_running(script_owner_id, file_name) 
        status_text = '🟢 Running' if is_now_running else '🟡 Starting (or failed)'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified (restart {file_name})")
             else: raise
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing restart callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid restart command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in restart_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error restarting.", show_alert=True)
        try:
            _, script_owner_id_err_str, file_name_err = call.data.split('_', 2)
            script_owner_id_err = int(script_owner_id_err_str)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(script_owner_id_err, file_name_err, False))
        except Exception as e_btn: logger.error(f"Failed to update buttons after restart error: {e_btn}")

def _cleanup_ai_data_for_project(user_id, file_name, user_folder):
    """Remove AI backups, hosting wrappers, pending approvals, and owner approval messages."""
    cleaned = 0
    user_folder_abs = os.path.abspath(user_folder) if user_folder else ''

    if user_folder_abs and os.path.isdir(user_folder_abs):
        for root, dirs, files in os.walk(user_folder_abs):
            for name in files:
                # AI backups and temporary files
                if (re.search(r'\.ai_backup(?:\.|$)', name) or
                        re.search(r'\.ai_tmp(?:\.|$)', name)):
                    path = os.path.join(root, name)
                    try:
                        os.remove(path)
                        cleaned += 1
                        logger.info('Removed AI artifact: %s', path)
                    except OSError as exc:
                        logger.warning('Could not delete AI artifact %s: %s', path, exc)
                # Auto-generated hosting wrappers
                elif name in ('__hosting_fastapi.py', '__hosting_flask.py',
                              '__hosting_entry.mjs', '__hosting.jar'):
                    path = os.path.join(root, name)
                    try:
                        os.remove(path)
                        cleaned += 1
                        logger.info('Removed hosting wrapper: %s', path)
                    except OSError as exc:
                        logger.warning('Could not delete hosting wrapper %s: %s', path, exc)

    # Remove matching pending repairs and their Telegram approval messages.
    for repair_id, item in list(pending_ai_repairs.items()):
        item_folder = os.path.abspath(str(item.get('user_folder', ''))) if item.get('user_folder') else ''
        if item_folder != user_folder_abs:
            continue
        approval_message_id = item.get('approval_message_id')
        chat_id = item.get('chat_id') or item.get('owner_id') or user_id
        if approval_message_id:
            try:
                bot.delete_message(int(chat_id), int(approval_message_id))
            except Exception as exc:
                logger.debug('AI approval message %s could not be deleted: %s', approval_message_id, exc)
        pending_ai_repairs.pop(repair_id, None)
        cleaned += 1
    return cleaned


def delete_bot_callback(call):
    """Delete a hosted file/project and reliably stop its process first."""
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requester = call.from_user.id
        chat_id = call.message.chat.id
        if not (requester == script_owner_id or requester in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        records = user_files.get(script_owner_id, [])
        record = next((f for f in records if f[0] == file_name), None)
        if not record:
            bot.answer_callback_query(call.id, "⚠️ File/project not found.", show_alert=True)
            check_files_callback(call)
            return
        bot.answer_callback_query(call.id, f"🗑️ Deleting {file_name}...")
        user_folder = get_user_folder(script_owner_id)

        # Remove accidental nested hosting wrapper for this owner before AI cleanup.
        nested_wrapper = os.path.join(user_folder, 'upload_bots')
        if os.path.isdir(nested_wrapper):
            _delete_path_force(nested_wrapper)
            logger.info("Removed nested hosting wrapper before AI cleanup: %s", nested_wrapper)

        ai_cleaned = _cleanup_ai_data_for_project(script_owner_id, file_name, user_folder)
        marker = _read_zip_project_marker(user_folder)
        is_zip_project = bool(marker and marker.get('entry_name') == file_name)
        if is_zip_project:
            keys = [k for k, info in list(bot_scripts.items()) if info.get('script_owner_id') == script_owner_id]
        else:
            keys = [f"{script_owner_id}_{file_name}"]
        for key in keys:
            info = bot_scripts.get(key)
            if info:
                logger.info("Delete: stopping process %s", key)
                kill_process_tree(info)
                _release_hosted_port(script_owner_id, info.get('file_name'))
                bot_scripts.pop(key, None)
        # Also release reservations left by a crashed/stopped project.
        if is_zip_project:
            _release_all_hosted_ports_for_user(script_owner_id)
        else:
            _release_hosted_port(script_owner_id, file_name)
        # Older/default reservations may still exist from legacy starts.
        _release_hosted_port(script_owner_id, 'default')
        deleted = []
        if is_zip_project:
            for name in os.listdir(user_folder):
                path_ = os.path.join(user_folder, name)
                if _delete_path_force(path_): deleted.append(name)
            remove_all_user_files_db(script_owner_id)
        else:
            file_path = os.path.join(user_folder, file_name)
            file_type = record[1] if len(record) > 1 else ''
            if file_type == 'static':
                log_names = ['static_site.log']
            elif file_name == 'npm_start' or file_type == 'npm':
                log_names = ['npm_start.log']
            else:
                # Runtime launchers write logs using the basename, even when the
                # hosted entry was stored as a nested relative path.
                base_stem = os.path.splitext(os.path.basename(file_name))[0]
                log_names = [f'{base_stem}.log']
            log_paths = [os.path.join(user_folder, name) for name in dict.fromkeys(log_names)]
            for path_, label in [(file_path, file_name)] + list(zip(log_paths, log_names)):
                if os.path.lexists(path_) and _delete_path_force(path_): deleted.append(label)
            remove_user_file_db(script_owner_id, file_name)

        # Remove empty nested directories left behind by a single-file delete.
        if os.path.isdir(user_folder):
            for root_dir, dirs, files in os.walk(user_folder, topdown=False):
                if root_dir == user_folder:
                    continue
                try:
                    if not os.listdir(root_dir):
                        os.rmdir(root_dir)
                except OSError:
                    pass
        try:
            if os.path.isdir(user_folder) and not os.listdir(user_folder): os.rmdir(user_folder)
        except OSError: pass
        text=(f"🗑️ `{file_name}` deleted successfully.\n"
              f"🛑 Process stopped/cleaned before deletion.\n"
              f"📁 Removed: {len(deleted)} item(s).\n"
              f"🤖 AI cleanup: {ai_cleaned} item(s).")
        try:
            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=None, parse_mode='Markdown')
        except Exception:
            bot.send_message(chat_id, f"🗑️ `{file_name}` deleted successfully.", parse_mode='Markdown')
    except (ValueError, IndexError):
        logger.exception("Invalid delete callback: %s", call.data)
        bot.answer_callback_query(call.id, "❌ Invalid delete command.", show_alert=True)
    except Exception as e:
        logger.exception("Delete failed for callback %s", call.data)
        bot.answer_callback_query(call.id, f"❌ Delete failed: {str(e)[:150]}", show_alert=True)

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        logger.info(f"Logs: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            check_files_callback(call)
            return
        user_folder = get_user_folder(script_owner_id)
        if file_name == 'npm_start':
            log_path = os.path.join(user_folder, 'npm_start.log')
        else:
            log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, f"⚠️ No logs for '{file_name}'.", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        try:
            log_content = ""
            file_size = os.path.getsize(log_path)
            max_log_kb = 100
            max_tg_msg = 4096
            if file_size == 0:
                log_content = "(Log empty)"
            elif file_size > max_log_kb * 1024:
                with open(log_path, 'rb') as f:
                    f.seek(-max_log_kb * 1024, os.SEEK_END)
                    log_bytes = f.read()
                log_content = log_bytes.decode('utf-8', errors='ignore')
                log_content = f"(Last {max_log_kb} KB)\n...\n" + log_content
            else:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
            if len(log_content) > max_tg_msg:
                log_content = log_content[-max_tg_msg:]
                first_nl = log_content.find('\n')
                if first_nl != -1:
                    log_content = "...\n" + log_content[first_nl+1:]
                else:
                    log_content = "...\n" + log_content
            if not log_content.strip():
                log_content = "(No visible content)"
            bot.send_message(
                chat_id_for_reply,
                f"📜 Logs for `{file_name}` (User `{script_owner_id}`):\n```\n{log_content}\n```",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error reading/sending log {log_path}: {e}", exc_info=True)
            bot.send_message(chat_id_for_reply, f"❌ Error reading log for `{file_name}`.")
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing logs callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid logs command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in logs_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error fetching logs.", show_alert=True)

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    start_cb_ping_time = time.time() 
    try:
        bot.edit_message_text("🏃 Testing speed...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing') 
        response_time = round((time.time() - start_cb_ping_time) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID: user_level = "👑 Owner"
        elif user_id in admin_ids: user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now(): user_level = "⭐ Premium"
        else: user_level = "🆓 Free User"
        speed_msg = (f"👑 DARKWEST • SYSTEM STATUS\n━━━━━━━━━━━━━━━━━━\n⚡ Bot Speed & Status:\n\n⏱️ API Response Time: {response_time} ms\n"
                     f"🚦 Bot Status: {status}\n"
                     f"👤 Your Level: {user_level}")
        bot.answer_callback_query(call.id) 
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
         logger.error(f"Error during speed test (cb): {e}", exc_info=True)
         bot.answer_callback_query(call.id, "Error in speed test.", show_alert=True)
         try: bot.edit_message_text("〽️ Main Menu", chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
         except Exception: pass

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except Exception:
            bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Owner"
    elif user_id in admin_ids:
        user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"
            expiry_info = f"\n⏳ Subscription expires in: {(expiry_date - datetime.now()).days} days"
        else:
            user_status = "🆓 Free User (Expired Sub)"
    else:
        user_status = "🆓 Free User"
    main_menu_text = (
        f"👑  DARKWEST HOSTING\n━━━━━━━━━━━━━━━━━━\n✨ Welcome back, {call.from_user.first_name}!\n\n"
        f"🆔 ID: `{user_id}`\n🔰 Status: {user_status}{expiry_info}\n"
        f"📁 Projects: {current_files} / {limit_str}\n\n"
        "━━━━━━━━━━━━━━━━━━\n💎 PROJECT CONTROL CENTER\n👇 Neeche dashboard se option select karein."
    )
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(main_menu_text, chat_id, call.message.message_id,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            logger.warning("Msg not modified (back_to_main).")
        else:
            logger.error(f"API error on back_to_main: {e}")
    except Exception as e:
        logger.error(f"Error handling back_to_main: {e}", exc_info=True)

def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("💳 Subscription Management\nSelect action:",
                              call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu())
    except Exception as e: logger.error(f"Error showing sub menu: {e}")

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message) 
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e:
        logger.error(f"Error updating menu after stats_callback: {e}")

def lock_bot_callback(call):
    global bot_locked; bot_locked = True
    logger.warning(f"Bot locked by Admin {call.from_user.id}")
    bot.answer_callback_query(call.id, "🔒 Bot locked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e: logger.error(f"Error updating menu (lock): {e}")

def unlock_bot_callback(call):
    global bot_locked; bot_locked = False
    logger.warning(f"Bot unlocked by Admin {call.from_user.id}")
    bot.answer_callback_query(call.id, "🔓 Bot unlocked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e: logger.error(f"Error updating menu (unlock): {e}")

def run_all_scripts_callback(call):
    _logic_run_all_scripts(call)

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Broadcast cancelled."); return
    broadcast_content = message.text
    if not broadcast_content and not (message.photo or message.video or message.document or message.sticker or message.voice or message.audio):
         bot.reply_to(message, "⚠️ Cannot broadcast empty message. Send text or media, or /cancel.")
         msg = bot.send_message(message.chat.id, "📢 Send broadcast message or /cancel.")
         bot.register_next_step_handler(msg, process_broadcast_message)
         return
    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ Confirm & Send", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast"))
    preview_text = broadcast_content[:1000].strip() if broadcast_content else "(Media message)"
    bot.reply_to(message, f"⚠️ Confirm Broadcast:\n\n```\n{preview_text}\n```\n" 
                          f"To **{target_count}** users. Sure?", reply_markup=markup, parse_mode='Markdown')

def handle_confirm_broadcast(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids: bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True); return
    try:
        original_message = call.message.reply_to_message
        if not original_message: raise ValueError("Could not retrieve original message.")
        broadcast_text = None
        broadcast_photo_id = None
        broadcast_video_id = None
        if original_message.text:
            broadcast_text = original_message.text
        elif original_message.photo:
            broadcast_photo_id = original_message.photo[-1].file_id
        elif original_message.video:
            broadcast_video_id = original_message.video.file_id
        else:
            raise ValueError("Message has no text or supported media for broadcast.")
        bot.answer_callback_query(call.id, "🚀 Starting broadcast...")
        bot.edit_message_text(f"📢 Broadcasting to {len(active_users)} users...",
                              chat_id, call.message.message_id, reply_markup=None)
        thread = threading.Thread(target=execute_broadcast, args=(
            broadcast_text, broadcast_photo_id, broadcast_video_id, 
            original_message.caption if (broadcast_photo_id or broadcast_video_id) else None, 
            chat_id))
        thread.start()
    except ValueError as ve: 
        logger.error(f"Error retrieving msg for broadcast confirm: {ve}")
        bot.edit_message_text(f"❌ Error starting broadcast: {ve}", chat_id, call.message.message_id, reply_markup=None)
    except Exception as e:
        logger.error(f"Error in handle_confirm_broadcast: {e}", exc_info=True)
        bot.edit_message_text("❌ Unexpected error during broadcast confirm.", chat_id, call.message.message_id, reply_markup=None)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Broadcast cancelled.")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if call.message.reply_to_message:
        try: bot.delete_message(call.message.chat.id, call.message.reply_to_message.message_id)
        except: pass

def execute_broadcast(broadcast_text, photo_id, video_id, caption, admin_chat_id):
    sent_count = 0; failed_count = 0; blocked_count = 0
    start_exec_time = time.time() 
    users_to_broadcast = list(active_users); total_users = len(users_to_broadcast)
    logger.info(f"Executing broadcast to {total_users} users.")
    batch_size = 25; delay_batches = 1.5
    for i, user_id_bc in enumerate(users_to_broadcast):
        try:
            if broadcast_text:
                bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
            elif photo_id:
                bot.send_photo(user_id_bc, photo_id, caption=caption, parse_mode='Markdown' if caption else None)
            elif video_id:
                bot.send_video(user_id_bc, video_id, caption=caption, parse_mode='Markdown' if caption else None)
            sent_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(s in err_desc for s in ["bot was blocked", "user is deactivated", "chat not found", "kicked from", "restricted"]): 
                logger.warning(f"Broadcast failed to {user_id_bc}: User blocked/inactive.")
                blocked_count += 1
            elif "flood control" in err_desc or "too many requests" in err_desc:
                retry_after = 5; match = re.search(r"retry after (\d+)", err_desc)
                if match: retry_after = int(match.group(1)) + 1 
                logger.warning(f"Flood control. Sleeping {retry_after}s...")
                time.sleep(retry_after)
                try:
                    if broadcast_text: bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
                    elif photo_id: bot.send_photo(user_id_bc, photo_id, caption=caption, parse_mode='Markdown' if caption else None)
                    elif video_id: bot.send_video(user_id_bc, video_id, caption=caption, parse_mode='Markdown' if caption else None)
                    sent_count += 1
                except Exception as e_retry: logger.error(f"Broadcast retry failed to {user_id_bc}: {e_retry}"); failed_count +=1
            else: logger.error(f"Broadcast failed to {user_id_bc}: {e}"); failed_count += 1
        except Exception as e: logger.error(f"Unexpected error broadcasting to {user_id_bc}: {e}"); failed_count += 1
        if (i + 1) % batch_size == 0 and i < total_users - 1:
            logger.info(f"Broadcast batch {i//batch_size + 1} sent. Sleeping {delay_batches}s...")
            time.sleep(delay_batches)
        elif i % 5 == 0: time.sleep(0.2) 
    duration = round(time.time() - start_exec_time, 2)
    result_msg = (f"📢 Broadcast Complete!\n\n✅ Sent: {sent_count}\n❌ Failed: {failed_count}\n"
                  f"🚫 Blocked/Inactive: {blocked_count}\n👥 Targets: {total_users}\n⏱️ Duration: {duration}s")
    logger.info(result_msg)
    try: bot.send_message(admin_chat_id, result_msg)
    except Exception as e: logger.error(f"Failed to send broadcast result to admin {admin_chat_id}: {e}")

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👑 DARKWEST • ADMIN CONTROL CENTER\n━━━━━━━━━━━━━━━━━━\nManage admins and hosting controls securely.",
                              call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except Exception as e: logger.error(f"Error showing admin panel: {e}")

def delete_forwarded_files_callback(call):
    """Owner-only: delete forwarded file messages that this bot has tracked."""
    bot.answer_callback_query(call.id)

    with forwarded_files_lock:
        entries = list(forwarded_files)

    if not entries:
        try:
            bot.send_message(
                call.message.chat.id,
                "ℹ️ No tracked forwarded files found.\n\n"
                "⚠️ Files forwarded before this tracking feature was enabled cannot be "
                "identified automatically by the Telegram Bot API."
            )
        except Exception as e:
            logger.error(f"Failed to send delete status: {e}")
        return

    deleted = 0
    failed = 0
    remaining = []

    for entry in entries:
        try:
            bot.delete_message(entry["chat_id"], entry["message_id"])
            deleted += 1
        except Exception as e:
            failed += 1
            remaining.append(entry)
            logger.warning(
                f"Could not delete forwarded message "
                f"{entry.get('chat_id')}:{entry.get('message_id')}: {e}"
            )

    with forwarded_files_lock:
        forwarded_files.clear()
        forwarded_files.extend(remaining)
        save_forwarded_files(forwarded_files)

    status = (
        "🗑️ <b>Delete Forwarded Files Result</b>\n\n"
        f"✅ Deleted: <b>{deleted}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"📦 Remaining tracked: <b>{len(remaining)}</b>"
    )
    if failed:
        status += "\n\n⚠️ Some messages could not be deleted (for example, "
        status += "they may already be deleted or the bot may lack permission)."
    try:
        bot.send_message(call.message.chat.id, status, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Failed to send delete result: {e}")

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID to promote to Admin.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    owner_id_check = message.from_user.id 
    if owner_id_check != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Admin promotion cancelled."); return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0: raise ValueError("ID must be positive")
        if new_admin_id == OWNER_ID: bot.reply_to(message, "⚠️ Owner is already Owner."); return
        if new_admin_id in admin_ids: bot.reply_to(message, f"⚠️ User `{new_admin_id}` already Admin."); return
        add_admin_db(new_admin_id, owner_id_check) 
        logger.warning(f"Admin {new_admin_id} added by Owner {owner_id_check}.")
        bot.reply_to(message, f"✅ User `{new_admin_id}` promoted to Admin.")
        try: bot.send_message(new_admin_id, "🎉 Congrats! You are now an Admin.")
        except Exception as e: logger.error(f"Failed to notify new admin {new_admin_id}: {e}")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Enter User ID to promote or /cancel.")
        bot.register_next_step_handler(msg, process_add_admin_id)
    except Exception as e: logger.error(f"Error processing add admin: {e}", exc_info=True); bot.reply_to(message, "Error.")

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID of Admin to remove.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    owner_id_check = message.from_user.id
    if owner_id_check != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Admin removal cancelled."); return
    try:
        admin_id_remove = int(message.text.strip())
        if admin_id_remove <= 0: raise ValueError("ID must be positive")
        if admin_id_remove == OWNER_ID: bot.reply_to(message, "⚠️ Owner cannot remove self."); return
        if admin_id_remove not in admin_ids: bot.reply_to(message, f"⚠️ User `{admin_id_remove}` not Admin."); return
        if remove_admin_db(admin_id_remove): 
            logger.warning(f"Admin {admin_id_remove} removed by Owner {owner_id_check}.")
            bot.reply_to(message, f"✅ Admin `{admin_id_remove}` removed.")
            try: bot.send_message(admin_id_remove, "ℹ️ You are no longer an Admin.")
            except Exception as e: logger.error(f"Failed to notify removed admin {admin_id_remove}: {e}")
        else: bot.reply_to(message, f"❌ Failed to remove admin `{admin_id_remove}`. Check logs.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Enter Admin ID to remove or /cancel.")
        bot.register_next_step_handler(msg, process_remove_admin_id)
    except Exception as e: logger.error(f"Error processing remove admin: {e}", exc_info=True); bot.reply_to(message, "Error.")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(f"- `{aid}` {'(Owner)' if aid == OWNER_ID else ''}" for aid in sorted(list(admin_ids)))
        if not admin_list_str: admin_list_str = "(No Owner/Admins configured!)"
        bot.edit_message_text(f"👑 Current Admins:\n\n{admin_list_str}", call.message.chat.id,
                              call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception as e: logger.error(f"Error listing admins: {e}")

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID & days (e.g., `12345678 30`).\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    admin_id_check = message.from_user.id 
    if admin_id_check not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Sub add cancelled."); return
    try:
        parts = message.text.split();
        if len(parts) != 2: raise ValueError("Incorrect format")
        sub_user_id = int(parts[0].strip()); days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0: raise ValueError("User ID/days must be positive")
        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date_new_sub = datetime.now()
        if current_expiry and current_expiry > start_date_new_sub: start_date_new_sub = current_expiry
        new_expiry = start_date_new_sub + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)
        logger.info(f"Sub for {sub_user_id} by admin {admin_id_check}. Expiry: {new_expiry:%Y-%m-%d}")
        bot.reply_to(message, f"✅ Sub for `{sub_user_id}` by {days} days.\nNew expiry: {new_expiry:%Y-%m-%d}")
        try: bot.send_message(sub_user_id, f"🎉 Sub activated/extended by {days} days! Expires: {new_expiry:%Y-%m-%d}.")
        except Exception as e: logger.error(f"Failed to notify {sub_user_id} of new sub: {e}")
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid: {e}. Format: `ID days` or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID & days, or /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)
    except Exception as e: logger.error(f"Error processing add sub: {e}", exc_info=True); bot.reply_to(message, "Error.")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID to remove sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Sub removal cancelled."); return
    try:
        sub_user_id_remove = int(message.text.strip())
        if sub_user_id_remove <= 0: raise ValueError("ID must be positive")
        if sub_user_id_remove not in user_subscriptions:
            bot.reply_to(message, f"⚠️ User `{sub_user_id_remove}` no active sub in memory."); return
        remove_subscription_db(sub_user_id_remove) 
        logger.warning(f"Sub removed for {sub_user_id_remove} by admin {admin_id_check}.")
        bot.reply_to(message, f"✅ Sub for `{sub_user_id_remove}` removed.")
        try: bot.send_message(sub_user_id_remove, "ℹ️ Your subscription removed by admin.")
        except Exception as e: logger.error(f"Failed to notify {sub_user_id_remove} of sub removal: {e}")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID to remove sub from, or /cancel.")
        bot.register_next_step_handler(msg, process_remove_subscription_id)
    except Exception as e: logger.error(f"Error processing remove sub: {e}", exc_info=True); bot.reply_to(message, "Error.")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID to check sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Sub check cancelled."); return
    try:
        sub_user_id_check = int(message.text.strip())
        if sub_user_id_check <= 0: raise ValueError("ID must be positive")
        if sub_user_id_check in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id_check].get('expiry')
            if expiry_dt:
                if expiry_dt > datetime.now():
                    days_left = (expiry_dt - datetime.now()).days
                    bot.reply_to(message, f"✅ User `{sub_user_id_check}` active sub.\nExpires: {expiry_dt:%Y-%m-%d %H:%M:%S} ({days_left} days left).")
                else:
                    bot.reply_to(message, f"⚠️ User `{sub_user_id_check}` expired sub (On: {expiry_dt:%Y-%m-%d %H:%M:%S}).")
                    remove_subscription_db(sub_user_id_check)
            else: bot.reply_to(message, f"⚠️ User `{sub_user_id_check}` in sub list, but expiry missing. Re-add if needed.")
        else: bot.reply_to(message, f"ℹ️ User `{sub_user_id_check}` no active sub record.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID to check, or /cancel.")
        bot.register_next_step_handler(msg, process_check_subscription_id)
    except Exception as e: logger.error(f"Error processing check sub: {e}", exc_info=True); bot.reply_to(message, "Error.")

def user_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👥 User Management\nSelect action:", call.message.chat.id, 
                              call.message.message_id, reply_markup=create_user_management_menu())
    except Exception as e: logger.error(f"Error showing user management menu: {e}")

def ban_user_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🚫 Enter User ID to ban and reason (e.g., `12345678 Spamming`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Ban cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Format: `user_id reason`\nExample: `12345678 Spamming`")
            return
        user_id = int(parts[0])
        reason = ' '.join(parts[1:])
        if user_id <= 0: raise ValueError("ID must be positive")
        if user_id == OWNER_ID: bot.reply_to(message, "⚠️ Cannot ban owner."); return
        if user_id in admin_ids: bot.reply_to(message, "⚠️ Cannot ban admin."); return
        if ban_user_db(user_id, reason, admin_id):
            bot.reply_to(message, f"✅ User `{user_id}` banned.\nReason: {reason}")
            for file_name, _ in user_files.get(user_id, []):
                script_key = f"{user_id}_{file_name}"
                if script_key in bot_scripts:
                    kill_process_tree(bot_scripts[script_key])
                    del bot_scripts[script_key]
            try:
                bot.send_message(user_id, f"🚫 You have been banned from using this bot.\nReason: {reason}")
            except Exception as e:
                logger.error(f"Failed to notify banned user {user_id}: {e}")
        else:
            bot.reply_to(message, "❌ Failed to ban user.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error banning user: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def unban_user_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "✅ Enter User ID to unban\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Unban cancelled.")
        return
    try:
        user_id = int(message.text.strip())
        if user_id <= 0: raise ValueError("ID must be positive")
        if user_id not in banned_users:
            bot.reply_to(message, f"ℹ️ User `{user_id}` is not banned.")
            return
        if unban_user_db(user_id):
            bot.reply_to(message, f"✅ User `{user_id}` unbanned.")
            try:
                bot.send_message(user_id, "✅ Your ban has been lifted. You can now use the bot again.")
            except Exception as e:
                logger.error(f"Failed to notify unbanned user {user_id}: {e}")
        else:
            bot.reply_to(message, "❌ Failed to unban user.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def user_info_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👤 Enter User ID to get info\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_user_info)

def process_user_info(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Info request cancelled.")
        return
    try:
        user_id = int(message.text.strip())
        if user_id <= 0: raise ValueError("ID must be positive")
        info_parts = []
        info_parts.append(f"👤 **User ID:** `{user_id}`")
        if user_id == OWNER_ID:
            info_parts.append("👑 **Status:** Owner")
        elif user_id in admin_ids:
            info_parts.append("🛡️ **Status:** Admin")
        elif user_id in banned_users:
            info_parts.append("🚫 **Status:** Banned")
        elif user_id in user_subscriptions:
            expiry = user_subscriptions[user_id].get('expiry')
            if expiry and expiry > datetime.now():
                days_left = (expiry - datetime.now()).days
                info_parts.append(f"⭐ **Status:** Premium (Expires in {days_left} days)")
            else:
                info_parts.append("🆓 **Status:** Free User (Expired subscription)")
        else:
            info_parts.append("🆓 **Status:** Free User")
        file_count = get_user_file_count(user_id)
        file_limit = get_user_file_limit(user_id)
        info_parts.append(f"📁 **Files:** {file_count}/{file_limit if file_limit != float('inf') else 'Unlimited'}")
        if user_id in user_limits:
            info_parts.append(f"⚙️ **Custom Limit:** {user_limits[user_id]}")
        running_scripts = 0
        for file_name, _ in user_files.get(user_id, []):
            if is_bot_running(user_id, file_name):
                running_scripts += 1
        info_parts.append(f"🤖 **Running Scripts:** {running_scripts}")
        if user_id in active_users:
            info_parts.append("🟢 **Status:** Active")
        info_text = "\n".join(info_parts)
        bot.reply_to(message, info_text, parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error getting user info: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def all_users_callback(call):
    bot.answer_callback_query(call.id)
    try:
        if not active_users:
            bot.edit_message_text("👥 No active users yet.", call.message.chat.id, call.message.message_id)
            return
        users_list = list(active_users)
        chunk_size = 20
        total_pages = (len(users_list) + chunk_size - 1) // chunk_size
        current_page = 0
        display_users_list(call.message.chat.id, call.message.message_id, users_list, current_page, total_pages, chunk_size)
    except Exception as e:
        logger.error(f"Error displaying all users: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error displaying users.", show_alert=True)

def display_users_list(chat_id, message_id, users_list, page, total_pages, chunk_size):
    start_idx = page * chunk_size
    end_idx = min(start_idx + chunk_size, len(users_list))
    user_chunk = users_list[start_idx:end_idx]
    message_text = f"👥 **Active Users** (Page {page + 1}/{total_pages})\n\n"
    for i, user_id in enumerate(user_chunk, start=start_idx + 1):
        status = ""
        if user_id == OWNER_ID: status = "👑"
        elif user_id in admin_ids: status = "🛡️"
        elif user_id in banned_users: status = "🚫"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            status = "⭐"
        else: status = "🆓"
        message_text += f"{i}. `{user_id}` {status}\n"
    markup = types.InlineKeyboardMarkup(row_width=3)
    if total_pages > 1:
        page_buttons = []
        if page > 0:
            page_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
        page_buttons.append(types.InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            page_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
        markup.row(*page_buttons)
    markup.row(types.InlineKeyboardButton("🔙 Back to User Management", callback_data='user_management'))
    try:
        bot.edit_message_text(message_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error editing users list: {e}")

def handle_users_page(call):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True)
        return
    try:
        page = int(call.data.split('_')[2])
        users_list = list(active_users)
        chunk_size = 20
        total_pages = (len(users_list) + chunk_size - 1) // chunk_size
        if 0 <= page < total_pages:
            bot.answer_callback_query(call.id)
            display_users_list(call.message.chat.id, call.message.message_id, users_list, page, total_pages, chunk_size)
    except Exception as e:
        logger.error(f"Error handling users page: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error.", show_alert=True)

def set_user_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔧 Enter User ID and new limit (e.g., `12345678 50`)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_set_user_limit)

def process_set_user_limit(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Limit set cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError("Format: user_id limit")
        user_id = int(parts[0])
        limit = int(parts[1])
        if user_id <= 0 or limit <= 0: raise ValueError("ID and limit must be positive")
        if set_user_limit_db(user_id, limit, admin_id):
            bot.reply_to(message, f"✅ Set file limit {limit} for user `{user_id}`")
            try:
                bot.send_message(user_id, f"⚙️ Your file upload limit has been set to {limit}")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            bot.reply_to(message, "❌ Failed to set limit.")
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid input: {e}\nFormat: `user_id limit`")
    except Exception as e:
        logger.error(f"Error setting user limit: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def remove_user_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🗑️ Enter User ID to remove custom limit\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_remove_user_limit)

def process_remove_user_limit(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Limit removal cancelled.")
        return
    try:
        user_id = int(message.text.strip())
        if user_id <= 0: raise ValueError("ID must be positive")
        if user_id not in user_limits:
            bot.reply_to(message, f"ℹ️ User `{user_id}` has no custom limit.")
            return
        if remove_user_limit_db(user_id):
            bot.reply_to(message, f"✅ Removed custom limit for user `{user_id}`")
            try:
                bot.send_message(user_id, "⚙️ Your custom file limit has been removed")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            bot.reply_to(message, "❌ Failed to remove limit.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid user ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error removing user limit: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def ai_settings_callback(call):
    bot.answer_callback_query(call.id)
    provider = _friendly_ai_provider(_provider_for_user(call.from_user.id))
    status = '🟢 Enabled' if ai_settings.get('enabled', True) else '🔴 Disabled'
    text = f'🛡️ <b>Darkwest AI Fixing</b>\n\n{provider}\nStatus: {status}\nAuto analysis, safe fixes and owner approval are enabled.'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=create_ai_settings_menu(call.from_user.id), parse_mode='HTML')


def user_ai_provider_menu_callback(call):
    """Show the AI provider selector to ordinary users."""
    bot.answer_callback_query(call.id)
    provider = _friendly_ai_provider(_provider_for_user(call.from_user.id))
    text = (f'🛡️ <b>Darkwest AI Fixing</b>\n\n'
            f'Current: <b>{_html_escape(provider)}</b>\n'
            'Select your AI engine:')
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=create_ai_provider_menu_for_user(call.from_user.id),
        parse_mode='HTML'
    )


def user_ai_provider_select_callback(call):
    """Save an AI provider selected by a normal user."""
    provider = call.data[len('user_ai_provider_select_'):].strip().lower()
    if provider not in AI_PROVIDER_NAMES:
        bot.answer_callback_query(call.id, 'Unsupported AI provider', show_alert=True)
        return
    user_ai_provider[str(call.from_user.id)] = provider
    _save_json_settings(AI_PROVIDER_SETTINGS_PATH, user_ai_provider)
    bot.answer_callback_query(call.id, 'AI provider selected')
    text = (f'🛡️ <b>Darkwest AI Fixing</b>\n\n'
            f'Current: <b>{_html_escape(AI_PROVIDER_NAMES[provider])}</b>\n'
            'Select your AI engine:')
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        reply_markup=create_ai_provider_menu_for_user(call.from_user.id),
        parse_mode='HTML'
    )


def ai_provider_menu_callback(call):
    bot.answer_callback_query(call.id)
    provider = _friendly_ai_provider(_provider_for_user(call.from_user.id))
    text = f'🛡️ <b>Darkwest AI Fixing</b>\n\nCurrent: <b>{_html_escape(provider)}</b>\nSelect your AI engine:'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=create_ai_provider_menu_for_user(call.from_user.id), parse_mode='HTML')

def ai_toggle_callback(call):
    ai_settings['enabled'] = not ai_settings.get('enabled', True)
    _save_json_settings(AI_SETTINGS_PATH, ai_settings)
    bot.answer_callback_query(call.id, 'AI Auto-Fix updated')
    ai_settings_callback(call)

def ai_set_key_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, '🔑 Send Direct AI API key.\n/cancel to abort.')
    bot.register_next_step_handler(msg, process_ai_set_key)

def process_ai_set_key(message):
    global OPENROUTER_API_KEY
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, '⚠️ Owner only.')
        return
    raw_value = str(message.text or '')
    value = re.sub(r'\s+', '', raw_value.strip().strip('`').replace('`', ''))
    if value.lower() == '/cancel':
        bot.reply_to(message, '❌ Cancelled.')
        return
    if len(value) < 20 or value == 'PASTE_NEW_OPENROUTER_API_KEY_HERE':
        bot.reply_to(message, '⚠️ Invalid OpenRouter API key.')
        return
    if not value.startswith('sk-or-'):
        bot.reply_to(message, '⚠️ This does not look like an OpenRouter key. OpenRouter keys start with sk-or-.')
        return
    OPENROUTER_API_KEY = value
    ai_settings['api_key'] = value
    ai_settings['enabled'] = True
    if not _save_json_settings(AI_SETTINGS_PATH, ai_settings):
        bot.reply_to(message, '❌ Key could not be saved to AI settings.')
        return
    try: bot.delete_message(message.chat.id, message.message_id)
    except Exception: pass
    bot.send_message(message.chat.id, '✅ Direct AI key saved. Use 🧪 Test AI to verify it.')

def ai_models_callback(call):
    bot.answer_callback_query(call.id)
    current_model = _html_escape(OPENROUTER_MODEL.split('/')[-1])
    text = f'🛡️ <b>Darkwest AI Fixing</b>\n\n🧠 Direct AI Model\nCurrent: <b>{current_model}</b>'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=create_ai_model_menu(), parse_mode='HTML')

def ai_model_select_callback(call):
    global OPENROUTER_MODEL
    model = call.data[len('ai_model_'):].replace('__', '/')
    allowed = ALLOWED_AI_MODELS
    if model not in allowed:
        bot.answer_callback_query(call.id, 'Unsupported model', show_alert=True)
        return
    OPENROUTER_MODEL = model
    ai_settings['model'] = model
    _save_json_settings(AI_SETTINGS_PATH, ai_settings)
    bot.answer_callback_query(call.id, 'Model selected')
    ai_models_callback(call)

def create_ai_test_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('💀 WormGPT', callback_data='ai_test_provider_wormgpt'),
        types.InlineKeyboardButton('⚡ DeepSeek V4', callback_data='ai_test_provider_deepseek')
    )
    markup.row(
        types.InlineKeyboardButton('🧠 Qwen LLM', callback_data='ai_test_provider_qwen'),
        types.InlineKeyboardButton('🔀 Direct AI', callback_data='ai_test_provider_router')
    )
    markup.row(types.InlineKeyboardButton('◀️ Back', callback_data='ai_settings'))
    return markup

def ai_test_callback(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        '🛡️ <b>Darkwest AI Fixing</b>\n\n🧪 Testing connection\nSelect a provider to run a live API check:',
        call.message.chat.id, call.message.message_id, reply_markup=create_ai_test_menu(), parse_mode='HTML'
    )

def _test_ai_provider_direct(provider):
    prompt = 'Reply only: OK'
    provider = str(provider or '').strip().lower()
    if provider == 'router':
        api_key = re.sub(r'\s+', '', str(OPENROUTER_API_KEY or '').strip().strip('`').replace('`', ''))
        if not api_key or not api_key.startswith('sk-or-'):
            return False
        result = _openrouter_request([
            {'role': 'system', 'content': 'Reply only with OK.'},
            {'role': 'user', 'content': prompt},
        ])
        return bool(result and result != 'AI service temporarily unavailable')
    endpoint = AI_PROVIDER_ENDPOINTS.get(provider)
    if not endpoint:
        return False
    try:
        response = requests.get(endpoint, params={'prompt': prompt}, timeout=30)
        if response.status_code != 200:
            return False
        data = response.json()
        if not isinstance(data, dict) or not data.get('success'):
            return False
        text = data.get('answer') if provider == 'wormgpt' else data.get('response')
        text = _strip_think_tags(text)
        return bool(text)
    except Exception as exc:
        logger.warning('AI provider test failed for %s: %s', provider, exc)
        return False

def ai_test_provider_callback(call):
    provider = call.data[len('ai_test_provider_'):].strip().lower()
    if provider not in AI_PROVIDER_NAMES:
        bot.answer_callback_query(call.id, 'Invalid provider', show_alert=True)
        return
    bot.answer_callback_query(call.id, 'Testing live API...')
    ok = _test_ai_provider_direct(provider)
    name = _friendly_ai_provider(provider)
    if ok:
        text = f'🛡️ <b>Darkwest AI Fixing</b>\n🧪 Testing connection...\n\nProvider: {name}\nStatus: 🟢 Connected\nLive API response received.'
    else:
        text = f'🛡️ <b>Darkwest AI Fixing</b>\n🧪 Testing connection...\n\nProvider: {name}\nStatus: 🔴 Unavailable\nLive API did not return a valid response.'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_ai_test_menu(), parse_mode='HTML')

def approval_settings_callback(call):
    bot.answer_callback_query(call.id)
    text = ('🛡️ <b>APPROVAL SYSTEM</b>\n\n'
            'ZIP uploads can require admin approval before extraction/start.\n'
            'You can also enable automatic approval when desired.')
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_approval_settings_menu(), parse_mode='HTML')

def toggle_zip_approval_callback(call):
    approval_settings['zip_requires_approval'] = not approval_settings.get('zip_requires_approval', True)
    _save_json_settings(APPROVAL_SETTINGS_PATH, approval_settings)
    bot.answer_callback_query(call.id, 'ZIP approval updated')
    approval_settings_callback(call)

def toggle_file_approval_callback(call):
    approval_settings['file_requires_approval'] = not approval_settings.get('file_requires_approval', True)
    _save_json_settings(APPROVAL_SETTINGS_PATH, approval_settings)
    bot.answer_callback_query(call.id, 'File approval updated')
    approval_settings_callback(call)

def clear_all_data_confirm_callback(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('🧨 YES, CLEAR ALL', callback_data='clear_all_data_execute'), types.InlineKeyboardButton('❌ CANCEL', callback_data='clear_all_data_cancel'))
    bot.edit_message_text('⚠️ <b>PERMANENT DATA RESET</b>\n\nThis removes hosted user files/projects, subscriptions, user records, bans, limits, installation logs, pending approvals and tracked forwarded-file records. Owner/admin accounts are preserved.\n\nContinue?', call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

def clear_all_data_execute_callback(call):
    global user_subscriptions, user_files, active_users, banned_users, user_limits, pending_modules, manual_install_requests, mandatory_channels, pending_zip_files, pending_files, forwarded_files, bot_scripts
    bot.answer_callback_query(call.id, 'Resetting data...')
    for key, info in list(bot_scripts.items()):
        try:
            proc = info.get('process') if isinstance(info, dict) else info
            if proc and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=3)
                except Exception: proc.kill()
        except Exception as e: logger.warning('Could not stop process during reset: %s', e)
    bot_scripts.clear()
    for name in os.listdir(UPLOAD_BOTS_DIR):
        path = os.path.join(UPLOAD_BOTS_DIR, name)
        try:
            if os.path.isdir(path): shutil.rmtree(path, ignore_errors=True)
            else: os.remove(path)
        except Exception as e: logger.warning('Could not remove %s: %s', path, e)
    os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        cur = conn.cursor()
        for table in ('subscriptions','user_files','active_users','banned_users','user_limits','mandatory_channels','install_logs'):
            cur.execute(f'DELETE FROM {table}')
        conn.commit(); conn.close()
    user_subscriptions.clear(); user_files.clear(); active_users.clear(); banned_users.clear(); user_limits.clear()
    for _repair_item in list(pending_ai_repairs.values()):
        _cleanup_ai_data_for_project(
            _repair_item.get('owner_id', 0),
            _repair_item.get('file_name', ''),
            _repair_item.get('user_folder', '')
        )
    pending_modules.clear(); manual_install_requests.clear(); mandatory_channels.clear(); pending_zip_files.clear(); pending_files.clear(); pending_ai_repairs.clear()
    with _HOSTED_PORT_LOCK:
        _HOSTED_PORT_RESERVATIONS.clear()
    with forwarded_files_lock:
        forwarded_files.clear(); save_forwarded_files([])
    init_db()
    bot.edit_message_text('✅ <b>ALL USER DATA CLEARED</b>\n\nFresh state restored. Owner/Admin accounts were preserved.', call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='HTML')

def admin_settings_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("⚙️ Admin Settings\nSelect action:", call.message.chat.id, 
                              call.message.message_id, reply_markup=create_admin_settings_menu())
    except Exception as e: logger.error(f"Error showing admin settings: {e}")

def _fmt_bytes(n):
    n=float(n)
    for unit in ('B','KB','MB','GB','TB'):
        if n < 1024: return f'{n:.1f} {unit}'
        n/=1024
    return f'{n:.1f} PB'

def system_info_callback(call):
    bot.answer_callback_query(call.id)
    try:
        import platform
        vm=psutil.virtual_memory(); disk=psutil.disk_usage('/'); uptime=max(0,int(time.time()-psutil.boot_time()))
        mins,sec=divmod(uptime,60); hrs,mins=divmod(mins,60); days,hrs=divmod(hrs,24)
        cpu=psutil.cpu_percent(interval=0.4)
        text=(f'🖥️ <b>VPS SYSTEM INFO</b>\n\n'
              f'🧩 OS: <code>{platform.system()} {platform.release()}</code>\n'
              f'🐍 Python: <code>{platform.python_version()}</code>\n'
              f'🏷️ Host: <code>{socket.gethostname()}</code>\n'
              f'⚙️ CPU: <code>{psutil.cpu_count(logical=True)} cores</code> / {cpu}%\n'
              f'🧠 RAM: <code>{_fmt_bytes(vm.used)} / {_fmt_bytes(vm.total)}</code> ({vm.percent}%)\n'
              f'💾 Disk: <code>{_fmt_bytes(disk.used)} / {_fmt_bytes(disk.total)}</code> ({disk.percent}%)\n'
              f'⏱️ VPS Uptime: <code>{days}d {hrs:02d}h {mins:02d}m {sec:02d}s</code>\n'
              f'🤖 Running Projects: <code>{len(bot_scripts)}</code>\n'
              f'👥 Active Users: <code>{len(active_users)}</code>\n'
              f'📦 Stored Files: <code>{sum(len(v) for v in user_files.values())}</code>')
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_admin_settings_menu(), parse_mode='HTML')
    except Exception as e:
        logger.error('System info error: %s',e,exc_info=True); bot.send_message(call.message.chat.id,f'❌ System info error: {e}')

def bot_performance_callback(call):
    bot.answer_callback_query(call.id)
    try:
        proc=psutil.Process(); vm=psutil.virtual_memory(); disk=psutil.disk_usage('/')
        rss=proc.memory_info().rss; cpu=proc.cpu_percent(interval=0.5)
        total=sum(len(v) for v in user_files.values()); running=len(bot_scripts); ratio=(running/total*100) if total else 0
        text=(f'📈 <b>BOT PERFORMANCE</b>\n\n'
              f'🚀 Running: <code>{running}</code>\n'
              f'📦 Total Files: <code>{total}</code>\n'
              f'📊 Running Ratio: <code>{ratio:.1f}%</code>\n'
              f'🧮 Bot CPU: <code>{cpu:.1f}%</code>\n'
              f'💾 Bot RAM: <code>{_fmt_bytes(rss)}</code>\n'
              f'🧠 VPS RAM: <code>{vm.percent}%</code>\n'
              f'💽 VPS Disk: <code>{disk.percent}%</code>\n'
              f'👥 Active Users: <code>{len(active_users)}</code>\n'
              f'💳 Subscriptions: <code>{len(user_subscriptions)}</code>\n'
              f'🚫 Banned: <code>{len(banned_users)}</code>\n'
              f'🛠️ Custom Limits: <code>{len(user_limits)}</code>')
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_admin_settings_menu(), parse_mode='HTML')
    except Exception as e:
        logger.error('Performance error: %s',e,exc_info=True); bot.send_message(call.message.chat.id,f'❌ Performance error: {e}')

def cleanup_files_callback(call):
    bot.answer_callback_query(call.id, "🧹 Cleaning up temporary files...")
    try:
        cleaned_dirs = 0
        cleaned_files = 0
        for user_dir in os.listdir(UPLOAD_BOTS_DIR):
            user_path = os.path.join(UPLOAD_BOTS_DIR, user_dir)
            if os.path.isdir(user_path):
                if not os.listdir(user_path):
                    try:
                        os.rmdir(user_path)
                        cleaned_dirs += 1
                    except Exception as e:
                        logger.error(f"Error removing empty dir {user_path}: {e}")
                else:
                    for file_name in os.listdir(user_path):
                        if file_name.endswith('.log'):
                            file_path = os.path.join(user_path, file_name)
                            try:
                                file_age = time.time() - os.path.getmtime(file_path)
                                if file_age > 7 * 24 * 3600:
                                    os.remove(file_path)
                                    cleaned_files += 1
                            except Exception as e:
                                logger.error(f"Error cleaning log file {file_path}: {e}")
        result_msg = f"🧹 **Cleanup Complete:**\n• Removed empty directories: {cleaned_dirs}\n• Cleared old log files: {cleaned_files}"
        try:
            bot.edit_message_text(result_msg, call.message.chat.id, call.message.message_id,
                                  reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e).lower():
                logger.info("Cleanup finished; Telegram message was already up to date.")
            else:
                raise
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        try:
            bot.edit_message_text(f"❌ Cleanup error: {str(e)}", call.message.chat.id, call.message.message_id)
        except telebot.apihelper.ApiTelegramException as edit_err:
            if "message is not modified" not in str(edit_err).lower():
                logger.error(f"Failed to show cleanup error: {edit_err}")

def install_logs_callback(call):
    bot.answer_callback_query(call.id)
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('SELECT user_id, module_name, package_name, status, install_date FROM install_logs ORDER BY install_date DESC LIMIT 20')
            logs = c.fetchall()
            conn.close()
        if not logs:
            bot.edit_message_text("📋 **No installation logs found**", call.message.chat.id, 
                                  call.message.message_id, reply_markup=create_admin_settings_menu())
            return
        log_text = "📋 **Recent Installation Logs (Last 20):**\n\n"
        for user_id, module_name, package_name, status, install_date in logs:
            status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
            log_text += f"{status_icon} `{user_id}`: {module_name} -> {package_name}\n"
            log_text += f"   📅 {install_date[:19]}\n\n"
        bot.edit_message_text(log_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error showing install logs: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error showing logs.", show_alert=True)

def admin_install_callback(call):
    bot.answer_callback_query(call.id)
    _logic_admin_install(call.message)

def manage_mandatory_channels_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("📢 Manage Mandatory Channels\nChoose desired action:",
                              call.message.chat.id, call.message.message_id, 
                              reply_markup=create_mandatory_channels_menu())
    except Exception as e:
        logger.error(f"Error showing channel management menu: {e}")

def add_mandatory_channel_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send channel ID or username (example: @channel_username or -1001234567890)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Channel addition cancelled.")
        return
    channel_identifier = message.text.strip()
    try:
        chat = bot.get_chat(channel_identifier)
        channel_id = str(chat.id)
        channel_username = f"@{chat.username}" if chat.username else ""
        channel_name = chat.title
        try:
            bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
            if bot_member.status not in ['administrator', 'creator']:
                bot.reply_to(message, f"❌ Bot is not admin in the channel! Must be promoted first.")
                return
        except Exception as e:
            bot.reply_to(message, f"❌ Bot is not admin in the channel or cannot access it!")
            return
        if save_mandatory_channel(channel_id, channel_username, channel_name, admin_id):
            bot.reply_to(message, f"✅ Mandatory channel added:\n**{channel_name}**\n{channel_username or channel_id}")
        else:
            bot.reply_to(message, "❌ Failed to add channel. Try again.")
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        bot.reply_to(message, f"❌ Error adding channel: {str(e)}")

def remove_mandatory_channel_callback(call):
    if not mandatory_channels:
        bot.answer_callback_query(call.id, "❌ No mandatory channels.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup()
    for channel_id, channel_info in mandatory_channels.items():
        channel_name = channel_info.get('name', 'Unknown')
        button_text = f"🗑️ {channel_name}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f'remove_channel_{channel_id}'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='manage_mandatory_channels'))
    try:
        bot.edit_message_text("📢 Choose channel to delete:",
                              call.message.chat.id, call.message.message_id, 
                              reply_markup=markup)
    except Exception as e:
        logger.error(f"Error showing remove channel menu: {e}")

def process_remove_channel(call):
    channel_id = call.data.replace('remove_channel_', '')
    if channel_id in mandatory_channels:
        channel_name = mandatory_channels[channel_id].get('name', 'Unknown')
        if remove_mandatory_channel_db(channel_id):
            bot.answer_callback_query(call.id, f"✅ Channel deleted: {channel_name}")
            try:
                bot.edit_message_text(f"✅ Mandatory channel deleted: **{channel_name}**",
                                      call.message.chat.id, call.message.message_id,
                                      reply_markup=create_mandatory_channels_menu(), parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error updating message after channel removal: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Failed to delete channel.", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Channel not found.", show_alert=True)

def list_mandatory_channels_callback(call):
    bot.answer_callback_query(call.id)
    if not mandatory_channels:
        message_text = "📢 **No mandatory channels currently**"
    else:
        message_text = "📢 **Mandatory Channels:**\n\n"
        for channel_id, channel_info in mandatory_channels.items():
            channel_name = channel_info.get('name', 'Unknown')
            channel_username = channel_info.get('username', 'No username')
            message_text += f"• **{channel_name}**\n  {channel_username or channel_id}\n\n"
    try:
        bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_mandatory_channels_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error listing channels: {e}")

def check_subscription_status_callback(call):
    user_id = call.from_user.id
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if is_subscribed or user_id in admin_ids:
        bot.answer_callback_query(call.id, "✅ You are subscribed to all required channels!", show_alert=True)
        try:
            _logic_send_welcome(call.message)
        except:
            back_to_main_callback(call)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all required channels yet!", show_alert=True)
        subscription_message, markup = create_subscription_check_message(not_joined)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, 
                                  call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error updating subscription message: {e}")

def process_approve_file(call):
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, file_name)
    if not os.path.exists(file_path):
        bot.answer_callback_query(call.id, "❌ File not found.", show_alert=True)
        return
    file_ext = os.path.splitext(file_name)[1].lower()
    try:
        if file_ext in ('.js', '.mjs', '.cjs'):
            handle_js_file(file_path, user_id, user_folder, file_name, call.message)
        elif file_ext == '.php':
            save_user_file(user_id, file_name, 'php')
            threading.Thread(target=run_php_script, args=(file_path, user_id, user_folder, file_name, call.message), daemon=True).start()
        elif file_ext == '.py':
            handle_py_file(file_path, user_id, user_folder, file_name, call.message)
        bot.answer_callback_query(call.id, "✅ File approved!")
        bot.edit_message_text(f"✅ File `{file_name}` approved for user `{user_id}`",
                              call.message.chat.id, call.message.message_id)
        try:
            bot.send_message(user_id, f"✅ Your file `{file_name}` has been approved and started.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error processing approved file: {e}")
        bot.answer_callback_query(call.id, "❌ Error processing file.", show_alert=True)

def process_reject_file(call):
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, file_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Error deleting rejected file: {e}")
    if user_id in pending_files:
        pending_files[user_id] = [f for f in pending_files[user_id] if f[1] != file_name]
        if not pending_files[user_id]:
            del pending_files[user_id]
    bot.answer_callback_query(call.id, "❌ File rejected!")
    bot.edit_message_text(f"❌ File `{file_name}` rejected for user `{user_id}`",
                          call.message.chat.id, call.message.message_id)
    try:
        bot.send_message(user_id, f"❌ Your file `{file_name}` has been rejected.")
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

def process_approve_zip(call):
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    if user_id in pending_zip_files and file_name in pending_zip_files[user_id]:
        file_content = pending_zip_files[user_id][file_name]
        user_folder = get_user_folder(user_id)
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_approve_")
            zip_path = os.path.join(temp_dir, file_name)
            with open(zip_path, 'wb') as f:
                f.write(file_content)
            try:
                user_message = bot.send_message(
                    user_id,
                    f"🔄 Admin approved `{file_name}`. Detecting project structure and starting it...",
                    parse_mode='Markdown'
                )
            except Exception:
                user_message = call.message

            processed = process_zip_file(
                zip_path, user_id, user_folder, file_name, user_message, temp_dir
            )

            if user_id in pending_zip_files and file_name in pending_zip_files[user_id]:
                del pending_zip_files[user_id][file_name]
                if not pending_zip_files[user_id]:
                    del pending_zip_files[user_id]

            if processed:
                bot.answer_callback_query(call.id, "✅ Archive approved and started!")
                bot.edit_message_text(
                    f"✅ Archive `{file_name}` approved and project start initiated for user `{user_id}`.",
                    call.message.chat.id, call.message.message_id
                )
                try:
                    bot.send_message(
                        user_id,
                        f"✅ Your archive `{file_name}` was approved by admin and the project start process has begun."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ Archive approved, but project failed to start.",
                    show_alert=True
                )
                bot.edit_message_text(
                    f"⚠️ Archive `{file_name}` was approved, but project startup failed for user `{user_id}`.",
                    call.message.chat.id, call.message.message_id
                )
        except Exception as e:
            logger.error(f"Error processing approved zip: {e}", exc_info=True)
            bot.answer_callback_query(call.id, "❌ Error processing archive.", show_alert=True)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f"Error cleaning temp dir: {e}")
    else:
        bot.answer_callback_query(call.id, "❌ File content not found. Ask user to re-upload.", show_alert=True)

def process_reject_zip(call):
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    if user_id in pending_zip_files and file_name in pending_zip_files[user_id]:
        del pending_zip_files[user_id][file_name]
        if not pending_zip_files[user_id]:
            del pending_zip_files[user_id]
    bot.answer_callback_query(call.id, "❌ Archive rejected!")
    bot.edit_message_text(
        "❌ SECURITY REVIEW REJECTED\n\n"
        f"📦 Archive: {file_name}\n"
        f"👤 User ID: {user_id}\n\n"
        "📋 REVIEW STATUS\n"
        "└─ ❌ Rejected by Owner/Admin\n\n"
        "⚠️ The archive was not processed or started.",
        call.message.chat.id,
        call.message.message_id
    )
    try:
        bot.send_message(
            user_id,
            "❌ SECURITY REVIEW REJECTED\n\n"
            f"📦 File: {file_name}\n"
            "📋 Status: ❌ Rejected by Owner/Admin\n\n"
            "⚠️ Your archive was not approved and will not be processed."
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

def process_ai_fix_approve(call):
    repair_id = call.data[len('ai_fix_yes_'):]
    item = pending_ai_repairs.get(repair_id)
    if not item:
        bot.answer_callback_query(call.id, '❌ Repair expired.', show_alert=True)
        return
    if int(call.from_user.id) != int(item.get('owner_id')):
        bot.answer_callback_query(call.id, '⚠️ Only the file owner can approve this fix.', show_alert=True)
        return
    ok, result = _apply_ai_repair(repair_id, call.from_user.id)
    if not ok:
        bot.answer_callback_query(call.id, '❌ Fix was not applied.', show_alert=True)
        _send_temp_message(call.from_user.id, f'🛡️ <b>Darkwest AI Fixing</b>\n⚠️ {_html_escape(str(result)[:1000])}', parse_mode='HTML')
        return
    pending_ai_repairs.pop(repair_id, None)
    bot.answer_callback_query(call.id, '✅ Fix approved and applied!')
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    _delete_after_final_action(call.message.chat.id, call.message.message_id)
    _send_temp_message(call.from_user.id, '🛡️ <b>Darkwest AI Fixing</b>\n✅ Fix applied\n🔄 Restarting project...', parse_mode='HTML')
    # Restart only after the owner-approved mutation.
    item_copy = dict(item)
    threading.Thread(target=_start_ai_repair_retry, args=(repair_id, item_copy), daemon=True).start()


def process_ai_fix_reject(call):
    repair_id = call.data[len('ai_fix_no_'):]
    item = pending_ai_repairs.get(repair_id)
    if not item:
        bot.answer_callback_query(call.id, '❌ Repair expired.', show_alert=True)
        return
    if int(call.from_user.id) != int(item.get('owner_id')):
        bot.answer_callback_query(call.id, '⚠️ Only the file owner can reject this fix.', show_alert=True)
        return
    pending_ai_repairs.pop(repair_id, None)
    bot.answer_callback_query(call.id, '❌ AI fix rejected.')
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    _delete_after_final_action(call.message.chat.id, call.message.message_id)
    _send_temp_message(call.from_user.id, '🛡️ <b>Darkwest AI Fixing</b>\n❌ Repair rejected\nNo changes made.', parse_mode='HTML')


# --- Helper functions for file handling (single files) ---
def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Error processing JS file {file_name} for {script_owner_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error processing JS file: {str(e)}")

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Error processing Python file {file_name} for {script_owner_id}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error processing Python file: {str(e)}")

# --- Cleanup and main loop ---
def cleanup():
    logger.warning("Shutdown. Cleaning up processes...")
    script_keys_to_stop = list(bot_scripts.keys()) 
    if not script_keys_to_stop: logger.info("No scripts running. Exiting."); return
    logger.info(f"Stopping {len(script_keys_to_stop)} scripts...")
    for key in script_keys_to_stop:
        if key in bot_scripts: logger.info(f"Stopping: {key}"); kill_process_tree(bot_scripts[key])
        else: logger.info(f"Script {key} already removed.")
    logger.warning("Cleanup finished.")
atexit.register(cleanup)

def ensure_node_installed():
    """Find Node/npm without requiring root. If absent, install a private Node.js runtime."""
    logger.info("Checking Node.js environment...")

    def find_runtime():
        node = shutil.which('node')
        npm = shutil.which('npm')
        if node and npm:
            return node, npm
        common_dirs = [
            "/usr/bin", "/usr/local/bin", "/usr/sbin", "/usr/local/sbin", "/bin", "/sbin",
            os.path.expanduser("~/.nvm/versions/node/*/bin"),
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/.local/share/div-hosting/node/bin"),
            "/opt/nodejs/bin"
        ]
        import glob
        for pattern in common_dirs:
            dirs = glob.glob(pattern) if '*' in pattern else [pattern]
            for d in dirs:
                n = os.path.join(d, 'node')
                m = os.path.join(d, 'npm')
                if os.path.isfile(n) and os.path.isfile(m):
                    os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
                    return n, m
        return None, None

    node_path, npm_path = find_runtime()

    if not node_path or not npm_path:
        logger.warning("Node.js/npm not found. No root/sudo is required; installing a private user-space runtime...")
        try:
            import platform
            import urllib.request
            import tarfile

            arch = platform.machine().lower()
            arch_map = {
                'x86_64': 'x64', 'amd64': 'x64',
                'aarch64': 'arm64', 'arm64': 'arm64',
                'armv7l': 'armv7l'
            }
            node_arch = arch_map.get(arch)
            if not node_arch:
                raise RuntimeError(f"Unsupported CPU architecture for automatic Node install: {arch}")

            runtime_root = Path(os.path.expanduser('~/.local/share/div-hosting/node'))
            runtime_root.mkdir(parents=True, exist_ok=True)
            marker = runtime_root / '.installed'

            if not marker.exists():
                index_url = 'https://nodejs.org/dist/index.json'
                with urllib.request.urlopen(index_url, timeout=30) as r:
                    releases = json.loads(r.read().decode('utf-8'))
                release = next((x for x in releases if x.get('lts')), None)
                if not release:
                    raise RuntimeError('Could not find a Node.js LTS release.')
                version = release['version']
                archive = f'node-{version}-linux-{node_arch}.tar.xz'
                url = f'https://nodejs.org/dist/{version}/{archive}'
                archive_path = runtime_root / archive
                logger.info(f"Downloading Node.js {version} ({node_arch}) to user directory...")
                urllib.request.urlretrieve(url, archive_path)

                extract_root = runtime_root / 'extract'
                if extract_root.exists():
                    shutil.rmtree(extract_root, ignore_errors=True)
                extract_root.mkdir(parents=True, exist_ok=True)
                with tarfile.open(archive_path, 'r:xz') as tf:
                    tf.extractall(extract_root)

                extracted = extract_root / f'node-{version}-linux-{node_arch}'
                if not (extracted / 'bin' / 'node').exists():
                    raise RuntimeError('Node archive downloaded but node binary was not found.')

                final_root = runtime_root / 'current'
                if final_root.exists():
                    shutil.rmtree(final_root, ignore_errors=True)
                shutil.move(str(extracted), str(final_root))
                shutil.rmtree(extract_root, ignore_errors=True)
                try:
                    archive_path.unlink()
                except Exception:
                    pass
                marker.write_text(version, encoding='utf-8')

            bin_dir = runtime_root / 'current' / 'bin'
            node_path = str(bin_dir / 'node')
            npm_path = str(bin_dir / 'npm')
            if not (os.path.isfile(node_path) and os.path.isfile(npm_path)):
                raise RuntimeError('Private Node.js installation is incomplete.')
            os.environ['PATH'] = str(bin_dir) + os.pathsep + os.environ.get('PATH', '')

        except Exception as e:
            logger.exception(f"User-space Node.js installation failed: {e}")
            node_path, npm_path = find_runtime()

    if node_path and npm_path:
        try:
            node_v = subprocess.run([node_path, '-v'], capture_output=True, text=True, timeout=10).stdout.strip()
            npm_v = subprocess.run([npm_path, '-v'], capture_output=True, text=True, timeout=10).stdout.strip()
            logger.info(f"Node.js ({node_v}) and npm ({npm_v}) ready at {node_path} and {npm_path}")
            return True
        except Exception as e:
            logger.error(f"Node.js/npm verification failed: {e}")
            return False

    logger.error("❌ Node.js/npm unavailable. Python hosting can still run; JS hosting requires a usable Node runtime.")
    return False


# =============================================================================
# FULL AUTO A2Z HOSTING PATCH
# Safe project detection, Node/Python/PHP website startup, Gojo/MD support,
# dynamic npm imports, dependency installation, FFmpeg-aware media projects.
# =============================================================================

NODE_RUNTIME_EXTS = ('.js', '.mjs', '.cjs', '.ts', '.tsx')
UNIVERSAL_SOURCE_EXTS = NODE_RUNTIME_EXTS + ('.py', '.php', '.go', '.rs', '.java', '.rb', '.kt', '.kts', '.swift')
PROJECT_SKIP_DIRS = {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'vendor', '.next', 'dist', 'build'}
GOJO_REQUIRED_DEPS = {
    '@whiskeysockets/baileys', 'pino', 'axios', 'fs-extra', 'jimp',
    'node-fetch', 'node-webpmux', '@ffmpeg-installer/ffmpeg',
    'fluent-ffmpeg', 'browser-id3-writer', 'cheerio', 'firebase', 'qs'
}


_HOSTED_PORT_LOCK = threading.Lock()
_HOSTED_PORT_RESERVATIONS = {}


def hosted_port_for_user(user_id, project_key=None):
    """Return and reserve a free non-privileged port for a hosted project.
    Each project gets its own reservation, so multiple npm/Node projects for
    the same user do not accidentally receive the same port. Busy ports are
    skipped automatically.
    """
    project_key = str(project_key or 'default')
    reservation_key = (int(user_id), project_key)
    with _HOSTED_PORT_LOCK:
        existing = _HOSTED_PORT_RESERVATIONS.get(reservation_key)
        if existing:
            return existing
        base = int(os.getenv('HOST_PORT_BASE', '12000')) + (int(user_id) % 20000)
        max_tries = int(os.getenv('HOST_PORT_SCAN_LIMIT', '200'))
        reserved_ports = set(_HOSTED_PORT_RESERVATIONS.values())
        for offset in range(max_tries):
            port = base + offset
            if port > 65535 or port in reserved_ports:
                continue
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                _HOSTED_PORT_RESERVATIONS[reservation_key] = port
                logger.info('Reserved hosting port %s for user %s project %s', port, user_id, project_key)
                return port
            except OSError:
                continue
            finally:
                sock.close()
    raise RuntimeError(f'No free hosting port found near {base}.')


def _release_hosted_port(user_id, project_key=None):
    reservation_key = (int(user_id), str(project_key or 'default'))
    with _HOSTED_PORT_LOCK:
        port = _HOSTED_PORT_RESERVATIONS.pop(reservation_key, None)
    if port:
        logger.info('Released hosting port %s for user %s project %s', port, user_id, project_key)
    return port


def _release_all_hosted_ports_for_user(user_id):
    uid = int(user_id)
    with _HOSTED_PORT_LOCK:
        keys = [key for key in _HOSTED_PORT_RESERVATIONS if key[0] == uid]
        ports = [_HOSTED_PORT_RESERVATIONS.pop(key) for key in keys]
    for key, port in zip(keys, ports):
        logger.info('Released hosting port %s for user %s project %s', port, uid, key[1])
    return len(ports)


def _project_env(user_id, port=None):
    env = os.environ.copy()
    env.setdefault('NODE_ENV', 'production')
    env.setdefault('PYTHONUNBUFFERED', '1')
    # Never inherit the hosting bot's PORT for a user project.
    env['PORT'] = str(port if port is not None else hosted_port_for_user(user_id))
    return env


def _iter_project_sources(project_dir, suffixes):
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
        for name in files:
            if name.endswith(suffixes):
                yield os.path.join(root, name)


def infer_node_dependencies(project_dir):
    """Detect static import, require and dynamic import('package') calls."""
    builtins = _node_builtin_modules()
    deps = set()
    patterns = (
        re.compile(r"(?:import\s+(?:[^'\";]+?\s+from\s+)?|export\s+[^'\";]+?\s+from\s+)['\"]([^'\"]+)['\"]"),
        re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"),
        re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    )
    for path in _iter_project_sources(project_dir, NODE_RUNTIME_EXTS):
        try:
            data = Path(path).read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for pattern in patterns:
            for match in pattern.finditer(data):
                mod = match.group(1).strip()
                if not mod or mod.startswith(('.', '/', 'node:')):
                    continue
                package = '/'.join(mod.split('/')[:2]) if mod.startswith('@') else mod.split('/')[0]
                if package not in builtins:
                    deps.add(package)
    # Known Gojo/WhatsApp-MD project shape: ensure media and sticker deps too.
    if os.path.isfile(os.path.join(project_dir, 'lib', 'client.js')):
        all_text = ''
        for path in _iter_project_sources(project_dir, NODE_RUNTIME_EXTS):
            try:
                all_text += Path(path).read_text(encoding='utf-8', errors='ignore')[:200000]
            except OSError:
                pass
        signatures = ('@whiskeysockets/baileys', 'makeWASocket', 'node-webpmux', 'fluent-ffmpeg')
        if any(sig in all_text for sig in signatures):
            deps.update(GOJO_REQUIRED_DEPS)
    return sorted(deps)


def infer_python_requirements(project_dir):
    """Conservative import-to-pip inference for common web/media projects."""
    mapping = {
        'flask': 'Flask', 'fastapi': 'fastapi', 'uvicorn': 'uvicorn[standard]',
        'django': 'Django', 'requests': 'requests', 'bs4': 'beautifulsoup4',
        'PIL': 'Pillow', 'cv2': 'opencv-python', 'yt_dlp': 'yt-dlp',
        'dotenv': 'python-dotenv', 'yaml': 'PyYAML', 'pydub': 'pydub',
        'moviepy': 'moviepy', 'aiohttp': 'aiohttp', 'httpx': 'httpx',
        'websockets': 'websockets', 'psutil': 'psutil',
        'googletrans': 'googletrans'
    }
    modules = set()
    import ast
    for path in _iter_project_sources(project_dir, ('.py',)):
        try:
            tree = ast.parse(Path(path).read_text(encoding='utf-8', errors='ignore'), filename=path)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split('.')[0])
    return sorted({mapping[m] for m in modules if m in mapping})


def _run_checked(command, cwd, label, timeout=900):
    # Serialize package/toolchain preparation so concurrent users cannot create
    # a CPU/RAM/disk installation storm.
    with _INSTALL_LOCK:
        logger.info('%s: %s', label, ' '.join(map(str, command)))
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                              encoding='utf-8', errors='ignore', timeout=timeout)


def _sanitize_requirements_file(requirements_path):
    """Remove malformed standalone requirement names before pip install.

    Some exported environments contain entries such as `_manylinux` that are
    not valid PEP 508 package requirements. One malformed line can make pip
    abort before installing valid packages such as googletrans.
    """
    path = Path(requirements_path)
    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except OSError:
        return []

    kept = []
    removed = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            kept.append(raw)
            continue
        # Keep pip options and normal requirement syntax untouched.
        if line.startswith(('-', '--', 'git+', 'http://', 'https://')):
            kept.append(raw)
            continue
        # A bare requirement must start with an ASCII letter or digit.
        # This specifically filters invalid names such as `_manylinux`.
        if not re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]+\])?(?:[<>=!~].*)?(?:\s*;.*)?$', line):
            removed.append(line)
            continue
        kept.append(raw)

    if removed:
        path.write_text('\n'.join(kept) + ('\n' if kept else ''), encoding='utf-8')
        logger.warning('Ignored malformed requirements: %s', removed)
    return removed



def _sanitize_node_manifest(project_dir):
    """Repair common broken Node manifests before npm install.

    Hosting should not die because an uploaded ZIP contains a placeholder/private
    package name that is not published on npm.  Keep a backup and only remove
    dependencies that npm explicitly reports as 404/unpublished.
    """
    package_path = os.path.join(project_dir, 'package.json')
    if not os.path.isfile(package_path):
        return []

    try:
        data = json.loads(Path(package_path).read_text(encoding='utf-8'))
    except Exception:
        return []

    changed = []
    for section in ('dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'):
        values = data.get(section)
        if not isinstance(values, dict):
            continue
        # This is a known non-public placeholder seen in uploaded WhatsApp projects.
        # It cannot be resolved from the public npm registry.
        if '@library/wawebjs' in values:
            values.pop('@library/wawebjs', None)
            changed.append('@library/wawebjs')

    if changed:
        backup = package_path + '.hosting-backup'
        try:
            if not os.path.exists(backup):
                shutil.copy2(package_path, backup)
        except Exception:
            pass
        Path(package_path).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        logger.warning('Removed unavailable npm placeholder package(s): %s', changed)
    return changed


def _try_install_git():
    """Best-effort Git bootstrap on supported Linux hosts; never bypasses permissions."""
    if shutil.which('git'):
        return True, "Git is already available."

    # Package managers supported by common VPS/container images. System package
    # installation requires root; managed hosting without root must use its image
    # configuration or the tarball fallback below.
    managers = [
        ('apt-get', ['update'], ['install', '-y', 'git']),
        ('apk', ['update'], ['add', 'git']),
        ('dnf', [], ['install', '-y', 'git']),
        ('yum', [], ['install', '-y', 'git']),
        ('pacman', ['-Sy', '--noconfirm'], ['-S', '--noconfirm', 'git']),
    ]
    manager = next((item for item in managers if shutil.which(item[0])), None)
    if not manager:
        return False, "Git is missing and no supported OS package manager was found."
    if not hasattr(os, 'geteuid') or os.geteuid() != 0:
        return False, "Git is missing, but this process has no root permission. Configure Git in the hosting image or use a supported source-tarball dependency."

    name, update_args, install_args = manager
    try:
        if update_args:
            update_cmd = [shutil.which(name)] + update_args
            update = subprocess.run(update_cmd, capture_output=True, text=True,
                                    timeout=180, check=False)
            if update.returncode != 0:
                return False, "Package index update failed: " + (update.stderr or update.stdout)[-700:]
        install = subprocess.run([shutil.which(name)] + install_args,
                                 capture_output=True, text=True, timeout=240, check=False)
        if install.returncode == 0 and shutil.which('git'):
            return True, "Git installed successfully using " + name + "."
        return False, "Automatic Git installation failed: " + (install.stderr or install.stdout)[-700:]
    except Exception as exc:
        return False, f"Automatic Git installation failed: {exc}"


def _rewrite_github_git_dependencies(project_dir):
    """Convert public GitHub git dependencies to codeload tarballs when Git is absent.

    npm invokes the `git` executable for git-based dependencies. On restricted
    hosting containers where Git cannot be installed, public GitHub repositories
    can often be installed as source tarballs instead. Private repos and non-GitHub
    providers are deliberately left unchanged.
    """
    if shutil.which('git'):
        return []
    package_path = Path(project_dir) / 'package.json'
    if not package_path.is_file():
        return []
    try:
        data = json.loads(package_path.read_text(encoding='utf-8'))
    except Exception:
        return []

    changed = []
    sections = ('dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies')
    # Recognize git+https://github.com/owner/repo.git#ref, https://github.com/owner/repo#ref,
    # github:owner/repo#ref, and owner/repo shorthand. Do not rewrite arbitrary URLs.
    pattern = re.compile(
        r'^(?:git\+https://github\.com/|https://github\.com/|github:)?'
        r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:#(.+))?$',
        re.IGNORECASE
    )
    for section in sections:
        values = data.get(section)
        if not isinstance(values, dict):
            continue
        for name, spec in list(values.items()):
            if not isinstance(spec, str):
                continue
            match = pattern.match(spec.strip())
            if not match:
                continue
            owner, repo, ref = match.groups()
            # Avoid converting shorthand that is actually a normal semver-like package spec.
            if '/' not in spec and not spec.startswith(('github:', 'git+https://github.com/', 'https://github.com/')):
                continue
            ref = ref or 'HEAD'
            # URL-encode spaces in branch/tag names without altering slash separators.
            ref = ref.replace(' ', '%20')
            values[name] = f'https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}'
            changed.append(f'{section}.{name}')

    if changed:
        backup = package_path.with_name('package.json.hosting-git-backup')
        try:
            if not backup.exists():
                shutil.copy2(package_path, backup)
        except Exception:
            pass
        package_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

        # A lockfile may preserve the old git+ URL and make npm invoke Git anyway.
        for lock_name in ('package-lock.json', 'npm-shrinkwrap.json'):
            lock_path = Path(project_dir) / lock_name
            if lock_path.is_file():
                try:
                    backup_lock = lock_path.with_name(lock_name + '.hosting-git-backup')
                    if not backup_lock.exists():
                        shutil.copy2(lock_path, backup_lock)
                    lock_path.unlink()
                except Exception as exc:
                    logger.warning('Could not refresh %s after Git URL rewrite: %s', lock_name, exc)
        logger.warning('Rewrote GitHub dependencies to tarballs because Git is unavailable: %s', changed)
    return changed


def _npm_install_resilient(project_dir, label='npm install'):
    """Install Node dependencies with peer-conflict/404 recovery and Git-missing recovery."""
    # If the host has no Git binary, rewrite supported public GitHub dependencies
    # to source tarballs before npm starts. This avoids npm's `spawn git ENOENT`.
    try:
        _rewrite_github_git_dependencies(project_dir)
    except Exception as exc:
        logger.warning('GitHub dependency fallback could not run: %s', exc)
    npm = shutil.which('npm') or 'npm'
    base = [npm, 'install', '--no-audit', '--no-fund']
    attempts = [
        base,
        base + ['--legacy-peer-deps'],
    ]

    last = None
    git_recovery_attempted = False
    for command in attempts:
        result = _run_checked(command, project_dir, label)
        if result.returncode == 0:
            return result

        last = result
        output = (result.stderr or '') + '\n' + (result.stdout or '')
        lower_output = output.lower()

        # npm may fail with ENOENT when a dependency is fetched from a Git URL.
        # Attempt system installation only when this host has apt-get and root access.
        if (
            not git_recovery_attempted
            and ('spawn git enoent' in lower_output or
                 ('enoent' in lower_output and re.search(r'\bgit\b', lower_output)))
        ):
            git_recovery_attempted = True
            installed, detail = _try_install_git()
            if installed:
                retry_command = command
                result = _run_checked(
                    retry_command, project_dir, label + ' after installing Git'
                )
                if result.returncode == 0:
                    return result
                last = result
                output = (result.stderr or '') + '\n' + (result.stdout or '')
                lower_output = output.lower()
            else:
                result.stderr = (result.stderr or '') + (
                    '\\n[hosting auto-repair] ' + detail +
                    ' Install Git in the hosting image/container or remove/replace the Git-based dependency.'
                )
                last = result

        # npm E404: remove only the known placeholder package, never arbitrary dependencies.
        if 'E404' in output and '@library/wawebjs' in output:
            removed = _sanitize_node_manifest(project_dir)
            if removed:
                result = _run_checked(
                    base + ['--legacy-peer-deps'],
                    project_dir,
                    label + ' after unavailable-package repair'
                )
                if result.returncode == 0:
                    return result
                last = result

    return last


def _install_project_dependencies(project_dir, message):
    """Detect and install declared dependencies for common project ecosystems.

    Installs project dependencies, not arbitrary OS packages. System toolchains
    (Node/npm, PHP/Composer, Java/Maven/Gradle, Go, Rust, Ruby/Bundler) must be
    present in the hosting image or be supplied by the hosting provider.
    """
    def notify(text):
        try:
            bot.reply_to(message, text)
        except Exception:
            logger.debug("Could not send dependency status message", exc_info=True)

    # Python: prefer an explicit lock/requirements manifest, then project metadata,
    # then conservative import inference.
    req = os.path.join(project_dir, 'requirements.txt')
    pyproject = os.path.join(project_dir, 'pyproject.toml')
    pipfile = os.path.join(project_dir, 'Pipfile')
    setup_py = os.path.join(project_dir, 'setup.py')

    if os.path.isfile(req):
        removed = _sanitize_requirements_file(req)
        if removed:
            notify('⚠️ Ignored malformed requirements: ' + ', '.join(removed[:10]))
        notify('🔄 Installing Python dependencies from requirements.txt...')
        result = _pip_install_isolated(['-r', req], project_dir, project_dir, 'pip requirements')
        if result.returncode != 0:
            raise RuntimeError('Python dependency install failed: ' + (result.stderr or result.stdout)[-1800:])
        notify('✅ Python dependencies installed.')
    elif os.path.isfile(pyproject) or os.path.isfile(setup_py):
        # Read PEP 621 dependencies from pyproject.toml and install them into the
        # same isolated target directory used by hosted Python processes. Avoid
        # `pip install -e . --target ...`, which pip does not support reliably.
        py_deps = []
        if os.path.isfile(pyproject):
            try:
                import tomllib
                project_meta = tomllib.loads(Path(pyproject).read_text(encoding='utf-8', errors='ignore'))
                declared = project_meta.get('project', {}).get('dependencies', [])
                if isinstance(declared, list):
                    py_deps.extend(x for x in declared if isinstance(x, str) and x.strip())
                optional = project_meta.get('project', {}).get('optional-dependencies', {})
                if isinstance(optional, dict):
                    for values in optional.values():
                        if isinstance(values, list):
                            py_deps.extend(x for x in values if isinstance(x, str) and x.strip())
            except Exception as exc:
                logger.warning('Could not parse Python project metadata: %s', exc)
        if not py_deps:
            py_deps = infer_python_requirements(project_dir)
        if py_deps:
            notify('🔄 Installing detected Python project dependencies...')
            result = _pip_install_isolated(list(dict.fromkeys(py_deps)), project_dir, project_dir, 'pip project metadata')
            if result.returncode != 0:
                raise RuntimeError('Python project dependency install failed: ' +
                                   (result.stderr or result.stdout)[-1800:])
            notify('✅ Python project dependencies installed.')
        else:
            logger.info('Python metadata found, but no external dependencies were declared or inferred.')
    elif os.path.isfile(pipfile):
        pipenv = shutil.which('pipenv')
        if not pipenv:
            notify('⚠️ Pipfile detected, but pipenv is not installed; using Python import detection instead.')
            inferred_py = infer_python_requirements(project_dir)
            if inferred_py:
                result = _pip_install_isolated(list(inferred_py), project_dir, project_dir, 'pip inferred from Pipfile project')
                if result.returncode != 0:
                    raise RuntimeError('Python inferred dependency install failed: ' + (result.stderr or result.stdout)[-1800:])
        else:
            notify('🔄 Installing Python dependencies from Pipfile...')
            result = _run_checked([pipenv, 'install', '--deploy'], project_dir, 'pipenv install')
            if result.returncode != 0:
                raise RuntimeError('Pipenv dependency install failed: ' + (result.stderr or result.stdout)[-1800:])
            notify('✅ Pipfile dependencies installed.')
    else:
        inferred_py = infer_python_requirements(project_dir)
        if inferred_py:
            notify('🔄 Detecting/installing Python runtime dependencies...')
            result = _pip_install_isolated(list(inferred_py), project_dir, project_dir, 'pip inferred')
            if result.returncode != 0:
                raise RuntimeError('Python inferred dependency install failed: ' + (result.stderr or result.stdout)[-1800:])
            notify('✅ Python runtime dependencies installed.')

    # Node.js / JavaScript / TypeScript: package.json covers JS, TS, and many web apps.
    package_path = os.path.join(project_dir, 'package.json')
    if os.path.isfile(package_path):
        notify('🔄 Installing Node.js/JavaScript dependencies from package.json...')
        result = _npm_install_resilient(project_dir, 'npm install')
        if result.returncode != 0:
            raise RuntimeError('npm install failed after automatic repair: ' + (result.stderr or result.stdout)[-2200:])
        notify('✅ Node.js dependencies installed.')

    # PHP / Composer.
    composer_path = os.path.join(project_dir, 'composer.json')
    if os.path.isfile(composer_path):
        composer = shutil.which('composer')
        if not composer:
            raise RuntimeError('composer.json detected, but Composer is unavailable. The hosting image must provide PHP + Composer.')
        notify('🔄 Installing PHP dependencies from composer.json...')
        result = _run_checked(
            [composer, 'install', '--no-dev', '--prefer-dist', '--no-interaction'],
            project_dir, 'composer install'
        )
        if result.returncode != 0:
            raise RuntimeError('Composer dependency install failed: ' + (result.stderr or result.stdout)[-2200:])
        notify('✅ PHP dependencies installed.')

    # Java: resolve Maven/Gradle dependencies if a manifest exists.
    pom = os.path.join(project_dir, 'pom.xml')
    gradle_files = [os.path.join(project_dir, n) for n in ('build.gradle', 'build.gradle.kts')]
    mvnw = os.path.join(project_dir, 'mvnw')
    gradlew = os.path.join(project_dir, 'gradlew')
    if os.path.isfile(pom):
        mvn = shutil.which('mvn')
        if mvn:
            notify('🔄 Resolving Java/Maven dependencies...')
            result = _run_checked([mvn, '-B', '-DskipTests', 'dependency:resolve'], project_dir, 'maven dependency resolve')
            if result.returncode != 0:
                raise RuntimeError('Maven dependency resolution failed: ' + (result.stderr or result.stdout)[-2000:])
            notify('✅ Maven dependencies resolved.')
        elif os.path.isfile(mvnw):
            notify('🔄 Resolving Java dependencies using Maven Wrapper...')
            result = _run_checked(['sh', './mvnw', '-B', '-DskipTests', 'dependency:resolve'], project_dir, 'maven wrapper dependency resolve')
            if result.returncode != 0:
                raise RuntimeError('Maven Wrapper dependency resolution failed: ' + (result.stderr or result.stdout)[-2000:])
        else:
            raise RuntimeError('pom.xml detected, but Maven/Maven Wrapper is unavailable on this host.')
    elif any(os.path.isfile(p) for p in gradle_files):
        gradle = shutil.which('gradle')
        if os.path.isfile(gradlew):
            command = ['sh', './gradlew', '--no-daemon', 'dependencies']
        elif gradle:
            command = [gradle, '--no-daemon', 'dependencies']
        else:
            raise RuntimeError('Gradle project detected, but Gradle/Gradle Wrapper is unavailable on this host.')
        notify('🔄 Resolving Java/Kotlin Gradle dependencies...')
        result = _run_checked(command, project_dir, 'gradle dependency resolution')
        if result.returncode != 0:
            raise RuntimeError('Gradle dependency resolution failed: ' + (result.stderr or result.stdout)[-2000:])
        notify('✅ Gradle dependencies resolved.')

    # Go, Rust and Ruby manifests can be present alongside another source file.
    go_mod = os.path.join(project_dir, 'go.mod')
    if os.path.isfile(go_mod):
        go = shutil.which('go')
        if not go:
            raise RuntimeError('go.mod detected, but Go is not installed on this host.')
        notify('🔄 Downloading Go modules...')
        result = _run_checked([go, 'mod', 'download'], project_dir, 'go mod download')
        if result.returncode != 0:
            raise RuntimeError('Go dependency download failed: ' + (result.stderr or result.stdout)[-1800:])
        notify('✅ Go modules downloaded.')

    cargo_toml = os.path.join(project_dir, 'Cargo.toml')
    if os.path.isfile(cargo_toml):
        cargo = shutil.which('cargo')
        if not cargo:
            raise RuntimeError('Cargo.toml detected, but Rust/Cargo is not installed on this host.')
        notify('🔄 Downloading Rust crates...')
        result = _run_checked([cargo, 'fetch'], project_dir, 'cargo fetch')
        if result.returncode != 0:
            raise RuntimeError('Rust dependency download failed: ' + (result.stderr or result.stdout)[-1800:])
        notify('✅ Rust crates downloaded.')

    gemfile = os.path.join(project_dir, 'Gemfile')
    if os.path.isfile(gemfile):
        bundle = shutil.which('bundle')
        if not bundle:
            raise RuntimeError('Gemfile detected, but Ruby/Bundler is not installed on this host.')
        notify('🔄 Installing Ruby gems...')
        result = _run_checked([bundle, 'install'], project_dir, 'bundle install')
        if result.returncode != 0:
            raise RuntimeError('Ruby dependency installation failed: ' + (result.stderr or result.stdout)[-1800:])
        notify('✅ Ruby gems installed.')

    # Dart/Flutter manifests are detected even when the host lacks their SDK;
    # do not attempt to download/install a system SDK from an untrusted ZIP.
    pubspec = os.path.join(project_dir, 'pubspec.yaml')
    if os.path.isfile(pubspec):
        dart = shutil.which('dart')
        flutter = shutil.which('flutter')
        if flutter:
            result = _run_checked([flutter, 'pub', 'get'], project_dir, 'flutter pub get')
        elif dart:
            result = _run_checked([dart, 'pub', 'get'], project_dir, 'dart pub get')
        else:
            raise RuntimeError('pubspec.yaml detected, but Dart/Flutter SDK is unavailable on this host.')
        if result.returncode != 0:
            raise RuntimeError('Dart/Flutter dependency resolution failed: ' + (result.stderr or result.stdout)[-1800:])
        notify('✅ Dart/Flutter dependencies resolved.')


def prepare_node_project_for_hosting(temp_dir):
    """Prepare only actual Node projects; never manufacture package.json for Python/PHP projects."""
    js_files = list(_iter_project_sources(temp_dir, NODE_RUNTIME_EXTS))
    package_path = os.path.join(temp_dir, 'package.json')
    if not js_files and not os.path.isfile(package_path):
        return None

    uses_esm = any(
        re.search(r'(^|\n)\s*(import\s|export\s)', Path(path).read_text(encoding='utf-8', errors='ignore'))
        for path in js_files[:500]
    )
    client_path = os.path.join(temp_dir, 'lib', 'client.js')
    config_path = os.path.join(temp_dir, 'config.js')
    entry_override = None
    if os.path.isfile(client_path):
        client_text = Path(client_path).read_text(encoding='utf-8', errors='ignore')
        if ('from "../config.js"' in client_text or "from '../config.js'" in client_text) and not os.path.exists(config_path):
            Path(config_path).write_text(
                "// Auto-created by hosting wrapper.\n"
                "export default {\n"
                '  prefix: process.env.BOT_PREFIX || ".",\n'
                '  SESSION_DIR: process.env.SESSION_DIR || "./sessions",\n'
                '  META_FILE: process.env.META_FILE || "./data/sessions.json",\n'
                "  CONCURRENCY: Number(process.env.CONCURRENCY) || 5,\n"
                "  START_DELAY_MS: Number(process.env.START_DELAY_MS) || 500,\n"
                "  RECONNECT_LIMIT: Number(process.env.RECONNECT_LIMIT) || 10\n"
                "};\n", encoding='utf-8')
        if re.search(r'export\s+(?:async\s+)?function\s+main\s*\(', client_text):
            bootstrap = os.path.join(temp_dir, '__hosting_entry.mjs')
            if not os.path.exists(bootstrap):
                Path(bootstrap).write_text(
                    "import { main } from './lib/client.js';\n"
                    "async function start() {\n"
                    "  try {\n"
                    "    await main();\n"
                    "    console.log('[hosting] Gojo/MD project initialized. Keeping Node process alive for sessions/reconnects.');\n"
                    "    setInterval(() => {}, 60_000);\n"
                    "  } catch (error) {\n"
                    "    console.error('[hosting] Startup failed:', error);\n"
                    "    process.exit(1);\n"
                    "  }\n"
                    "}\n"
                    "start();\n",
                    encoding='utf-8')
            entry_override = '__hosting_entry.mjs'

    if os.path.isfile(package_path):
        try:
            package_data = json.loads(Path(package_path).read_text(encoding='utf-8'))
        except Exception as e:
            raise RuntimeError(f'Invalid root package.json: {e}')
    else:
        package_data = {'name': 'hosted-project', 'version': '1.0.0', 'private': True}
    changed = not os.path.isfile(package_path)
    if uses_esm and package_data.get('type') != 'module':
        package_data['type'] = 'module'; changed = True
    deps = package_data.setdefault('dependencies', {})
    if not isinstance(deps, dict):
        deps = {}; package_data['dependencies'] = deps; changed = True
    for dep in infer_node_dependencies(temp_dir):
        if dep not in deps:
            deps[dep] = '*'; changed = True
    if entry_override:
        package_data['main'] = entry_override
        scripts = package_data.setdefault('scripts', {})
        if not isinstance(scripts, dict):
            scripts = {}; package_data['scripts'] = scripts
        scripts.setdefault('start', 'node __hosting_entry.mjs')
        changed = True
    if changed:
        Path(package_path).write_text(json.dumps(package_data, indent=2) + '\n', encoding='utf-8')
    return entry_override


def _python_web_wrapper(project_dir, entry):
    entry_path = os.path.join(project_dir, entry)
    try:
        code = Path(entry_path).read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return None
    module = os.path.splitext(entry.replace('\\', '/'))[0].replace('/', '.')
    if 'FastAPI(' in code or 'fastapi import' in code.lower():
        wrapper = '__hosting_fastapi.py'
        Path(os.path.join(project_dir, wrapper)).write_text(
            "import os, uvicorn\n"
            f"uvicorn.run('{module}:app', host='0.0.0.0', port=int(os.getenv('PORT','8000')))\n",
            encoding='utf-8')
        return wrapper
    if 'Flask(' in code and 'app.run(' not in code:
        wrapper = '__hosting_flask.py'
        Path(os.path.join(project_dir, wrapper)).write_text(
            "import os, importlib\n"
            f"app = importlib.import_module('{module}').app\n"
            "app.run(host='0.0.0.0', port=int(os.getenv('PORT','8000')))\n",
            encoding='utf-8')
        return wrapper
    return None


def _php_is_web_project(project_dir, entry):
    return os.path.basename(entry).lower() == 'index.php' or os.path.isdir(os.path.join(project_dir, 'public'))


def run_static_site(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, auto_repair_retry=0):
    """Serve a static HTML/CSS/JS website with Python's built-in HTTP server."""
    if not _guard_duplicate_start(script_owner_id, file_name, message_obj_for_reply):
        return
    token_check = _check_token_collision_before_start(user_folder, script_owner_id, None, message_obj_for_reply)
    if not token_check.get('ok', True):
        return
    script_key = f'{script_owner_id}_{file_name}'
    try:
        if not os.path.isfile(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Website entry `{file_name}` not found.")
            return
        port = hosted_port_for_user(script_owner_id, file_name)
        env = _project_env(script_owner_id, port)
        log_file_path = os.path.join(user_folder, 'static_site.log')
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        process = subprocess.Popen(
            [sys.executable, '-m', 'http.server', str(port), '--bind', '0.0.0.0'],
            cwd=user_folder, env=env, stdout=log_file, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=(os.name != 'nt'),
            preexec_fn=_child_preexec_memory_limit()
        )
        bot_scripts[script_key] = {
            'process': process, 'log_file': log_file, 'file_name': file_name,
            'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
            'start_time': datetime.now(), 'user_folder': user_folder,
            'type': 'static', 'script_key': script_key, 'log_file_path': log_file_path, 'auto_repair_retry': auto_repair_retry
        }
        public_base = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
        if public_base:
            bot.reply_to(message_obj_for_reply, f"✅ Website started!\n🌐 URL: {public_base}/\n🔌 Port: {port} (PID: {process.pid})")
        else:
            bot.reply_to(message_obj_for_reply,
                         f"✅ Website started! (PID: {process.pid})\n"
                         f"🔌 Port: {port}\n"
                         f"ℹ️ Set PUBLIC_BASE_URL to expose the public URL.")
        threading.Thread(target=_watch_started_process,
                         args=(script_key, process, user_folder, log_file_path,
                               message_obj_for_reply, file_name, 'static', auto_repair_retry), daemon=True).start()
    except Exception as e:
        logger.exception('Static website runner error')
        bot.reply_to(message_obj_for_reply, f'❌ Error starting website: {e}')


def run_php_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, auto_repair_retry=0):
    if not _guard_duplicate_start(script_owner_id, file_name, message_obj_for_reply):
        return
    token_check = _check_token_collision_before_start(user_folder, script_owner_id, script_path, message_obj_for_reply)
    if not token_check.get('ok', True):
        return
    script_key = f'{script_owner_id}_{file_name}'
    try:
        check = subprocess.run(['php', '-l', script_path], cwd=user_folder, capture_output=True, text=True,
                               encoding='utf-8', errors='ignore')
        if check.returncode != 0:
            err = (check.stderr or check.stdout or '')[-AUTO_REPAIR_LOG_CHARS:]
            if not _ai_handle_direct_error(script_owner_id, message_obj_for_reply, 'php', user_folder, file_name, err, auto_repair_retry):
                bot.reply_to(message_obj_for_reply, f"❌ PHP syntax error:\n```\n{err[-1800:]}\n```", parse_mode='Markdown')
            return
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(os.path.basename(file_name))[0]}.log")
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        port = hosted_port_for_user(script_owner_id, file_name)
        env = _project_env(script_owner_id, port)
        logger.info('Selected hosting port %s for PHP project %s', port, file_name)
        if _php_is_web_project(user_folder, file_name):
            docroot = os.path.join(user_folder, 'public') if os.path.isdir(os.path.join(user_folder, 'public')) else user_folder
            command = ['php', '-S', f"0.0.0.0:{env['PORT']}", '-t', docroot]
            label = f"PHP website on port {env['PORT']}"
        else:
            command = ['php', script_path]; label = 'PHP script'
        process = subprocess.Popen(command, cwd=user_folder, env=env, stdout=log_file, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=(os.name != 'nt'), preexec_fn=_child_preexec_memory_limit())
        bot_scripts[script_key] = {'process':process,'log_file':log_file,'file_name':file_name,
            'chat_id':message_obj_for_reply.chat.id,'script_owner_id':script_owner_id,
            'start_time':datetime.now(),'user_folder':user_folder,'type':'php','script_key':script_key,
            'log_file_path':log_file_path, 'auto_repair_retry': auto_repair_retry}
        bot.reply_to(message_obj_for_reply, f"✅ {label} started! (PID: {process.pid})")
        threading.Thread(target=_watch_started_process,
                         args=(script_key, process, user_folder, log_file_path, message_obj_for_reply, file_name, 'php', auto_repair_retry), daemon=True).start()
    except FileNotFoundError:
        bot.reply_to(message_obj_for_reply, '❌ PHP runtime is not installed on this hosting server.')
    except Exception as e:
        logger.exception('PHP runner error')
        bot.reply_to(message_obj_for_reply, f'❌ Error starting PHP project: {e}')


_DUPLICATE_START_LOCK = threading.Lock()


def _guard_duplicate_start(script_owner_id, file_name, message_obj_for_reply=None):
    """Prevent a second live process for the same user/project from starting."""
    script_key = f'{script_owner_id}_{file_name}'
    with _DUPLICATE_START_LOCK:
        info = bot_scripts.get(script_key)
        if not info:
            return True
        process = info.get('process')
        if process is not None:
            try:
                alive = process.poll() is None
            except Exception:
                alive = False
            if alive:
                logger.warning('Duplicate start blocked for %s', script_key)
                if message_obj_for_reply is not None:
                    try:
                        bot.reply_to(message_obj_for_reply, f'⚠️ `{file_name}` is already running. Duplicate start blocked.', parse_mode='Markdown')
                    except Exception:
                        logger.debug('Could not send duplicate-start notice for %s', script_key, exc_info=True)
                return False
        # Remove stale bookkeeping left by a process that already exited.
        bot_scripts.pop(script_key, None)
        try:
            _release_hosted_port(script_owner_id, file_name)
        except Exception:
            logger.debug('Could not release stale port for %s', script_key, exc_info=True)
        return True


def _auto_install_missing_python_module(module_name, script_path, script_owner_id, user_folder):
    """Install one validated missing import into the project's isolated package folder."""
    if not isinstance(module_name, str):
        return False
    module_name = module_name.strip().split('.')[0]
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', module_name):
        return False
    stdlib = set(getattr(sys, 'stdlib_module_names', set()))
    if module_name in stdlib or module_name in {'__future__', 'builtins'}:
        return False

    package_map = {
        'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
        'bs4': 'beautifulsoup4', 'PIL': 'Pillow', 'cv2': 'opencv-python',
        'dotenv': 'python-dotenv', 'yaml': 'PyYAML', 'dateutil': 'python-dateutil',
        'yt_dlp': 'yt-dlp', 'Crypto': 'pycryptodome', 'Cryptodome': 'pycryptodomex',
        'googleapiclient': 'google-api-python-client', 'discord': 'discord.py',
        'telegramify_markdown': 'telegramify-markdown', 'magic': 'python-magic',
        'docx': 'python-docx', 'fitz': 'PyMuPDF', 'pymongo': 'pymongo',
        'psycopg2': 'psycopg2-binary', 'apscheduler': 'APScheduler',
        'slack_sdk': 'slack-sdk', 'playwright_stealth': 'playwright-stealth',
        'sqlalchemy': 'SQLAlchemy', 'PIL': 'Pillow', 'Crypto': 'pycryptodome',
    }
    package_name = package_map.get(module_name, module_name.replace('_', '-'))
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?', package_name):
        return False
    dep_dir = _python_dependency_dir(os.path.abspath(user_folder))
    if _module_available_for_project(module_name, dep_dir):
        return True

    logger.info('AUTO-REPAIR: installing missing Python import %s as %s', module_name, package_name)
    try:
        result = _pip_install_isolated(
            [package_name], os.path.abspath(user_folder), os.path.abspath(user_folder),
            'automatic missing Python import ' + package_name, timeout=600
        )
    except Exception:
        logger.exception('AUTO-REPAIR: package install exception for %s', package_name)
        return False
    if result.returncode != 0:
        logger.error('AUTO-REPAIR: package %s install failed: %s',
                     package_name, (result.stderr or result.stdout)[-1800:])
        return False
    return _module_available_for_project(module_name, dep_dir)


def _python_import_precheck(script_path, script_owner_id, user_folder):
    """Check explicit top-level imports in a child interpreter before hosting.

    The user's script itself is never executed by this check. Each import statement
    is tested in its own short-lived process with the same project dependency path,
    so ImportError (including "cannot import name") reaches the AI repair flow.
    Relative imports are skipped because they require package execution context.
    """
    try:
        source = Path(script_path).read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(source, filename=script_path)
    except Exception as exc:
        return f"Import pre-check could not parse source: {exc}"

    # Normalize the source path first; callers may pass a relative or stale path.
    script_path = os.path.abspath(script_path)
    actual_folder = os.path.dirname(script_path)

    # FIX 1: Derive the owner ID from the upload path when available, rather
    # than trusting a potentially stale caller argument. Keep the argument as
    # fallback for paths that do not use the upload_bots/<owner_id> layout.
    try:
        parts = Path(script_path).parts
        if 'upload_bots' in parts:
            idx = parts.index('upload_bots')
            if idx + 1 < len(parts):
                try:
                    derived = int(parts[idx + 1])
                    if derived != script_owner_id:
                        logger.warning(
                            "Owner mismatch: arg=%s path=%s",
                            script_owner_id, derived
                        )
                        script_owner_id = derived
                except (TypeError, ValueError):
                    pass
    except Exception:
        logger.debug("Could not derive owner ID from script path %s", script_path, exc_info=True)

    env = _python_project_env(script_owner_id, actual_folder, None)
    statements = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            statements.append(ast.get_source_segment(source, node) or ast.unparse(node))
        elif isinstance(node, ast.ImportFrom) and not node.level:
            statements.append(ast.get_source_segment(source, node) or ast.unparse(node))

    for statement in statements:
        # Import statements only; never execute the uploaded script body here.
        # Python -c accepts a direct import statement; this executes only the
        # extracted import, never the uploaded script body.
        check_code = statement
        try:
            result = subprocess.run(
                [sys.executable, '-c', check_code], cwd=actual_folder, env=env,
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=25
            )
        except subprocess.TimeoutExpired:
            continue
        except Exception as exc:
            return f"Import pre-check failed to run: {exc}"
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or 'Import statement failed').strip()
            # Only auto-install for an explicit "No module named X" error. API/symbol
            # mismatches such as ImportError: cannot import name ... are code/version
            # issues and must not trigger guessing random package names.
            missing = re.search(r"No module named ['\\\"]([^'\\\"]+)['\\\"]", detail)
            if missing:
                missing_module = missing.group(1).split('.')[0]
                if _auto_install_missing_python_module(
                    missing_module, script_path, script_owner_id, actual_folder
                ):
                    try:
                        retry = subprocess.run(
                            [sys.executable, '-c', check_code], cwd=actual_folder, env=env,
                            capture_output=True, text=True, encoding='utf-8',
                            errors='ignore', timeout=25
                        )
                        if retry.returncode == 0:
                            logger.info('AUTO-REPAIR: missing import %s fixed; import check passed.',
                                        missing_module)
                            continue
                        detail = (retry.stderr or retry.stdout or detail).strip()
                    except Exception as exc:
                        detail = f'{detail}\nRetry after install failed: {exc}'
            return f"Import pre-check failed for `{statement}`\n{detail}"[-AUTO_REPAIR_LOG_CHARS:]
    return None


def _find_config_admin_placeholder(user_folder):
    """Find a project CONFIG/config.py containing the common ADMIN_ID placeholder."""
    root = os.path.abspath(user_folder)
    for walk_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
        if 'config.py' in files and os.path.basename(walk_root).lower() == 'config':
            candidate = os.path.join(walk_root, 'config.py')
            try:
                content = Path(candidate).read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            if re.search(r'^\s*ADMIN_ID\s*=\s*#\s*(?:YOU\s*ID\s*HERE)?', content, re.I | re.M):
                return candidate
    return None


# Pending setup context is keyed by the project owner's Telegram ID.
_PENDING_PROJECT_ADMIN_CONFIGS = {}
_PENDING_PROJECT_ADMIN_LOCK = threading.Lock()


def _ask_for_project_admin_id(message_obj, script_path, script_owner_id, user_folder,
                              file_name, attempt, auto_repair_retry, config_path):
    """Offer clickable automatic setup and manual-editor options."""
    try:
        owner_id = int(script_owner_id)
        with _PENDING_PROJECT_ADMIN_LOCK:
            _PENDING_PROJECT_ADMIN_CONFIGS[owner_id] = {
                'script_path': script_path, 'user_folder': user_folder,
                'file_name': file_name, 'message_obj': message_obj,
                'attempt': attempt, 'auto_repair_retry': auto_repair_retry,
                'config_path': config_path,
            }
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('🆔 Set Admin ID automatically', callback_data='project_admin_set'))
        markup.add(types.InlineKeyboardButton('📝 Manual Edit / Show path', callback_data='project_admin_edit'))
        msg = bot.send_message(
            message_obj.chat.id,
            "⚙️ Project config mein invalid `ADMIN_ID` placeholder mila.\n\n"
            "Button choose karein: Admin ID bot se set karwaein, ya file khud edit karein.\n"
            "Manual edit ke baad `I edited, restart` button dabayein.",
            parse_mode='Markdown', reply_markup=markup
        )
        return True
    except Exception:
        logger.exception('Could not request project ADMIN_ID')
        return False


def _handle_project_admin_config_callback(call, action):
    """Owner-only inline menu for automatic or manual ADMIN_ID setup."""
    owner_id = call.from_user.id
    with _PENDING_PROJECT_ADMIN_LOCK:
        ctx = _PENDING_PROJECT_ADMIN_CONFIGS.get(owner_id)
    if not ctx:
        bot.answer_callback_query(call.id, 'Setup expired. Start the project again.', show_alert=True)
        return
    bot.answer_callback_query(call.id)
    if action == 'set':
        msg = bot.send_message(call.message.chat.id, 'Numeric Telegram Admin ID bhejein. Cancel ke liye /cancel.')
        bot.register_next_step_handler(
            msg, _receive_project_admin_id, ctx['script_path'], owner_id,
            ctx['user_folder'], ctx['file_name'], ctx['message_obj'],
            ctx['attempt'], ctx['auto_repair_retry'], ctx['config_path']
        )
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('✅ I edited, restart', callback_data='project_admin_restart'))
    bot.send_message(
        call.message.chat.id,
        f"📝 Manual edit path:\n`{ctx['config_path']}`\n\n"
        "Is file mein `ADMIN_ID = #YOU ID HERE` ko apni numeric ID se replace karein, misal: `ADMIN_ID = 123456789`.\n"
        "Save karne ke baad neeche button dabayein.",
        parse_mode='Markdown', reply_markup=markup
    )


def _restart_after_manual_project_admin_edit(call):
    owner_id = call.from_user.id
    with _PENDING_PROJECT_ADMIN_LOCK:
        ctx = _PENDING_PROJECT_ADMIN_CONFIGS.get(owner_id)
    if not ctx:
        bot.answer_callback_query(call.id, 'Setup expired. Start the project again.', show_alert=True)
        return
    try:
        config_path = ctx['config_path']
        raw = Path(config_path).read_text(encoding='utf-8', errors='ignore')
        compile(raw, config_path, 'exec')
        if re.search(r'^\s*ADMIN_ID\s*=\s*#', raw, re.I | re.M):
            bot.answer_callback_query(call.id, 'ADMIN_ID abhi bhi invalid hai.', show_alert=True)
            return
        bot.answer_callback_query(call.id, 'Config syntax OK; restarting…')
        bot.send_message(call.message.chat.id, '✅ Config syntax valid. Project restart kar raha hoon…')
        run_script(ctx['script_path'], owner_id, ctx['user_folder'], ctx['file_name'],
                   ctx['message_obj'], attempt=ctx['attempt'], auto_repair_retry=ctx['auto_repair_retry'])
    except Exception as exc:
        logger.exception('Manual project config validation/restart failed')
        bot.send_message(call.message.chat.id, '❌ Config check failed: ' + str(exc).replace('`', '').replace('*', '').replace('_', ''), parse_mode=None)


def _receive_project_admin_id(message, script_path, script_owner_id, user_folder,
                              file_name, original_message, attempt, auto_repair_retry, config_path):
    """Receive an ADMIN_ID or provide manual edit instructions; owner only."""
    try:
        if getattr(message.from_user, 'id', None) != int(script_owner_id):
            bot.reply_to(message, '❌ Sirf project owner is config ko update kar sakta hai.')
            return
        value = (message.text or '').strip()
        if value.lower() == '/cancel':
            bot.reply_to(message, 'Setup cancelled. Project config unchanged.')
            return
        if value.upper() == 'EDIT':
            bot.reply_to(
                message,
                f"📝 Manual edit path:\n`{config_path}`\n\n"
                "Is file mein `ADMIN_ID = #YOU ID HERE` ko replace karein, misal ke taur par:\n"
                "`ADMIN_ID = 123456789`\n\nSave karke phir project start karein.",
                parse_mode='Markdown'
            )
            return
        if not value.isdigit() or int(value) <= 0:
            msg = bot.reply_to(message, '❌ Valid numeric Telegram ID bhejein, ya `EDIT` likhein.', parse_mode='Markdown')
            bot.register_next_step_handler(
                msg, _receive_project_admin_id, script_path, script_owner_id,
                user_folder, file_name, original_message, attempt, auto_repair_retry, config_path
            )
            return
        admin_id = int(value)
        raw = Path(config_path).read_text(encoding='utf-8', errors='ignore')
        updated, count = re.subn(
            r'^([ \t]*ADMIN_ID[ \t]*=[ \t]*)#[ \t]*(?:YOU[ \t]*ID[ \t]*HERE)?[ \t]*$',
            lambda m: m.group(1) + str(admin_id), raw, count=1, flags=re.I | re.M
        )
        if count != 1:
            bot.reply_to(message, '❌ Placeholder line change ho chuki hai. File ko manually edit karein: ' + config_path)
            return
        compile(updated, config_path, 'exec')
        temp_path = config_path + '.tmp'
        Path(temp_path).write_text(updated, encoding='utf-8')
        os.replace(temp_path, config_path)
        saved = Path(config_path).read_text(encoding='utf-8', errors='ignore')
        compile(saved, config_path, 'exec')
        if not re.search(r'^\s*ADMIN_ID\s*=\s*' + re.escape(str(admin_id)) + r'\s*$', saved, re.M):
            raise RuntimeError('ADMIN_ID write verification failed; project was not restarted')
        bot.reply_to(message, f'ADMIN_ID set ho gaya: {admin_id}. Config verify ho gayi; project restart kar raha hoon.', parse_mode=None)
        run_script(script_path, script_owner_id, user_folder, file_name, original_message,
                   attempt=attempt, auto_repair_retry=auto_repair_retry)
    except Exception as exc:
        logger.exception('Failed to update project ADMIN_ID')
        try:
            bot.reply_to(message, '❌ Config update fail hui: ' + str(exc).replace('`', '').replace('*', '').replace('_', ''))
        except Exception:
            pass


# Project BOT_TOKEN setup flow (owner-approved; token values are never logged).
_PENDING_PROJECT_TOKEN_CONFIGS = {}
_PENDING_PROJECT_TOKEN_LOCK = threading.Lock()


def _find_project_token_config(user_folder, file_name=None):
    """Find a Python config file with a BOT_TOKEN assignment in this project."""
    root = os.path.abspath(user_folder)
    candidates = []
    for walk_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
        for name in files:
            if not name.endswith('.py') or name.startswith('.'): continue
            path = os.path.join(walk_root, name)
            try:
                raw = Path(path).read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            if re.search(r'^\s*BOT_TOKEN\s*=', raw, re.M):
                score = (0 if os.path.basename(path).lower() == 'config.py' else 1,
                         0 if os.path.basename(walk_root).lower() == 'config' else 1,
                         len(path))
                candidates.append((score, path))
    return min(candidates)[1] if candidates else None


def _ask_for_project_bot_token(message_obj, script_path, script_owner_id, user_folder,
                               file_name, attempt, auto_repair_retry, config_path):
    try:
        owner_id = int(script_owner_id)
        with _PENDING_PROJECT_TOKEN_LOCK:
            _PENDING_PROJECT_TOKEN_CONFIGS[owner_id] = {
                'script_path': script_path, 'user_folder': user_folder,
                'file_name': file_name, 'message_obj': message_obj,
                'attempt': attempt, 'auto_repair_retry': auto_repair_retry,
                'config_path': config_path,
            }
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('🔑 Set Token Automatically', callback_data='project_token_set'))
        markup.add(types.InlineKeyboardButton('📝 Manual Edit / Show path', callback_data='project_token_edit'))
        bot.send_message(message_obj.chat.id,
            '❌ Project BOT_TOKEN missing/invalid hai. Apne BotFather se valid token lein, phir option choose karein. Token chat mein sirf apne hosting bot ko bhejein; kisi aur ko share na karein.',
            reply_markup=markup, parse_mode=None)
        return True
    except Exception:
        logger.exception('Could not request project BOT_TOKEN')
        return False


def _handle_project_token_callback(call, action):
    owner_id = call.from_user.id
    with _PENDING_PROJECT_TOKEN_LOCK:
        ctx = _PENDING_PROJECT_TOKEN_CONFIGS.get(owner_id)
    if not ctx:
        bot.answer_callback_query(call.id, 'Setup expired. Project dobara start karein.', show_alert=True)
        return
    bot.answer_callback_query(call.id)
    if action == 'set':
        msg = bot.send_message(call.message.chat.id,
            'BotFather se mila hua poora bot token bhejein. Token logs mein print nahi hoga. Cancel: /cancel', parse_mode=None)
        bot.register_next_step_handler(msg, _receive_project_bot_token, owner_id)
    else:
        bot.send_message(call.message.chat.id,
            'Manual edit path:\n' + ctx['config_path'] + '\n\nBOT_TOKEN assignment ko valid token se update karein, save karein, phir project dobara start karein.',
            parse_mode=None)


def _receive_project_bot_token(message, owner_id):
    with _PENDING_PROJECT_TOKEN_LOCK:
        ctx = _PENDING_PROJECT_TOKEN_CONFIGS.get(int(owner_id))
    if not ctx: return
    if getattr(message.from_user, 'id', None) != int(owner_id):
        bot.reply_to(message, 'Sirf project owner token update kar sakta hai.', parse_mode=None); return
    token = (message.text or '').strip()
    if token.lower() == '/cancel':
        bot.reply_to(message, 'Token setup cancelled; config unchanged.', parse_mode=None); return
    # Telegram bot token shape check only; never echo it back.
    if not re.fullmatch(r'\d{8,12}:[A-Za-z0-9_-]{25,}', token):
        msg = bot.reply_to(message, 'Token format valid nahi lagta. BotFather se poora token bhejein, ya /cancel.', parse_mode=None)
        bot.register_next_step_handler(msg, _receive_project_bot_token, owner_id); return
    path = ctx['config_path']
    try:
        raw = Path(path).read_text(encoding='utf-8', errors='ignore')
        pattern = r'^([ \t]*BOT_TOKEN[ \t]*=[ \t]*)(?:[\'\"].*?[\'\"]|[^\n#]*)([ \t]*(?:#.*)?)$'
        updated, count = re.subn(pattern, lambda m: m.group(1) + repr(token) + m.group(2), raw, count=1, flags=re.M)
        if count != 1: raise RuntimeError('BOT_TOKEN assignment locate nahi hui; manual edit use karein.')
        compile(updated, path, 'exec')
        tmp = path + '.tmp'
        Path(tmp).write_text(updated, encoding='utf-8')
        os.replace(tmp, path)
        saved = Path(path).read_text(encoding='utf-8', errors='ignore')
        compile(saved, path, 'exec')
        bot.reply_to(message, 'BOT_TOKEN config mein save aur syntax-verify ho gaya. Project restart kar raha hoon.', parse_mode=None)
        _PENDING_PROJECT_TOKEN_CONFIGS.pop(int(owner_id), None)
        run_script(ctx['script_path'], owner_id, ctx['user_folder'], ctx['file_name'], ctx['message_obj'],
                   attempt=ctx['attempt'], auto_repair_retry=ctx['auto_repair_retry'])
    except Exception as exc:
        logger.exception('Project BOT_TOKEN update failed (token value redacted)')
        bot.reply_to(message, 'Config update fail hui: ' + str(exc).replace('`','').replace('*','').replace('_',''), parse_mode=None)


def _token_error_from_log(log_text):
    low = str(log_text or '').lower()
    return ('token must contain a colon' in low or 'invalid token' in low or
            ('bot_token' in low and ('missing' in low or 'invalid' in low)))


def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1, auto_repair_retry=0):
    """Python runner with compile validation and one AI-assisted dependency retry."""
    script_path = os.path.abspath(os.fspath(script_path))
    given_root = os.path.abspath(os.fspath(user_folder))

    # Defensive recovery: some upload/ZIP paths can accidentally pass the project
    # directory as the Python entry point. Never send a directory to py_compile,
    # open(), or Popen; resolve a sensible Python file first.
    if os.path.isdir(script_path):
        project_root = script_path
        preferred_names = ('bot.py', 'main.py', 'app.py', 'run.py', 'start.py', '__main__.py')
        candidates = []
        for base, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            for name in files:
                if name.lower().endswith('.py'):
                    full = os.path.join(base, name)
                    if os.path.isfile(full):
                        candidates.append(full)
        preferred = [f for wanted in preferred_names for f in candidates
                     if os.path.basename(f).lower() == wanted]
        if preferred:
            script_path = preferred[0]
        elif len(candidates) == 1:
            script_path = candidates[0]
        else:
            bot.reply_to(
                message_obj_for_reply,
                '❌ Python entry file select nahi ho saki. Project folder ke andar bot.py/main.py jaisi entry file rakhein, ya upload ke waqt actual .py file select karein.',
                parse_mode=None
            )
            logger.error('Python runner received directory instead of a file: %s; candidates=%s', project_root, candidates[:30])
            return
        user_folder = project_root
        file_name = os.path.basename(script_path)
        logger.warning('Resolved directory entry point to Python file: %s', script_path)
    elif not os.path.isfile(script_path):
        bot.reply_to(message_obj_for_reply, f'❌ Python file nahi mili: {script_path}', parse_mode=None)
        logger.error('Python runner received a missing/non-file entry point: %s', script_path)
        return
    # Preserve a valid project root (it may contain requirements/config files); only
    # correct it when the script is outside that root due to a stale/nested path.
    if not (script_path == given_root or script_path.startswith(given_root + os.sep)):
        actual_root = os.path.dirname(script_path)
        logger.warning("user_folder mismatch: given=%s actual=%s", given_root, actual_root)
        user_folder = actual_root
    else:
        user_folder = given_root
    if not _guard_duplicate_start(script_owner_id, file_name, message_obj_for_reply):
        return
    token_check = _check_token_collision_before_start(user_folder, script_owner_id, script_path, message_obj_for_reply)
    if not token_check.get('ok', True):
        return
    script_key = f'{script_owner_id}_{file_name}'
    try:
        check = subprocess.run([sys.executable, '-m', 'py_compile', script_path], cwd=user_folder,
                               capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if check.returncode != 0:
            err = (check.stderr or check.stdout or '')[-AUTO_REPAIR_LOG_CHARS:]
            if not _ai_handle_direct_error(script_owner_id, message_obj_for_reply, 'python', user_folder, file_name, err, auto_repair_retry):
                bot.reply_to(message_obj_for_reply, f"❌ Python syntax error:\n```\n{err[-1800:]}\n```", parse_mode='Markdown')
            return

        # FULL AUTO: install every detected third-party Python dependency
        # before launching the hosted script. Each package is isolated so
        # invalid names such as `_manylinux` cannot abort valid installs.
        if auto_repair_retry == 0:
            with _user_start_lock(script_owner_id):
                auto_install_python_dependencies(script_path, message_obj_for_reply)
        else:
            logger.info("Skipping full Python dependency scan on automatic repair retry %s/%s for %s", auto_repair_retry, AUTO_REPAIR_MAX_RETRIES, file_name)

        import_error = _python_import_precheck(script_path, script_owner_id, user_folder)
        if import_error:
            # Handle the common invalid ADMIN_ID placeholder before generic AI repair.
            # This asks the owner for an ID or offers a manual-edit path instead of
            # repeatedly sending an unfixable config SyntaxError to the AI.
            config_path = _find_config_admin_placeholder(user_folder)
            if config_path and 'syntaxerror' in import_error.lower() and 'config.py' in import_error.lower():
                logger.warning('Project ADMIN_ID placeholder detected in %s', config_path)
                if _ask_for_project_admin_id(
                    message_obj_for_reply, script_path, script_owner_id, user_folder,
                    file_name, attempt, auto_repair_retry, config_path
                ):
                    return
            logger.warning("Python import pre-check failed for %s: %s", file_name, import_error[-2000:])
            if not _ai_handle_direct_error(
                script_owner_id, message_obj_for_reply, 'python', user_folder,
                file_name, import_error, auto_repair_retry
            ):
                bot.reply_to(
                    message_obj_for_reply,
                    "❌ Python import pre-check failed:\n```\n" + import_error[-1800:] + "\n```",
                    parse_mode='Markdown'
                )
            return

        log_file_path = os.path.join(user_folder, f"{os.path.splitext(os.path.basename(file_name))[0]}.log")
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        port = hosted_port_for_user(script_owner_id, file_name)
        logger.info('Selected hosting port %s for Python project %s', port, file_name)
        process = subprocess.Popen([sys.executable, script_path], cwd=user_folder, env=_python_project_env(script_owner_id, user_folder, port),
                                   stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   start_new_session=(os.name != 'nt'), preexec_fn=_child_preexec_memory_limit())
        bot_scripts[script_key] = {'process':process,'log_file':log_file,'file_name':file_name,
            'chat_id':message_obj_for_reply.chat.id,'script_owner_id':script_owner_id,
            'start_time':datetime.now(),'user_folder':user_folder,'type':'py','script_key':script_key,
            'log_file_path':log_file_path, 'auto_repair_retry': auto_repair_retry}
        bot.reply_to(message_obj_for_reply, f"✅ Python project `{file_name}` started! (PID: {process.pid})")
        threading.Thread(target=_watch_started_process,
                         args=(script_key, process, user_folder, log_file_path, message_obj_for_reply, file_name, 'py', auto_repair_retry), daemon=True).start()
    except Exception as e:
        logger.exception('Python runner error')
        bot.reply_to(message_obj_for_reply, f'❌ Error starting Python project: {e}')


def _ensure_single_js_dependencies(project_dir, message=None):
    """Install Node dependencies for a standalone JS/Node project.

    For uploads containing only a .js file (and no package.json), infer external
    imports/requires, create a minimal package.json when needed, and install the
    detected packages. Existing package.json dependencies are installed first.
    Built-in Node modules and relative/local imports are excluded by
    infer_node_dependencies().
    """
    npm = shutil.which('npm')
    if not npm:
        raise RuntimeError('npm is not installed or not available in PATH.')

    package_path = os.path.join(project_dir, 'package.json')
    has_package = os.path.isfile(package_path)

    if not has_package:
        deps = infer_node_dependencies(project_dir)
        if not deps:
            logger.info('Standalone JS file has no external Node dependencies: %s', project_dir)
            return []
        result = _run_checked([npm, 'init', '-y'], project_dir, 'npm init for standalone JS')
        if result.returncode != 0:
            raise RuntimeError('npm init failed: ' + (result.stderr or result.stdout)[-1800:])
    else:
        deps = infer_node_dependencies(project_dir)
        # Install declared package.json dependencies first.
        result = _npm_install_resilient(project_dir, 'npm install declared Node dependencies')
        if result.returncode != 0:
            raise RuntimeError('npm install failed after automatic repair: ' + (result.stderr or result.stdout)[-2200:])

    if deps:
        # npm install --save is intentional here: standalone JS uploads need a
        # persistent package.json so the next restart does not lose dependencies.
        result = _run_checked([npm, 'install', '--save', '--no-audit', '--no-fund', *deps],
                              project_dir, 'npm install inferred Node dependencies')
        if result.returncode != 0:
            raise RuntimeError('Inferred Node dependency install failed: ' +
                               (result.stderr or result.stdout)[-2200:])
        logger.info('Installed/inferred Node dependencies for standalone project: %s', deps)
        if message is not None:
            try:
                bot.reply_to(message, '✅ Node dependencies installed: ' + ', '.join(deps[:20]))
            except Exception:
                logger.debug('Could not send Node dependency install notice', exc_info=True)
    return deps


def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1, auto_repair_retry=0):
    """Node runner with syntax validation and up to two AI-assisted dependency retries."""
    if not _guard_duplicate_start(script_owner_id, file_name, message_obj_for_reply):
        return
    token_check = _check_token_collision_before_start(user_folder, script_owner_id, script_path, message_obj_for_reply)
    if not token_check.get('ok', True):
        return
    script_key = f'{script_owner_id}_{file_name}'
    try:
        # Remove harmless encoding artifacts before syntax validation.  Do not
        # rewrite smart quotes because they may be intentional string data.
        try:
            raw = Path(script_path).read_bytes()
            if raw.startswith(b'\xef\xbb\xbf') or b'\xc2\xa0' in raw:
                text = raw.decode('utf-8-sig', errors='strict').replace('\u00a0', ' ')
                Path(script_path).write_text(text, encoding='utf-8', newline='')
        except (UnicodeDecodeError, OSError) as enc_err:
            logger.warning('Could not normalize JS encoding for %s: %s', script_path, enc_err)

        check = subprocess.run(['node', '--check', script_path], cwd=user_folder,
                               capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if check.returncode != 0:
            err = (check.stderr or check.stdout or '')[-AUTO_REPAIR_LOG_CHARS:]
            if not _ai_handle_direct_error(script_owner_id, message_obj_for_reply, 'node', user_folder, file_name, err, auto_repair_retry):
                bot.reply_to(message_obj_for_reply, f"❌ JavaScript syntax error:\n```\n{err[-1800:]}\n```", parse_mode='Markdown')
            return

        # FULL AUTO: standalone .js uploads get the same dependency treatment
        # as Python uploads. Infer external imports/requires, create a minimal
        # package.json when necessary, then install declared/inferred packages.
        if auto_repair_retry == 0:
            try:
                with _user_start_lock(script_owner_id):
                    _ensure_single_js_dependencies(user_folder, message_obj_for_reply)
            except Exception as dep_err:
                logger.exception('Node dependency installation failed for %s', file_name)
                bot.reply_to(message_obj_for_reply, f'❌ Node dependency installation failed:\n{str(dep_err)[-1800:]}')
                return
        else:
            logger.info('Skipping full Node dependency scan on automatic repair retry %s/%s for %s',
                        auto_repair_retry, AUTO_REPAIR_MAX_RETRIES, file_name)

        log_file_path = os.path.join(user_folder, f"{os.path.splitext(os.path.basename(file_name))[0]}.log")
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        port = hosted_port_for_user(script_owner_id, file_name)
        logger.info('Selected hosting port %s for Node project %s', port, file_name)
        process = subprocess.Popen(['node', script_path], cwd=user_folder, env=_project_env(script_owner_id, port),
                                   stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   start_new_session=(os.name != 'nt'), preexec_fn=_child_preexec_memory_limit())
        bot_scripts[script_key] = {'process':process,'log_file':log_file,'file_name':file_name,
            'chat_id':message_obj_for_reply.chat.id,'script_owner_id':script_owner_id,
            'start_time':datetime.now(),'user_folder':user_folder,'type':'js','script_key':script_key,
            'log_file_path':log_file_path, 'auto_repair_retry': auto_repair_retry}
        bot.reply_to(message_obj_for_reply, f"✅ Node project `{file_name}` started! (PID: {process.pid})\n🔄 Attempt: {attempt} | Auto-fix retry: {auto_repair_retry}/{AUTO_REPAIR_MAX_RETRIES}")
        threading.Thread(target=_watch_started_process,
                         args=(script_key, process, user_folder, log_file_path, message_obj_for_reply, file_name, 'js', auto_repair_retry), daemon=True).start()
    except FileNotFoundError:
        bot.reply_to(message_obj_for_reply, '❌ Node.js is not installed on this hosting server.')
    except Exception as e:
        logger.exception('Node runner error')
        bot.reply_to(message_obj_for_reply, f'❌ Error starting Node project: {e}')


def run_npm_start(user_folder, script_owner_id, message_obj_for_reply, auto_repair_retry=0):
    if not _guard_duplicate_start(script_owner_id, 'npm_start', message_obj_for_reply):
        return
    token_check = _check_token_collision_before_start(user_folder, script_owner_id, None, message_obj_for_reply)
    if not token_check.get('ok', True):
        return
    script_key = f'{script_owner_id}_npm_start'
    log_file_path = os.path.join(user_folder, 'npm_start.log')
    try:
        log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        port = hosted_port_for_user(script_owner_id, 'npm_start')
        logger.info('Selected hosting port %s for npm project', port)
        process = subprocess.Popen(['npm', 'start'], cwd=user_folder, env=_project_env(script_owner_id, port),
                                   stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   start_new_session=(os.name != 'nt'), preexec_fn=_child_preexec_memory_limit())
        bot_scripts[script_key] = {'process':process,'log_file':log_file,'file_name':'npm_start',
            'chat_id':message_obj_for_reply.chat.id,'script_owner_id':script_owner_id,
            'start_time':datetime.now(),'user_folder':user_folder,'type':'npm','script_key':script_key,
            'log_file_path':log_file_path, 'auto_repair_retry': auto_repair_retry}
        bot.reply_to(message_obj_for_reply, f'✅ npm start launched! (PID: {process.pid})')
        threading.Thread(target=_watch_started_process,
                         args=(script_key, process, user_folder, log_file_path, message_obj_for_reply, 'npm_start', 'npm', auto_repair_retry), daemon=True).start()
    except Exception as e:
        logger.exception('npm start error')
        bot.reply_to(message_obj_for_reply, f'❌ Error starting npm project: {e}')


def _detect_universal_project(project_dir):
    """Detect common project ecosystems from manifests/entry files."""
    checks = [
        ('package.json', 'npm'), ('pnpm-workspace.yaml', 'npm'), ('yarn.lock', 'npm'),
        ('requirements.txt', 'py'), ('pyproject.toml', 'py'), ('Pipfile', 'py'),
        ('composer.json', 'php'), ('go.mod', 'go'), ('Cargo.toml', 'rust'),
        ('pom.xml', 'java'), ('build.gradle', 'java'), ('build.gradle.kts', 'java'),
        ('Gemfile', 'ruby'), ('Gemfile.lock', 'ruby'),
    ]
    names = {x.lower(): x for x in os.listdir(project_dir)}
    for marker, typ in checks:
        if marker.lower() in names:
            return typ
    # Source-only projects.
    ext_map = {
        '.ts':'ts', '.tsx':'ts', '.go':'go', '.rs':'rust', '.java':'java',
        '.kt':'kotlin', '.kts':'kotlin', '.rb':'ruby', '.swift':'swift'
    }
    counts = {}
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
        for f in files:
            typ = ext_map.get(Path(f).suffix.lower())
            if typ: counts[typ] = counts.get(typ, 0) + 1
    if counts:
        return max(counts, key=counts.get)
    return None


def _universal_entry(project_dir, project_type):
    preferred = {
        'go':['main.go'], 'rust':['src/main.rs'], 'java':['Main.java','Application.java'],
        'ruby':['main.rb','app.rb','bot.rb'], 'kotlin':['Main.kt','Application.kt'],
        'swift':['main.swift'], 'ts':['index.ts','main.ts','app.ts','server.ts','index.tsx']
    }.get(project_type, [])
    for name in preferred:
        p = os.path.join(project_dir, name)
        if os.path.isfile(p): return name
    # Find first reasonable source file.
    exts = {'go':('.go',),'rust':('.rs',),'java':('.java',),'ruby':('.rb',),
            'kotlin':('.kt','.kts'),'swift':('.swift',),'ts':('.ts','.tsx')}.get(project_type, ())
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in PROJECT_SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(exts): return os.path.relpath(os.path.join(root,f), project_dir)
    return None


def _install_universal_dependencies(project_dir, project_type, message):
    """Resolve dependencies for universal runtimes; fail with actionable logs."""
    if project_type in {'npm', 'py', 'php'}:
        # Handled by _install_project_dependencies.
        return
    if project_type == 'ts':
        package_path = os.path.join(project_dir, 'package.json')
        data = {}
        if os.path.isfile(package_path):
            try:
                data = json.loads(Path(package_path).read_text(encoding='utf-8'))
            except Exception:
                data = {}
        data.setdefault('name', 'hosted-typescript-project')
        data.setdefault('version', '1.0.0')
        data['private'] = True
        dev = data.setdefault('devDependencies', {})
        if not isinstance(dev, dict):
            dev = {}
            data['devDependencies'] = dev
        if 'tsx' not in dev:
            dev['tsx'] = '^4.0.0'
            Path(package_path).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        npm = shutil.which('npm')
        if not npm:
            raise RuntimeError('TypeScript project detected, but Node.js/npm is unavailable on this host.')
        result = _run_checked([npm, 'install', '--no-audit', '--no-fund'], project_dir, 'tsx/npm install')
        if result.returncode != 0:
            raise RuntimeError('TypeScript runtime dependency install failed: ' + (result.stderr or result.stdout)[-1800:])
        return

    # These ecosystems are normally installed by _install_project_dependencies
    # when their manifest exists. This fallback supports source-only projects.
    commands = {
        'go': (['go', 'mod', 'download'], 'Go'),
        'rust': (['cargo', 'fetch'], 'Rust/Cargo'),
        'ruby': (['bundle', 'install'], 'Ruby/Bundler'),
    }
    if project_type in commands:
        command, label = commands[project_type]
        executable = shutil.which(command[0])
        manifest = {'go':'go.mod', 'rust':'Cargo.toml', 'ruby':'Gemfile'}[project_type]
        if not os.path.isfile(os.path.join(project_dir, manifest)):
            return
        if not executable:
            raise RuntimeError(f'{manifest} detected, but {label} is not installed on this host.')
        command[0] = executable
        result = _run_checked(command, project_dir, f'{label} dependency resolution')
        if result.returncode != 0:
            raise RuntimeError(f'{label} dependency resolution failed: ' + (result.stderr or result.stdout)[-1800:])
        return

    if project_type == 'java':
        pom = os.path.join(project_dir, 'pom.xml')
        gradle_names = ('build.gradle', 'build.gradle.kts')
        if os.path.isfile(pom):
            mvn = shutil.which('mvn')
            if mvn:
                command = [mvn, '-B', '-DskipTests', 'dependency:resolve']
            elif os.path.isfile(os.path.join(project_dir, 'mvnw')):
                command = ['sh', './mvnw', '-B', '-DskipTests', 'dependency:resolve']
            else:
                raise RuntimeError('Java Maven project detected, but Maven/Maven Wrapper is unavailable.')
            result = _run_checked(command, project_dir, 'Maven dependency resolve')
            if result.returncode != 0:
                raise RuntimeError('Maven dependency resolution failed: ' + (result.stderr or result.stdout)[-1800:])
        elif any(os.path.isfile(os.path.join(project_dir, n)) for n in gradle_names):
            gradle = shutil.which('gradle')
            if os.path.isfile(os.path.join(project_dir, 'gradlew')):
                command = ['sh', './gradlew', '--no-daemon', 'dependencies']
            elif gradle:
                command = [gradle, '--no-daemon', 'dependencies']
            else:
                raise RuntimeError('Java Gradle project detected, but Gradle/Gradle Wrapper is unavailable.')
            result = _run_checked(command, project_dir, 'Gradle dependency resolve')
            if result.returncode != 0:
                raise RuntimeError('Gradle dependency resolution failed: ' + (result.stderr or result.stdout)[-1800:])
        return

    if project_type == 'swift':
        if os.path.isfile(os.path.join(project_dir, 'Package.swift')):
            swift = shutil.which('swift')
            if not swift:
                raise RuntimeError('Package.swift detected, but Swift toolchain is unavailable on this host.')
            result = _run_checked([swift, 'package', 'resolve'], project_dir, 'Swift package resolve')
            if result.returncode != 0:
                raise RuntimeError('Swift dependency resolution failed: ' + (result.stderr or result.stdout)[-1800:])


def run_universal_project(project_dir, script_owner_id, file_name, message_obj_for_reply, project_type, entry, auto_repair_retry=0):
    """Run common non-Python/Node/PHP project types using their native toolchain."""
    if not _guard_duplicate_start(script_owner_id, file_name, message_obj_for_reply):
        return
    script_key = f'{script_owner_id}_{file_name}'
    log_file_path = os.path.join(project_dir, f'{Path(file_name).stem}.log')
    commands = {
        'go': ['go','run','.'],
        'rust': ['cargo','run','--release'],
        'java': (['mvn','-q','-DskipTests','exec:java'] if os.path.isfile(os.path.join(project_dir,'pom.xml')) else ['java', Path(entry).stem]),
        'ruby': ['ruby', entry],
        'kotlin': ['kotlinc', entry, '-include-runtime', '-d', '__hosting.jar'],
        'swift': ['swift','run'] if os.path.isfile(os.path.join(project_dir,'Package.swift')) else ['swift', entry],
        'ts': ['npm','exec','--','tsx',entry],
    }
    command = commands.get(project_type)
    if not command:
        raise RuntimeError(f'Unsupported project runtime: {project_type}')
    if project_type == 'ts' and auto_repair_retry == 0:
        _install_universal_dependencies(project_dir, project_type, message_obj_for_reply)
    if shutil.which(command[0]) is None and command[0] != 'npx':
        raise RuntimeError(f'{project_type} runtime/tool `{command[0]}` is not installed on this VPS.')
    if project_type == 'kotlin':
        compile_result = _run_checked(command, project_dir, 'kotlin compile')
        if compile_result.returncode != 0:
            raise RuntimeError((compile_result.stderr or compile_result.stdout)[-2200:])
        command = ['java','-jar','__hosting.jar']
    log_file = open(log_file_path,'w',encoding='utf-8',errors='ignore')
    process = subprocess.Popen(command, cwd=project_dir, env=_project_env(script_owner_id, hosted_port_for_user(script_owner_id, file_name)),
                               stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               start_new_session=(os.name != 'nt'), preexec_fn=_child_preexec_memory_limit())
    bot_scripts[script_key] = {'process':process,'log_file':log_file,'file_name':file_name,
        'chat_id':message_obj_for_reply.chat.id,'script_owner_id':script_owner_id,
        'start_time':datetime.now(),'user_folder':project_dir,'type':project_type,
        'script_key':script_key,'log_file_path':log_file_path,'auto_repair_retry':auto_repair_retry}
    bot.reply_to(message_obj_for_reply, f'✅ {project_type.upper()} project `{file_name}` started! (PID: {process.pid})')
    threading.Thread(target=_watch_started_process,
        args=(script_key, process, project_dir, log_file_path, message_obj_for_reply, file_name, project_type, auto_repair_retry), daemon=True).start()



# ========== UNIVERSAL ZIP ENTRY RESOLVER v2 ==========
# Deterministic manifests first, heuristics second, AI only for genuine ambiguity.

_UNIVERSAL_ENTRY_EXTS = {'.js': 'js', '.mjs': 'js', '.cjs': 'js',
                         '.py': 'py', '.php': 'php', '.html': 'static', '.htm': 'static'}


def _safe_rel_entry(project_root, value):
    """Validate a manifest-selected relative entry without allowing traversal."""
    if not isinstance(value, str):
        return None
    value = value.strip().strip('"\'')
    if not value or value.startswith(('/', '\\')):
        return None
    norm = os.path.normpath(value).replace('\\', '/')
    if norm in ('..', '.') or norm.startswith('../') or '/..' in norm:
        return None
    path = os.path.join(project_root, norm)
    try:
        if os.path.isfile(path) and os.path.commonpath([os.path.abspath(project_root), os.path.abspath(path)]) == os.path.abspath(project_root):
            return norm
    except (OSError, ValueError):
        return None
    return None


def _command_entry_from_text(project_root, command):
    """Extract a safe entry from common node/python/php command forms."""
    if not isinstance(command, str):
        return None
    cmd = command.strip()
    # Do not execute this string; only inspect it.
    patterns = (
        r'^(?:node|nodejs|bun|tsx|ts-node|python|python3|py|php)\s+([\"\']?[^\s\"\']+[\"\']?)',
    )
    for pattern in patterns:
        m = re.match(pattern, cmd, re.I)
        if m:
            target = _safe_rel_entry(project_root, m.group(1))
            if target:
                ext = os.path.splitext(target)[1].lower()
                return target, _UNIVERSAL_ENTRY_EXTS.get(ext, 'unknown')
    return None


def _read_procfile(project_root):
    p = os.path.join(project_root, 'Procfile')
    if not os.path.isfile(p):
        return None
    try:
        content = Path(p).read_text(encoding='utf-8', errors='ignore')
        for raw in content.splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or ':' not in line:
                continue
            kind, cmd = line.split(':', 1)
            if kind.strip().lower() not in {'web', 'worker', 'bot'}:
                continue
            found = _command_entry_from_text(project_root, cmd.strip())
            if found:
                return found[0], found[1], f'Procfile: {cmd.strip()}'
    except Exception as e:
        logger.warning('Procfile parse failed: %s', e)
    return None


def _read_railway_json(project_root):
    p = os.path.join(project_root, 'railway.json')
    if not os.path.isfile(p):
        return None
    try:
        data = json.loads(Path(p).read_text(encoding='utf-8', errors='ignore'))
        commands = []
        if isinstance(data, dict):
            deploy = data.get('deploy')
            build = data.get('build')
            for obj in (data, deploy, build):
                if isinstance(obj, dict):
                    for key in ('startCommand', 'start', 'command', 'run'):
                        if isinstance(obj.get(key), str):
                            commands.append(obj[key])
        for cmd in commands:
            found = _command_entry_from_text(project_root, cmd)
            if found:
                return found[0], found[1], f'railway.json: {cmd}'
    except Exception as e:
        logger.warning('railway.json parse failed: %s', e)
    return None


def _read_runtime_txt(project_root):
    p = os.path.join(project_root, 'runtime.txt')
    if not os.path.isfile(p):
        return None
    try:
        content = Path(p).read_text(encoding='utf-8', errors='ignore').strip().lower()
        if content.startswith('python-') or content.startswith('python'):
            return 'py'
        if content.startswith('node-') or content.startswith('node'):
            return 'js'
    except Exception:
        pass
    return None


def _read_package_json_start(project_root):
    p = os.path.join(project_root, 'package.json')
    if not os.path.isfile(p):
        return None
    try:
        data = json.loads(Path(p).read_text(encoding='utf-8', errors='ignore'))
        scripts = data.get('scripts') if isinstance(data, dict) else None
        if isinstance(scripts, dict) and isinstance(scripts.get('start'), str):
            found = _command_entry_from_text(project_root, scripts['start'])
            if found:
                return found[0], found[1], f"package.json scripts.start: {scripts['start']}"
        if isinstance(data, dict) and isinstance(data.get('main'), str):
            target = _safe_rel_entry(project_root, data['main'])
            if target:
                ext = os.path.splitext(target)[1].lower()
                return target, _UNIVERSAL_ENTRY_EXTS.get(ext, 'unknown'), f"package.json main: {data['main']}"
    except Exception as e:
        logger.warning('package.json start/main parse failed: %s', e)
    return None


def _score_entry_file(project_root, rel_path):
    """Score likely application entry files; helpers/config/setup are penalized."""
    name = os.path.basename(rel_path).lower()
    base, ext = os.path.splitext(name)
    score = 0
    name_scores = {
        'index': 100, 'main': 95, 'bot': 90, 'app': 85, 'server': 80,
        'start': 75, 'drenox': 70, 'pair': 60, 'client': 55,
    }
    score += name_scores.get(base, 10)
    score -= rel_path.count(os.sep) * 5
    try:
        size = os.path.getsize(os.path.join(project_root, rel_path))
        if 5_000 <= size <= 100_000:
            score += 30
        elif size < 5_000:
            score += 10
        elif size > 500_000:
            score -= 20
    except OSError:
        pass

    try:
        text = Path(os.path.join(project_root, rel_path)).read_text(encoding='utf-8', errors='ignore')[:5000]
        signals = [
            'require(', 'import ', 'from "', "from '", 'if __name__', 'def main(',
            'async def', 'app = Flask', 'app = FastAPI', 'bot =', 'client =',
            'makeWASocket', 'TeleBot', 'TelegramClient', 'new Client(',
            'express()', 'app.listen', 'createServer', 'bot.launch(', 'bot.start_polling',
        ]
        score += sum(15 for sig in signals if sig in text)
    except Exception:
        pass

    if any(x in name for x in ('util', 'helper', 'config', 'setting', 'test_', '_test', 'package-lock', 'security_scanner', 'setup')):
        score -= 80
    return score, ext


def _find_best_entry_by_score(project_root, lang_exts):
    candidates = []
    skip = set(globals().get('PROJECT_SKIP_DIRS', {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'vendor', 'dist', 'build'}))
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in lang_exts:
                continue
            rel = os.path.relpath(os.path.join(root, f), project_root).replace('\\', '/')
            score, _ = _score_entry_file(project_root, rel)
            candidates.append((score, rel, _UNIVERSAL_ENTRY_EXTS.get(ext, 'unknown')))
    if not candidates:
        return None, []
    candidates.sort(key=lambda x: (-x[0], x[1].lower()))
    return candidates[0], candidates


def _ai_detect_project_type(project_root, message_obj=None):
    """Use OpenRouter only as an ambiguity resolver; never execute its command output."""
    if not OPENROUTER_API_KEY or not ai_settings.get('enabled', True):
        return None
    skip = set(globals().get('PROJECT_SKIP_DIRS', {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'vendor', 'dist', 'build'}))
    files = []
    for root, dirs, fs in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in fs:
            files.append(os.path.relpath(os.path.join(root, f), project_root).replace('\\', '/'))
            if len(files) >= 200:
                break
        if len(files) >= 200:
            break
    manifests = {}
    for name in ('package.json', 'Procfile', 'requirements.txt', 'composer.json', 'railway.json', 'runtime.txt'):
        path = os.path.join(project_root, name)
        if os.path.isfile(path):
            try:
                manifests[name] = Path(path).read_text(encoding='utf-8', errors='ignore')[:2500]
            except Exception:
                pass
    prompt = f"""Analyze this uploaded project and identify the single most likely entry file.\nFILES:\n{json.dumps(files, ensure_ascii=False)}\nMANIFESTS:\n{json.dumps(manifests, ensure_ascii=False)}\nReturn ONLY JSON with entry_file and runtime. The entry_file must be one of FILES. Do not invent shell commands. runtime must be python, node, php, static, or other."""
    try:
        r = requests.post(
            OPENROUTER_BASE_URL,
            headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}', 'Content-Type': 'application/json', 'X-Title': 'Darkwest Hosting Entry Detection'},
            json={'model': OPENROUTER_MODEL, 'messages': [
                {'role': 'system', 'content': 'Return strict JSON only.'},
                {'role': 'user', 'content': prompt}], 'temperature': 0, 'max_tokens': 250},
            timeout=40
        )
        r.raise_for_status()
        content = r.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', content, re.S)
        if not match:
            return None
        result = json.loads(match.group(0))
        entry = _safe_rel_entry(project_root, result.get('entry_file', ''))
        runtime = str(result.get('runtime', '')).lower().strip()
        if entry and runtime in {'python', 'node', 'php', 'static', 'other'}:
            return {'entry_file': entry, 'runtime': {'python':'py','node':'js','php':'php','static':'static'}.get(runtime, 'other'), 'confidence': float(result.get('confidence', 0.5) or 0.5)}
    except Exception as e:
        logger.warning('AI entry detection failed: %s', e)
    return None


def _resolve_entry(project_root, message_obj=None):
    """Resolve entry deterministically first, then heuristically, then AI."""
    for resolver in (_read_procfile, _read_railway_json, _read_package_json_start):
        result = resolver(project_root)
        if result:
            return result

    runtime_hint = _read_runtime_txt(project_root)
    exts = {'.py'} if runtime_hint == 'py' else {'.js', '.mjs', '.cjs'} if runtime_hint == 'js' else {'.py', '.js', '.mjs', '.cjs', '.php', '.html', '.htm'}
    best, candidates = _find_best_entry_by_score(project_root, exts)
    if best:
        score, entry, ftype = best
        ambiguous = len(candidates) > 1 and (score - candidates[1][0] <= 12)
        if message_obj is not None and (score < 80 or ambiguous):
            ai = _ai_detect_project_type(project_root, message_obj)
            if ai and ai.get('confidence', 0) >= 0.6:
                return ai['entry_file'], ai['runtime'], f"AI confidence {ai['confidence']:.2f}"
        return entry, ftype, f"heuristic score {score}"

    if message_obj is not None:
        ai = _ai_detect_project_type(project_root, message_obj)
        if ai:
            return ai['entry_file'], ai['runtime'], f"AI confidence {ai.get('confidence', 0):.2f}"
    return None, None, 'no entry found'


def _flatten_nested_hosting_wrapper(user_folder, user_id):
    """Safely flatten nested upload_bots wrappers, preserving conflicting files."""
    root = os.path.abspath(user_folder)
    changed = False

    def merge_dir(src_dir, dst_dir):
        nonlocal changed
        os.makedirs(dst_dir, exist_ok=True)
        for name in os.listdir(src_dir):
            src = os.path.join(src_dir, name)
            dst = os.path.join(dst_dir, name)
            if not os.path.exists(dst):
                shutil.move(src, dst)
                changed = True
            elif os.path.isdir(src) and os.path.isdir(dst):
                merge_dir(src, dst)
                try:
                    os.rmdir(src)
                except OSError:
                    pass
            else:
                # Never delete/overwrite existing user data. Keep conflict in place.
                logger.warning("Flatten skipped conflicting path: %s", dst)

    for _ in range(15):
        bare = os.path.join(root, 'upload_bots')
        if not os.path.isdir(bare):
            break
        # Flatten any immediate nested upload_bots/<id>/ contents, regardless of ID.
        try:
            items = list(os.listdir(bare))
        except OSError:
            break
        if not items:
            try:
                os.rmdir(bare)
                changed = True
            except OSError:
                pass
            continue
        moved_any = False
        for name in items:
            src = os.path.join(bare, name)
            if os.path.isdir(src) and os.path.isdir(os.path.join(src, 'upload_bots')):
                inner = os.path.join(src, 'upload_bots')
                before = changed
                merge_dir(inner, root)
                moved_any = moved_any or changed != before
                # Remove only empty wrapper directories; don't recursively delete conflicts.
                try:
                    os.rmdir(inner)
                    os.rmdir(src)
                except OSError:
                    pass
                continue
            dst = os.path.join(root, name)
            before = changed
            if not os.path.exists(dst):
                shutil.move(src, dst)
                changed = True
            elif os.path.isdir(src) and os.path.isdir(dst):
                merge_dir(src, dst)
            else:
                logger.warning("Flatten skipped conflicting path: %s", dst)
            moved_any = moved_any or changed != before
        try:
            os.rmdir(bare)
            changed = True
        except OSError:
            pass
        if not moved_any:
            break

    if changed:
        logger.warning('Flattened nested hosting wrapper for user %s', user_id)
    return changed

def process_zip_file(zip_path, user_id, user_folder, file_name_zip, message, temp_dir=None):
    """Universal ZIP deployment with safe root detection and layered entry resolution."""
    cleanup_temp = False
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix=f'user_{user_id}_zip_')
        cleanup_temp = True
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            base = os.path.abspath(temp_dir)
            for member in z.infolist():
                target = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not (target == base or target.startswith(base + os.sep)):
                    raise zipfile.BadZipFile('ZIP contains an unsafe path')
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise zipfile.BadZipFile('ZIP symlinks are not allowed')
            z.extractall(temp_dir)

        project_root = _detect_project_root(temp_dir)
        logger.info('ZIP project root detected: user=%s archive=%s root=%s', user_id, file_name_zip, project_root)

        package_path = os.path.join(project_root, 'package.json')
        has_static_entry = any(os.path.isfile(os.path.join(project_root, n)) for n in ('index.html', 'index.htm'))
        has_node_project = os.path.isfile(package_path) or (not has_static_entry and any(
            name.endswith(NODE_RUNTIME_EXTS) for _, _, names in os.walk(project_root) for name in names
        ))
        universal_type = _detect_universal_project(project_root)

        # Resolve from the original project metadata BEFORE creating hosting wrappers.
        # This prevents an auto-generated package.json from overriding the user's manifest.
        entry, file_type, reason = _resolve_entry(project_root, message)

        node_entry_override = prepare_node_project_for_hosting(project_root) if has_node_project else None
        if node_entry_override:
            entry, file_type, reason = node_entry_override, 'js', 'Node/MD hosting bootstrap'
        elif universal_type in {'go','rust','java','ruby','kotlin','swift','ts'} and not entry:
            entry = _universal_entry(project_root, universal_type)
            file_type = universal_type
            reason = f'universal runtime {universal_type}'

        if not entry:
            raise RuntimeError('No supported project entry was detected in the ZIP.')

        # Stop this user's existing bots BEFORE dependency installation.
        # Other users' bots are never touched.
        with _user_start_lock(user_id):
            for key, info in list(bot_scripts.items()):
                if info.get('script_owner_id') == user_id:
                    logger.info("Stopping existing process %s before deployment", key)
                    kill_process_tree(info)
                    bot_scripts.pop(key, None)

            _install_project_dependencies(project_root, message)
            if universal_type:
                _install_universal_dependencies(project_root, universal_type, message)

        if file_type == 'py':
            wrapper = _python_web_wrapper(project_root, entry)
            if wrapper:
                entry = wrapper

        # Deploy/verify the new project first. Only clear the old file index
        # after replacement succeeds, so a failed deployment doesn't leave the
        # user's existing file list empty.
        _safe_replace_project(user_folder, project_root)
        _flatten_nested_hosting_wrapper(user_folder, user_id)
        remove_all_user_files_db(user_id)
        user_files[user_id] = []

        entry = os.path.normpath(entry).replace('\\', '/')

        prefix = f"upload_bots/{user_id}/"
        while entry.startswith(prefix):
            entry = entry[len(prefix):]

        entry = entry.lstrip('/')

        if entry.startswith('../') or entry == '..' or os.path.isabs(entry):
            raise RuntimeError(f'Invalid project entry path: {entry}')

        script_path = os.path.join(user_folder, entry)
        if not os.path.isfile(script_path) and file_type != 'npm':
            raise RuntimeError(f'Entry file was not found after deployment: {entry}')

        save_user_file(user_id, entry, file_type)
        if file_type == 'npm':
            # The UI and lifecycle callbacks use this virtual entry to represent
            # package.json projects launched through `npm start`.
            save_user_file(user_id, 'npm_start', 'npm')
        _write_zip_project_marker(user_folder, file_name_zip, entry)

        bot.reply_to(message, f'🔍 Entry: `{entry}`\n⚙️ Type: `{file_type}`\n📌 Detection: {reason}\n🚀 Starting...', parse_mode='Markdown')

        if file_type == 'npm':
            threading.Thread(target=run_npm_start, args=(user_folder, user_id, message, 0), daemon=True).start()
        elif file_type == 'py':
            threading.Thread(target=run_script, args=(script_path, user_id, user_folder, entry, message, 1, 0), daemon=True).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(script_path, user_id, user_folder, entry, message, 1, 0), daemon=True).start()
        elif file_type == 'php':
            threading.Thread(target=run_php_script, args=(script_path, user_id, user_folder, entry, message, 0), daemon=True).start()
        elif file_type == 'static':
            threading.Thread(target=run_static_site, args=(script_path, user_id, user_folder, entry, message, 0), daemon=True).start()
        elif file_type in {'go','rust','java','ruby','kotlin','swift','ts'}:
            threading.Thread(target=run_universal_project, args=(user_folder, user_id, entry, message, file_type, entry), daemon=True).start()
        else:
            raise RuntimeError(f'Unsupported detected project type: {file_type}')
        return True
    except Exception as e:
        logger.error('Error processing ZIP: %s', e, exc_info=True)
        try:
            bot.reply_to(message, f'❌ Error processing ZIP: {str(e)[:3500]}')
        except Exception:
            logger.exception('Failed to send ZIP error message')
        return False
    finally:
        if cleanup_temp and temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# Unlimited multi-bot model: no artificial per-user/per-hosted-script count limit is imposed here.
# Capacity is determined by the VPS/platform resources and the hosted apps themselves.
if __name__ == '__main__':
    logger.info('🛡️ Multi-bot safety enabled: isolated Python dependencies, serialized installs, per-user start locking.')
    ensure_node_installed()
    logger.info("="*50 + "\n🤖 DIV Hosting Bot Starting Up... (FULL AUTO - Approval Required)\n" + f"🐍 Python: {sys.version.split()[0]}\n" +
                f"🔧 Base Dir: {BASE_DIR}\n📁 Upload Dir: {UPLOAD_BOTS_DIR}\n" +
                f"📊 Data Dir: {IROTECH_DIR}\n🔑 Owner ID: {OWNER_ID}\n🛡️ Admins: {len(admin_ids)}\n" +
                f"🚫 Banned Users: {len(banned_users)}\n📢 Mandatory Channels: {len(mandatory_channels)}\n" +
                f"🔓 Trusted Users (no approval): {list(TRUSTED_USERS)}\n" +
                f"🤖 AI Auto-Fix: {bool(OPENROUTER_API_KEY)} / Model: {OPENROUTER_MODEL} / Owner approval required\n" +
                "="*50)
    keep_alive()
    logger.info("🚀 Starting polling...")
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout: 
            logger.warning("Polling ReadTimeout. Restarting in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as ce: 
            logger.error(f"Polling ConnectionError: {ce}. Retrying in 15s...")
            time.sleep(15)
        except Exception as e:
            logger.critical(f"💥 Unrecoverable polling error: {e}", exc_info=True)
            logger.info("Restarting polling in 30s due to critical error...")
            time.sleep(30)
        finally: 
            logger.warning("Polling attempt finished. Will restart if in loop.")
            time.sleep(1)
