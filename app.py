from docuseal import docuseal
import subprocess
from flask import Flask, request

docuseal.key = "xHPyWnY8iyRLuTG9XuRjYZWKA1tAqSAnnwKa27YzYcT"
docuseal.url = "https://servis.sevenet.sk/api/"

# Flask webhook listener
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    submission_id = data.get('data', {}).get('submission_id')

    email = None
    for item in data.get('data', {}).get('values', []):
        if item.get('field') == 'Email':
            email = item.get('value')
            break

    response = docuseal.get_submission_documents(submission_id)
    pdf_url = response['documents'][0]['url']
    name = response['documents'][0]['name']

    # PDF letöltése a tmp mappába
    subprocess.run(['wget', pdf_url, '-O', f'tmp/{name}.pdf'])

    print("Webhook kapott:", data)
    print(f"submission_id: {submission_id}")
    print(f"email: {email}")
    print(f"PDF letöltve: tmp/{name}.pdf")
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    print("Webhook listener indítása a 5000-es porton...")
    app.run(host='0.0.0.0', port=5000, debug=False)