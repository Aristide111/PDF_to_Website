from tqdm import tqdm
from pathlib import Path as p
import os
from dotenv import load_dotenv
from mistralai.client import Mistral
import time


# OCR et extraction des images


# chargement de la clef d'api depuis le .env
load_dotenv()
api_key = os.environ["KEY"]
client = Mistral(api_key=api_key)

# OCR des documents
# Transfert des documents sur les serveurs de Mistral
# ajout de délai pour éviter surcharge des serveurs et erreurs de refus d'accès
# Ajout d'un score de confidence et supression des documents une fois traités
# Stockage de la data dans le dictionnaire result

def OCR(folder):
    result = {}
    pdf_files = list(folder.glob("*.pdf")) 
    for file in tqdm(pdf_files, desc="Transfert des PDF complets à Mistral pour OCR..."):
        uploaded_pdf = client.files.upload(
            file={
                "fileName": file.name,
                "content": open(file, "rb"),
            },
            purpose="ocr")
        
        time.sleep(1)

        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url,
            },
            include_image_base64=True,
            confidence_scores_granularity="word",
            include_blocks=True,
        )

        result[file.stem] = {
            "ocr": ocr_response,  
            "update": "no",       
        }

        
        
        client.files.delete(file_id=uploaded_pdf.id)
        print(f"{file.name} : supprimé des serveurs Mistral")

    return result

