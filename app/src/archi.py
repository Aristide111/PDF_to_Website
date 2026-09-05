import shutil
from pathlib import Path as p
import yaml
from tqdm import tqdm

# Création générale de l'architecture au fil du pipeline 
# (définition de chemins généraux,  vérification de l'existence de site précédent, 
# création des nouveaux sites, adaptation des chemins de navigation au cours des différents traitements).


# Dossier d'entrée des documents 
Input = p.cwd() / "PDF"

# Architecture du site de sortie

path_site = p.cwd() / "Site"
path_docs = path_site / "docs"
path_img = path_docs / "img"
path_page = path_docs / "page"

# éléments conservés à chaque nouveau site
path_assets = path_docs / "assets"
path_stylesheet = path_docs / "stylesheet"

# Configuration MkDocs + page de sommaire
path_index = path_docs / "index.md"
path_config = path_site / "mkdocs.yml"

# vérification de l'existence d'un site web préexistant pour suppression avec accord de l'opérateur
def verify_site_folder():
    if path_site.exists():
        answer = (
            input(f"'{path_site.name}' existe déjà. Le supprimer ? (oui/non) : ")
            .strip()
            .lower()
        )

        if answer in ("oui", "o", "yes", "y"):
            shutil.rmtree(path_site)
            print(f"'{path_site.name}' supprimé.")
        else:
            print(f"'{path_site.name}' conservé (les fichiers existants pourront être écrasés).")

# Création des dossiers du site à partir du nom des pdfs du dossier PDF et conservation des configurations graphiques
def architecture(folder):
    path_assets.mkdir(parents=True, exist_ok=True)
    path_stylesheet.mkdir(parents=True, exist_ok=True)
    pdf_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]
    total_files = len(pdf_files)

    for pdf in tqdm(
        pdf_files,
        desc="Création de l'arborescence du site...",
        total=total_files,
    ):
        (path_page / pdf.stem).mkdir(parents=True, exist_ok=True)
        (path_img / pdf.stem).mkdir(parents=True, exist_ok=True)

# Construction du site MkDocs avec les résultats de l'OCR et de l'extraction d'image.
# écriture des fichiers de configuration MkDocs et index avec les bons éléments graphiques.
# Ajout également des fonctionnalité de navigation : Une entrée de navigation + une ligne d'index par PDF traité
# Ajout du CSS et des assets (logo)
def build_mkdocs_site(result_OCR):
    
    nav = [
        {"Accueil": "index.md"},
        {"Visualisation": "visualisation.md"},
    ]
    index_lines = ["# Sommaire\n"]

    for pdf_stem in sorted(result_OCR.keys()):
        nb_pages = len(result_OCR[pdf_stem]["ocr"].pages)

        pages_nav = [
            {
                f"Page {page_index + 1}": f"page/{pdf_stem}/{pdf_stem}_page_{page_index}.md"
            }
            for page_index in range(nb_pages)
        ]
        nav.append({pdf_stem: pages_nav})

        first_page = f"page/{pdf_stem}/{pdf_stem}_page_0.md"
        index_lines.append(f"- [{pdf_stem}]({first_page})")

    config = {
        "site_name": "Site",
        "docs_dir": "docs",
        "theme": {
            "name": "material",
            "features": ["navigation.footer"],
        },
        "nav": nav,
    }

   
    logo_file = path_assets / "logo.jpg"
    if logo_file.exists():
        config["theme"]["logo"] = "assets/logo.jpg"

    css_file = path_stylesheet / "custom.css"
    if css_file.exists():
        config["extra_css"] = ["stylesheet/custom.css"]

    with path_config.open("wt", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

    with path_index.open("wt", encoding="utf-8") as f:
        f.write("\n".join(index_lines) + "\n")