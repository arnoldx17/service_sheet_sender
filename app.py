from docuseal import docuseal
import subprocess
from flask import Flask, request

docuseal.key = "xHPyWnY8iyRLuTG9XuRjYZWKA1tAqSAnnwKa27YzYcT"
docuseal.url = "https://servis.sevenet.sk/api/"

response = docuseal.get_submission_documents(40)
pdf_url = response['documents'][0]['url']
name = response['documents'][0]['name']

# PDF letöltése a tmp mappába
subprocess.run(['wget', pdf_url, '-O', f'tmp/{name}.pdf'])

print(f"PDF letöltve: tmp/{name}.pdf")

# Flask webhook listener
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Webhook kapott:", data)
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    print("Webhook listener indítása a 5000-es porton...")
    app.run(host='0.0.0.0', port=5000, debug=False)