from docuseal import docuseal
import subprocess
from flask import Flask, request
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import imaplib
import time
import logging
import sys
from logging.handlers import RotatingFileHandler
from email.utils import formatdate, formataddr

docuseal.key = "xHPyWnY8iyRLuTG9XuRjYZWKA1tAqSAnnwKa27YzYcT"
docuseal.url = "https://servis.sevenet.sk/api/"

# SMTP adatok
SMTP_SERVER = "mail3.sevenet.sk"
SMTP_PORT = 587
IMAP_SERVER = "mail3.sevenet.sk"
IMAP_PORT = 993
SENDER_EMAIL = "faktury@sevenet.sk"
SENDER_PASSWORD = "?,SINNEt,29"

# Logger beállítása
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'service_sheet_sender.log')
logger = logging.getLogger('service_sheet_sender')
logger.setLevel(logging.INFO)

# File handler
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler (stdout)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Flask webhook listener
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    event_type = data.get('event_type')
    
    logger.info(f"Webhook kapott - Event type: {event_type}")
    
    # Event típus alapján különböző handler-ek
    if event_type == 'submission.completed':
        return handle_submission_completed(data)
    elif event_type == 'submission.created':
        return handle_submission_created(data)
    else:
        logger.warning(f"Ismeretlen event típus: {event_type}")
        return {'status': 'ok'}, 200


def handle_submission_completed(data):
    """submission.completed event feldolgozása"""
    submission_data = data.get('data', {})
    submission_id = submission_data.get('submission_id') or submission_data.get('id')

    email_recipient = None
    pdf_url = None
    name = None

    # Régi struktúra: data.values
    for item in submission_data.get('values', []):
        if item.get('field') == 'Email':
            email_recipient = item.get('value')
            break

    # Új struktúra: submitters list
    submitters = submission_data.get('submitters', [])
    if submitters:
        first_submitter = submitters[0]
        email_recipient = email_recipient or first_submitter.get('email')
        for item in first_submitter.get('values', []):
            if item.get('field') == 'Email':
                email_recipient = item.get('value')
                break

        documents = first_submitter.get('documents', [])
        if documents:
            pdf_url = documents[0].get('url')
            name = documents[0].get('name')

    if not pdf_url:
        documents = submission_data.get('documents', [])
        if documents:
            pdf_url = documents[0].get('url')
            name = documents[0].get('name')

    if not submission_id:
        logger.error("Nincs submission_id a webhookban")
        return {'status': 'error', 'message': 'submission_id hiányzik'}, 400

    if not pdf_url or not name:
        logger.error("Nincs PDF dokumentum a webhookban")
        return {'status': 'error', 'message': 'PDF dokumentum hiányzik'}, 400

    response = docuseal.get_submission_documents(submission_id)
    pdf_url = response['documents'][0]['url']
    name = response['documents'][0]['name']

    # PDF letöltése a tmp mappába
    os.makedirs('tmp', exist_ok=True)
    pdf_path = f'tmp/{name}.pdf'
    try:
        subprocess.run(['wget', pdf_url, '-O', pdf_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF letöltési hiba: {e}")
        return {'status': 'error', 'message': 'PDF letöltés sikertelen'}, 500

    logger.info(f"submission_id: {submission_id}")
    logger.info(f"email: {email_recipient}")
    logger.info(f"PDF letöltve: {pdf_path}")

    recipient = email_recipient or "arnoldx17@gmail.com"
    if not email_recipient:
        logger.warning("Nincs Email mező az adatokban, teszt címre küldve")

    # Email küldés
    try:
        send_email(pdf_path, name, recipient)
        logger.info("Email sikeresen elküldve")
    except Exception as e:
        logger.exception(f"Hiba az email küldéskor: {e}")
        return {'status': 'error', 'message': 'Email küldés sikertelen'}, 500

    return {'status': 'ok'}, 200


def handle_submission_created(data):
    """submission.created event feldolgozása"""
    # TODO: Implementáció a submission.created event feldolgozására
    logger.info("submission.created event feldolgozása")
    return {'status': 'ok'}, 200


def send_email(pdf_path, pdf_name, recipient_email):
    """Email küldése PDF csatolmánnyal és mentése a Sent mappába"""
    msg = MIMEMultipart()
    msg['From'] = formataddr(('SEVENET s.r.o.', SENDER_EMAIL))
    msg['To'] = recipient_email
    msg['Subject'] = f'SEVENET s.r.o. - Servisny list - {pdf_name}'
    msg['Date'] = formatdate(localtime=True)

    body = f"{pdf_name}.pdf"
    msg.attach(MIMEText(body, 'plain'))

    # PDF csatolása
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as attachment:
            part = MIMEBase('application', 'pdf')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{pdf_name}.pdf"')
            msg.attach(part)

    # SMTP küldés
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()

    # IMAP-on keresztül a Sent mappába mentés
    sent_mailboxes = ['Sent', 'INBOX.Sent', 'Sent Items', 'INBOX.Sent Items']
    saved = False
    for mailbox in sent_mailboxes:
        try:
            imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            imap.login(SENDER_EMAIL, SENDER_PASSWORD)
            internal_date = imaplib.Time2Internaldate(time.time())
            imap.append(mailbox, '', internal_date, msg.as_bytes())
            imap.logout()
            logger.info(f"Email mentve a Sent mappába: {mailbox}")
            saved = True
            break
        except Exception as e:
            logger.warning(f"IMAP append hiba {mailbox}: {e}")
            try:
                imap.logout()
            except Exception:
                pass

    if not saved:
        logger.warning("Nem sikerült menteni az emailt a Sent mappába")


if __name__ == '__main__':
    print("Webhook listener indítása a 5000-es porton...")
    logger.info("Webhook listener indítása a 5000-es porton...")
    app.run(host='0.0.0.0', port=5000, debug=False)