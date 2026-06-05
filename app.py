from docuseal import docuseal
import subprocess

docuseal.key = "xHPyWnY8iyRLuTG9XuRjYZWKA1tAqSAnnwKa27YzYcT"
docuseal.url = "https://servis.sevenet.sk/api/"

response = docuseal.get_submission_documents(40)
pdf_url = response['documents'][0]['url']
name = response['documents'][0]['name']

# PDF letöltése a tmp mappába
subprocess.run(['wget', pdf_url, '-O', f'tmp/{name}.pdf'])

print(f"PDF letöltve: tmp/{name}.pdf")