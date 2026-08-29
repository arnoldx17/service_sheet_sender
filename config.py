import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DOCUSEAL_KEY = os.getenv("DOCUSEAL_KEY")
DOCUSEAL_URL = os.getenv("DOCUSEAL_URL")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
IMAP_SERVER = os.getenv("IMAP_SERVER") 
IMAP_PORT = os.getenv("IMAP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SPLYNX_HOST = os.getenv("SPLYNX_HOST")
SPLYNX_AUTH = os.getenv("SPLYNX_AUTH")
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER")
NEXTCLOUD_PASS = os.getenv("NEXTCLOUD_PASS")
NEXTCLOUD_AUTH = f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASS}"
NEXTCLOUD_CHAT_LINK = os.getenv("NEXTCLOUD_CHAT_LINK")