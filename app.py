from docuseal import docuseal
import subprocess
import json
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
import requests

from config import (
    DOCUSEAL_KEY,
    DOCUSEAL_URL,
    SMTP_SERVER,
    SMTP_PORT,
    IMAP_SERVER,
    IMAP_PORT,
    SENDER_EMAIL,
    SENDER_PASSWORD,
    SPLYNX_HOST,
    SPLYNX_AUTH
)

docuseal.key = DOCUSEAL_KEY
docuseal.url = DOCUSEAL_URL

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

    logger.info(f"Webhook data: {data}")

    submission_data = data.get('data', {})
    submission_id = submission_data.get('submission_id') or submission_data.get('id')

    email_recipient = None
    portal_id = None

    # Régi struktúra: data.values
    for item in submission_data.get('values', []):
        if item.get('field') == 'Email':
            email_recipient = item.get('value')
            break

    # Új struktúra: submitters list
    submitters = submission_data.get('submitters', [])
    if submitters:
        first_submitter = submitters[0]
        for item in first_submitter.get('values', []):
            if item.get('field') == 'Email':
                email_recipient = item.get('value')              
            if item.get('field') == 'Portal ID':
                portal_id = item.get('value')

    #Lekérjük a docuseal API-tól a dokumentum URL-jét és nevét
    response = docuseal.get_submission_documents(submission_id)
    pdf_url = response['documents'][0]['url']
    name = response['documents'][0]['name']

    logger.info(
        f"PDF URL: {pdf_url}, PDF Name: {name}, "
        f"Email: {email_recipient}, Portal ID: {portal_id}"
    )

    if not pdf_url or not name:
        logger.error(f"A dokumentumból hiányzik az URL vagy a név: {submission_id}")
        return {'status': 'error', 'message': 'Hiányos PDF dokumentum'}, 400

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

    #Feltöltjük a PDF-et a Splynx-be
    if portal_id is not None:
        upload_servisny_list_to_splynx(portal_id, name, pdf_path)

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
    logger.info("submission.created event feldolgozása")
    logger.info(f"Webhook data: {data}")

    submission_data = data.get('data', {})
    submission_id = submission_data.get('submission_id') or submission_data.get('id')
    template_name = submission_data.get('template', {}).get('name')
    submitters = submission_data.get('submitters', [])
    submitter_email = None
    if submitters:
        submitter_email = submitters[0].get('email')

    if not template_name or not submitter_email:
        logger.warning("submission.created webhookból hiányoznak a szükséges adatok")

    message_text = f"🛠️ Új szervizlap létrehozva\n📋 Név: {template_name}\n👤 Létrehozta: {submitter_email}\n🔗 https://servis.sevenet.sk/submissions/{submission_id}"

    # A megadott curl script Pythonból subprocess-szel
    curl_command = [
        'curl',
        '-X', 'POST',
        '-u', 'sevenetbot:j23sy-yA28P-oqH9w-SirXP-FDrkw',
        '-H', 'OCS-APIRequest: true',
        '-H', 'Accept: application/json',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({'message': message_text}),
        'https://cloud.sevenet.sk/ocs/v2.php/apps/spreed/api/v1/chat/53ixg5u5',
    ]

    try:
        subprocess.run(curl_command, check=True)
        logger.info("submission.created chat üzenet sikeresen elküldve")
    except subprocess.CalledProcessError as e:
        logger.error(f"Hiba a chat üzenet küldésekor: {e}")
        return {'status': 'error', 'message': 'Chat üzenet küldése sikertelen'}, 500

    return {'status': 'ok'}, 200


def send_email(pdf_path, pdf_name, recipient_email):
    """Email küldése PDF csatolmánnyal és mentése a Sent mappába"""
    msg = MIMEMultipart()
    msg['From'] = formataddr(('SEVENET s.r.o.', SENDER_EMAIL))
    msg['To'] = recipient_email
    msg['Subject'] = f'SEVENET s.r.o. - Servisný list - {pdf_name}'
    msg['Date'] = formatdate(localtime=True)

    body = f"Dobrý deň,\n\n v prílohe Vám zasielame podpísaný servisný list z vykonaného servisného zásahu.\n\n Ak ste boli s našimi službami a prácou našich technikov spokojní, budeme Vám veľmi vďační, ak si nájdete chvíľku a ohodnotíte nás na Google. Vaša spätná väzba je pre nás nesmierne dôležitá.\n Link: https://g.page/r/CfC2Gk1aicCAEBM/review\n\n Ďakujeme, že využívate naše služby.\n\n S pozdravom,\n SEVENET s.r.o.\n Úzka ulica 1623/7\n Štúrovo\n 943 01\n\n"
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

def upload_servisny_list_to_splynx(portal_id, pdf_name, pdf_path):
    try:
        # 1. Üres dokumentum rekord létrehozása a Splynx-ben
        doc_init_url = f"https://{SPLYNX_HOST}/api/2.0/admin/customers/customer-documents"
        doc_init_payload = {
            "customer_id": portal_id,
            "type": "uploaded",
            "title": pdf_name,
            "description": "Servisný list",
            "visible_by_customer": "1",
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": SPLYNX_AUTH
        }

        response = requests.post(
            doc_init_url,
            headers=headers,
            json=doc_init_payload,
            timeout=15
        )
        response.raise_for_status()
        
        splynx_document_id = response.json().get('id')
        if not splynx_document_id:
            raise ValueError("A Splynx válasza nem tartalmazott dokumentum ID-t.")

        logger.info(f"Splynx újonnan létrehozott dokumentum ID: {splynx_document_id}")

        # 2. A PDF fájl megnyitása és feltöltése
        upload_url = f"https://{SPLYNX_HOST}/api/2.0/admin/customers/customer-documents/{splynx_document_id}--upload"
        upload_headers = {
            "Authorization": SPLYNX_AUTH
        }

        with open(pdf_path, "rb") as f:
            files = {
                "file": (pdf_name, f, "application/pdf")
            }

            upload_response = requests.post(
                upload_url,
                headers=upload_headers,
                files=files,
                timeout=60
            )

        upload_response.raise_for_status()
        
        logger.info(f"Splynx feltöltés sikeres. Status: {upload_response.status_code}")

    except FileNotFoundError:
        logger.error(f"A megadott PDF fájl nem található a megadott útvonalon: {pdf_path}")
        raise

    except requests.exceptions.RequestException as e:
        logger.error(f"Hálózati / HTTP hiba történt a Splynx kommunikáció során: {str(e)}")
        if getattr(e, 'response', None) is not None:
            logger.error(f"Splynx hiba válasz: {e.response.text}")
        raise RuntimeError(f"Splynx feltöltési hiba: {str(e)}") from e

    except Exception as e:
        logger.error(f"Váratlan hiba történt a feltöltés közben: {str(e)}")
        raise

if __name__ == '__main__':
    print("Webhook listener indítása a 5000-es porton...")
    logger.info("Webhook listener indítása a 5000-es porton...")
    app.run(host='0.0.0.0', port=5000, debug=False)