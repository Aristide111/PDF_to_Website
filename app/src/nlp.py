import os
import re
import json
import time
import random
from pathlib import Path as p
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
from dotenv import load_dotenv
from mistralai.client import Mistral

from src.archi import path_site, path_docs, path_img, path_page
from src.ocr import api_key, client

# Reconnaissance d'entité nommée et création des datavisualisation

# Prompt pour MISTRAL et configuration des parametres de ce dernier


tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_entities",
            "description": "Extrait les entités nommées du texte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "word": {"type": "string"},
                                "type": {"type": "string", "enum": ["PERS", "ORG", "EVENT", "PLACE"]},
                                "document_name": {"type": "string"}
                            },
                            "required": ["word", "type", "document_name"]
                        }
                    }
                },
                "required": ["entities"]
            }
        }
    }
]


# Configuration du corpus et création initialisation de la liste de résultats.

corpus = list(path_page.rglob("*.md"))
results = []


# Evite l'erreur 429 en ajoutant un délai exponentiel (backoff)

def call_with_retry(func, max_retries=5):
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "429" not in str(e) and "rate_limited" not in str(e):
                raise  
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"Débit limité (rate limit), nouvelle tentative dans {wait:.1f}s (essai {attempt + 1}/{max_retries})")
            time.sleep(wait)

# Extraction d'entité nommée sur le corpus via le formulaire d'interrogation de l'API
# On applique cette opération sur tout le corpus de document markdown
# On vérifie qu'ils existent bien
# On utilise des délais et des retry pour éviter un bug de limitation de ressource de l'API

def extract_entities():
    
    path_pages = p("Site/docs/page")
    
    corpus = list(path_pages.rglob("*.md")) if path_pages.exists() else []

    if not corpus:
        print("Aucun fichier Markdown trouvé dans Site/docs/page.")
        return []

    results = []

    for texte in tqdm(corpus, desc="Extraction des entités nommées..."):
        
        try:
            with open(p(texte), "r", encoding="utf-8") as f:
                document_content = f.read()
        except FileNotFoundError:
            print(f"\n[Avertissement] Le fichier {texte} n'existe plus, passage au suivant.")
            continue
        except Exception as e:
            print(f"\n[Erreur] Impossible de lire {texte} : {e}")
            continue

        
        response = call_with_retry(lambda: client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "user",
                    "content": f"Document : {texte.name}\nContenu : {document_content}"
                }
            ],
            tools=tools,
            tool_choice="any"  
        ))

        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            extracted_data = json.loads(tool_call.function.arguments)
            results.append({
                "file": texte.name,
                "entities": extracted_data["entities"]
            })

        time.sleep(2)  

    print(results)
    return results


# Création des datavisualisations et de la page de synthèse de la NLP

# Dictionnaires de correspondance pour le graph et couleurs

TYPE_LABELS = {
    "PERS": "Personnes",
    "ORG": "Organisations",
    "EVENT": "Événements",
    "PLACE": "Lieux",
}
TYPE_COLORS = {
    "PERS": "#4C72B0",
    "ORG": "#DD8452",
    "EVENT": "#55A868",
    "PLACE": "#C44E52",
}

# Extraction du nom du pdf et de l'index de page correspondant
def _parse_location(filename):
    
    match = re.match(r"^(.*)_page_(\d+)\.md$", filename)
    if not match:
        return None, None
    return match.group(1), int(match.group(2))


# Génération de la datavisualisation en prenant les 30 entités pour éviter un graphique illisible
# Crée la page Markdown qui liste les occurences avec les liens
def graph(detection):
   
    rows = []
    for doc in detection:
        file_name = doc.get("file")
        for entity in doc.get("entities", []):
            rows.append({
                "word": entity.get("word"),
                "type": entity.get("type"),
                "file": file_name,
            })

    df_entities = pd.DataFrame(rows)
    if df_entities.empty:
        print("Aucune entité détectée.")
        return

    # Nettoyage des lignes comportant des valeurs nulles ou des chaînes vides
    df_entities = df_entities.dropna(subset=['word', 'type'])
    df_entities = df_entities[df_entities['word'].str.strip() != ""]

    if df_entities.empty:
        print("Aucune entité exploitable après nettoyage.")
        return

  
    counts = df_entities.groupby(['word', 'type']).size().reset_index(name='count')
    totals = df_entities.groupby('word').size().reset_index(name='total')
    dominant = counts.loc[counts.groupby('word')['count'].idxmax(), ['word', 'type']]
    merged = totals.merge(dominant, on='word').sort_values('total', ascending=False).head(30)

    colors = merged['type'].map(TYPE_COLORS).fillna("#888888")

    plt.figure(figsize=(15, 10))
    plt.bar(merged['word'], merged['total'], color=colors)
    plt.xticks(rotation=60, ha='right')
    plt.xlabel("Entité")
    plt.ylabel("Nombre d'occurrences")
    plt.title("Top 30 des entités les plus fréquentes dans votre corpus")

    legend_elements = [
        Patch(facecolor=TYPE_COLORS[t], label=TYPE_LABELS[t])
        for t in TYPE_LABELS if t in merged['type'].values
    ]
    plt.legend(handles=legend_elements, title="Type d'entité")
    plt.tight_layout()

    # Sauvegarde physique de l'image du graphique
    path_viz_img = path_img / "visualisation"
    path_viz_img.mkdir(parents=True, exist_ok=True)
    img_path = path_viz_img / "frequence_entites.png"
    plt.savefig(img_path, format="png")
    plt.close()
    print(f"Graphique enregistré sous '{img_path}'")

    # --- Génération de la page Markdown de visualisation ---
    lines = [
        "# Visualisation des entités nommées\n",
        "![Fréquence des entités](img/visualisation/frequence_entites.png)\n",
        "## Détail des occurrences\n",
        "| Entité | Type | Emplacement |",
        "|---|---|---|",
    ]

    df_sorted = df_entities.sort_values(['type', 'word'])
    for _, row in df_sorted.iterrows():
        pdf_stem, page_index = _parse_location(row['file'])
        if pdf_stem is not None:
            link = f"page/{pdf_stem}/{row['file']}"
            emplacement = f"[{pdf_stem} — page {page_index + 1}]({link})"
        else:
            emplacement = row['file']

        type_label = TYPE_LABELS.get(row['type'], row['type'])
        lines.append(f"| {row['word']} | {type_label} | {emplacement} |")

    path_viz_md = path_docs / "visualisation.md"
    with path_viz_md.open("wt", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Page de visualisation créée : '{path_viz_md}'")