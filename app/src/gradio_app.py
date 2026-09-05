import gradio as gr

from src.pipeline import (
    check_existing_site,
    run_ocr_and_build,
    run_ner_pipeline,
    deploy_site,
    save_website_archive,
    save_and_apply_metadata,
)
from src.metadata import DUBLIN_CORE_METADATA, DUBLIN_CORE_LABELS, WARNING

# Configuration de l'application Gradio

# CSS personnalisé pour l'application Gradio, basé sur la charte graphique de la FEP

CSS_CUSTOM = """
body, .gradio-container {
    background-color: #121212 !important;
    color: #FFFFFF !important;
}

#header-row {
    background-color: #0A0A0A;
    padding: 15px;
    align-items: center;
    border-bottom: 1px solid #333;
}

#logo-box {
    display: flex;
    justify-content: center;
    align-items: center;
}

#main-title {
    text-align: center;
}

.bordered-box {
    border: 1px solid #444;
    border-radius: 8px;
    padding: 15px;
    background-color: #1E1E1E;
}

#confirm-box {
    border: 2px solid #E53935;
    background-color: #2C1C1C;
    padding: 15px;
    border-radius: 8px;
    margin-top: 10px;
}

#warning-footer-row {
    background-color: #2C2517 !important;
    border: 1px solid #D97706 !important;
    border-radius: 8px;
    padding: 12px 18px;
    margin-top: 25px;
    margin-bottom: 15px;
    font-size: 0.83em;
    line-height: 1.4;
    color: #FDE68A !important;
}

#footer-row {
    background-color: #9CE3E1;
    color: #000000 !important;
    padding: 10px;
    text-align: center;
    font-weight: bold;
    border-radius: 6px;
    margin-top: 10px;
}
#footer-row a {
    color: #004D40 !important;
    text-decoration: underline;
}
"""

# Architecture générale de l'application

