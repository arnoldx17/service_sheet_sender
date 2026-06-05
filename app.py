from docuseal import docuseal
import subprocess
from flask import Flask, request
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

docuseal.key = "xHPyWnY8iyRLuTG9XuRjYZWKA1tAqSAnnwKa27YzYcT"
docuseal.url = "https://servis.sevenet.sk/api/"

# SMTP adatok
SMTP_SERVER = "mail3.sevenet.sk"
SMTP_PORT = 587
SENDER_EMAIL = "faktury@sevenet.sk"
SENDER_PASSWORD = "?,SINNEt,29"

# Flask webhook listener
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    submission_id = data.get('data', {}).get('submission_id')

    email_recipient = None
    for item in data.get('data', {}).get('values', []):
        if item.get('field') == 'Email':
            email_recipient = item.get('value')
            break

    response = docuseal.get_submission_documents(submission_id)
    pdf_url = response['documents'][0]['url']
    name = response['documents'][0]['name']

    # PDF letöltése a tmp mappába
    pdf_path = f'tmp/{name}.pdf'
    subprocess.run(['wget', pdf_url, '-O', pdf_path])

    print("Webhook kapott:", data)
    print(f"submission_id: {submission_id}")
    print(f"email: {email_recipient}")
    print(f"PDF letöltve: {pdf_path}")

    # Email küldés (TESZT: akrausz@sevenet.sk)
    try:
        send_email(pdf_path, name, "akrausz@sevenet.sk")
        print("Email sikeresen elküldve")
    except Exception as e:
        print(f"Hiba az email küldéskor: {e}")

    return {'status': 'ok'}, 200


def send_email(pdf_path, pdf_name, recipient_email):
    """Email küldése PDF csatolmánnyal"""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f'Servisny list - {pdf_name}'

    body = f"Csatolt a servisny list: {pdf_name}.pdf"
    msg.attach(MIMEText(body, 'plain'))

    # PDF csatolása
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as attachment:
            part = MIMEBase('application', 'pdf')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{pdf_name}.pdf"')
            msg.attach(part)

    # SMTP kapcsolat és email küldés
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()

if __name__ == '__main__':
    print("Webhook listener indítása a 5000-es porton...")
    app.run(host='0.0.0.0', port=5000, debug=False)