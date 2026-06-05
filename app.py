from docuseal import docuseal

docuseal.key = "xHPyWnY8iyRLuTG9XuRjYZWKA1tAqSAnnwKa27YzYcT"
docuseal.url = "https://servis.sevenet.sk/api/"

response = docuseal.get_submission_documents(40)
pdf_url = response['documents'][0]['url']
print(pdf_url)