def build_interface():
    
    with gr.Blocks(title="PANEEL : ") as demo:

        with gr.Row(elem_id="header-row"):
            with gr.Column(scale=1, min_width=100, elem_id="logo-box"):
                gr.Markdown("👓🗞️")
            with gr.Column(scale=9):
                gr.Markdown("Visualization, Extraction, Linguistic analysis and Metadata for Archives documents", elem_id="main-title")

        # Zone principale en 2 colonnes
        with gr.Row():
            # Colonne de gauche : téléversement, aperçu et boutons de transformation/NLP
            with gr.Column(scale=6):
                with gr.Row():
                    with gr.Column(scale=3):
                        pdf_input = gr.File(
                            label="Explore",
                            file_count="multiple",
                            file_types=[".pdf"],
                            elem_classes=["bordered-box"],
                        )
                    with gr.Column(scale=7):
                        pdf_preview = gr.File(
                            label="Aperçu des fichiers",
                            interactive=False,
                            elem_classes=["bordered-box"],
                        )

                # Met à jour l'aperçu dès que de nouveaux fichiers sont ajoutés

                pdf_input.change(
                    fn=lambda files: files, inputs=[pdf_input], outputs=[pdf_preview]
                )

                with gr.Row():
                    btn_transform = gr.Button("Transformer", variant="primary", size="lg")
                    btn_ner = gr.Button("Extraire les noms de personnes, de lieux et d'évènements", variant="secondary", size="lg")

                # S'affiche uniquement si un site existe déjà (demande de confirmation)

                with gr.Column(visible=False, elem_id="confirm-box") as confirm_group:
                    confirm_label = gr.Markdown(
                        "Un site web existe déjà, voulez vous le supprimer ?"
                    )
                    with gr.Row():
                        btn_confirm_yes = gr.Button("Oui, réinitialiser", variant="stop")
                        btn_confirm_no = gr.Button("Non, conserver", variant="secondary")

            # Colonne de droite : guide d'utilisation (README) + exemple
            with gr.Column(scale=4, elem_classes=["bordered-box"]):
                with gr.Accordion("READ_ME", open=True):
                    gr.Markdown(
                        """
                        Bonjour et bienvenue sur PANEEL (Program for Archival Newspaper Exploration and Entity Localization).

                        Cet outil vous permet d'OCRiser vos documents, d'en extraire les images et de les transformer en site web.
                        Vous pourrez ensuite effectuer des recherches en texte intégral dans votre corpus mais aussi opérer des tâches de reconnaissance d'entités nommées.
                        Ce processus a été pensé selon une logique de pérennisation des documents archivistiques. 
                        Tous les éléments générés sont récupérables dans le dossier `Site`, au format Markdown pour le texte et PNG pour les images.
                        Vous pouvez aussi ajouter des métadonnées à vos documents.

                        ! ATTENTION ! Ce pipeline utilise une technologie externe (l'API Mistral OCR). 
                        Tout document transmis est hébergé temporairement sur les serveurs de Mistral AI.

                        Il est donc fortement déconseillé de transmettre des documents à caractère personnel ou des collections sous droits.

                        Pour toute question relative au traitement des données collectées, merci de vous référer aux conditions d'utilisation de Mistral AI : https://legal.mistral.ai/terms/get-started/#terms-of-service


                        **Comment l'utiliser ?**

                        1. Déposez vos fichiers PDF dans **Explore**.
                        2. Cliquez sur **Transformer** pour lancer l'OCR, extraire les images et générer le site web.
                        3. Cliquez sur **Extraire les noms de personnes, de lieux et d'événements** pour détecter les entités nommées et créer un graphique accessible sur la page "Visualisation".
                        4. Remplissez les **métadonnées Dublin Core** si vous le souhaitez pour les appliquer à l'en-tête de l'ensemble des pages de vos documents (elles n'apparaîtront pas sur la page elle-même).
                        5. Cliquez sur **DÉPLOYER** pour ouvrir automatiquement le site dans votre navigateur.

                        
                        """
                    )

                with gr.Group():
                    gr.Markdown("### EXEMPLE ")
                    gr.Markdown(
                        "En attente d'un exemple : ⌛"
                    )

        # Formulaire des métadonnées Dublin Core

        with gr.Row():
            with gr.Column(scale=12, elem_classes=["bordered-box"]):
                with gr.Accordion("Métadonnées Dublin Core", open=False):
                    gr.Markdown(
                        "Ces valeurs sont écrites dans l'en-tête de chaque page Markdown générée. "
                        "Modifiez-les et cliquez sur **Sauvegarder & appliquer** pour les appliquer à toutes les pages existantes."
                    )
                    meta_inputs = {}
                    keys = list(DUBLIN_CORE_METADATA.keys())
                    half = (len(keys) + 1) // 2
                    with gr.Row():
                        with gr.Column():
                            for key in keys[:half]:
                                meta_inputs[key] = gr.Textbox(
                                    label=DUBLIN_CORE_LABELS[key],
                                    value=DUBLIN_CORE_METADATA[key],
                                )
                        with gr.Column():
                            for key in keys[half:]:
                                meta_inputs[key] = gr.Textbox(
                                    label=DUBLIN_CORE_LABELS[key],
                                    value=DUBLIN_CORE_METADATA[key],
                                )
                    btn_save_meta = gr.Button("Sauvegarder & appliquer à chaque document", variant="primary")
                    meta_status = gr.Textbox(show_label=False, interactive=False)

        # Suivi de progression + déploiement + sauvegarde en archive

        with gr.Row():
            with gr.Column(scale=6):
                status_output = gr.Textbox(
                    label="PROGRESSION",
                    placeholder="Statut de l'exécution...",
                    interactive=False,
                )
            with gr.Column(scale=3):
                btn_deploy = gr.Button("DÉPLOYER")
                deploy_status = gr.Textbox(show_label=False, interactive=False)
            with gr.Column(scale=3):
                btn_save = gr.Button("Sauvegarder le site")
                site_zip_output = gr.File(label="Télécharger le site", interactive=False)

        # Zone d'export de la datavisualisation
        with gr.Row():
            with gr.Column(scale=12, elem_classes=["bordered-box"]):
                export_dataviz = gr.File(
                    label="Télécharger la datavisualisation",
                    interactive=False,
                )

        # Bannière d'avertissement réglementaire/IA
        with gr.Row(elem_id="warning-footer-row"):
            gr.Markdown(
                f"""
                **Avertissement / Warning**  
                **FR :** {WARNING['fr']}  
                **EN :** {WARNING['eng']}
                """
            )

        # Pied de page avec les crédits et liens GitHub
        with gr.Row(elem_id="footer-row"):
            gr.Markdown(
                "Projet réalisé par Aristide Curtelin en 2026, dans le cadre de son stage au sein du consortium pictorIA et du projet TORNE-H."
                "L'ensemble du projet est disponible sur Github : https://github.com/Aristide111 "
            )

        # --- Connexion des événements et des boutons (Wiring) ---

        # Déclenche la vérification de l'existence d'un site lors de la transformation
        btn_transform.click(
            fn=check_existing_site,
            inputs=[pdf_input],
            outputs=[status_output, confirm_group],
        )

        # Confirmation positive : réinitialise le site et lance l'OCR
        btn_confirm_yes.click(
            fn=lambda files: run_ocr_and_build(files, clean_site=True),
            inputs=[pdf_input],
            outputs=[status_output, confirm_group],
        )

        # Confirmation négative : conserve l'existant et lance l'OCR
        btn_confirm_no.click(
            fn=lambda files: run_ocr_and_build(files, clean_site=False),
            inputs=[pdf_input],
            outputs=[status_output, confirm_group],
        )

        # Exécute le pipeline de reconnaissance d'entités nommées (NER)
        btn_ner.click(
            fn=run_ner_pipeline,
            inputs=[],
            outputs=[status_output, export_dataviz],
        )

        # Enregistre et applique les métadonnées Dublin Core à tous les documents
        btn_save_meta.click(
            fn=save_and_apply_metadata,
            inputs=[meta_inputs[k] for k in keys],
            outputs=[meta_status],
        )

        # Déploie localement ou en ligne le site MkDocs
        btn_deploy.click(
            fn=deploy_site,
            inputs=[],
            outputs=[deploy_status],
        )

        # Crée une archive ZIP du site web complet
        btn_save.click(
            fn=save_website_archive,
            inputs=[],
            outputs=[site_zip_output, status_output],
        )

    return demo

# Lance l'application

def launch_app():
    demo = build_interface()
    demo.launch(css=CSS_CUSTOM)