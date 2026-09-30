import gradio as gr
from pathlib import Path

from src.pipeline import (
    check_existing_site,
    run_ocr_and_build,
    run_ner_pipeline,
    deploy_site,
    save_website_archive,
    save_and_apply_metadata,
)
from src.metadata import DUBLIN_CORE_METADATA, DUBLIN_CORE_LABELS, WARNING


# application Gradio

# CSS
CSS_CUSTOM = (
    Path(__file__).parent / "custom_gradio.css"
).read_text(
    encoding="utf-8"
)


# Application gradio

def build_interface():

    # création de l'application Gradio
    with gr.Blocks(
        title="Pdf_to_website : "
    ) as demo:

        # titre de l'application
        with gr.Row(
            elem_id="header-row"
        ):

            with gr.Column(scale=12):
                gr.Markdown(
                    "VELMA Visualization, Extraction, Linguistic analysis and Metadata for Archives documents",
                    elem_id="main-title"
                )

        # zone principale pour importer et traiter les documents
        with gr.Row():

            # zone d'import des PDF et boutons de traitement
            with gr.Column(scale=6):

                with gr.Row():

                    with gr.Column(scale=3):

                        # permet d'importer plusieurs fichiers PDF
                        pdf_input = gr.File(
                            label="Explore",
                            file_count="multiple",
                            file_types=[".pdf"],
                            elem_classes=["bordered-box"],
                        )

                    with gr.Column(scale=7):

                        # affiche les fichiers sélectionnés
                        pdf_preview = gr.File(
                            label="Aperçu des fichiers",
                            interactive=False,
                            elem_classes=["bordered-box"],
                        )

                # met à jour l'aperçu dès qu'un fichier est ajouté
                # reprend simplement les fichiers présents dans la zone d'import
                pdf_input.change(
                    fn=lambda files: files,
                    inputs=[pdf_input],
                    outputs=[pdf_preview]
                )

                # boutons pour lancer la transformation et l'extraction NER
                with gr.Row():

                    btn_transform = gr.Button(
                        "Transformer",
                        variant="primary",
                        size="lg"
                    )

                    btn_ner = gr.Button(
                        "Extraire les noms de personnes, de lieux et d'évènements",
                        variant="secondary",
                        size="lg"
                    )

                # zone cachée affichée uniquement si un site existe déjà
                # permet de choisir entre supprimer l'ancien site ou le conserver
                with gr.Column(
                    visible=False,
                    elem_id="confirm-box"
                ) as confirm_group:

                    confirm_label = gr.Markdown(
                        "Un site web existe déjà, voulez vous le supprimer ?"
                    )

                    with gr.Row():

                        # supprime l'ancien site avant de relancer le traitement
                        btn_confirm_yes = gr.Button(
                            "Oui, réinitialiser",
                            variant="stop"
                        )

                        # garde l'ancien site et continue le traitement
                        btn_confirm_no = gr.Button(
                            "Non, conserver",
                            variant="secondary"
                        )

            # zone contenant le guide d'utilisation
            with gr.Column(
                scale=4,
                elem_classes=["bordered-box"]
            ):

                with gr.Accordion():

                    # affiche les informations sur le fonctionnement de l'application
                    gr.Markdown(
                        """
                        Bonjour et bienvenue sur **VELMA** _Visualization, Extraction, Linguistic analysis and Metadata for Archives documents_.

                        Cet outil vous permet d'OCRiser vos documents, d'en extraire les images et de les transformer en site web.
                        Vous pourrez ensuite effectuer des recherches en texte intégral dans votre corpus mais aussi opérer des tâches de reconnaissance d'entités nommées.
                        Ce processus a été pensé selon une logique de pérennisation des documents archivistiques. 
                        Tous les éléments générés sont récupérables dans le dossier `Site`, au format **Markdown** pour le texte et **PNG** pour les images.
                        Vous pouvez aussi ajouter des métadonnées à vos documents.

                        **ATTENTION** Ce pipeline utilise une technologie externe (l'API Mistral OCR). 
                        Tout document transmis est hébergé temporairement sur les serveurs de Mistral AI.

                        Il est donc fortement déconseillé de transmettre des documents à caractère personnel ou des collections sous droits.

                        Pour toute question relative au traitement des données collectées, merci de vous référer aux conditions d'utilisation de Mistral AI : https://legal.mistral.ai/terms/get-started/#terms-of-service


                        **Comment l'utiliser ?**

                        1. Déposez vos fichiers PDF dans **Explore**.
                        2. Cliquez sur **Transformer** pour lancer l'OCR, extraire les images et générer le site web.
                        3. Cliquez sur **Extraire les noms de personnes, de lieux et d'événements** pour détecter les entités nommées et créer un graphique accessible sur la page "Visualisation".
                        4. Remplissez les **métadonnées** si vous le souhaitez pour les appliquer à l'en-tête de l'ensemble des pages de vos documents (elles n'apparaîtront pas sur la page elle-même).
                        5. Cliquez sur **DÉPLOYER** pour ouvrir automatiquement le site dans votre navigateur.

                        **En raison d'une modification des politiques tarifaires de l'API MISTRAL OCR cet été 2026, le fonctionnement de l'application est actuellement suspendu. Merci de vous référez à sa V2, basée sur l'API ALBERT du CNRS**
                        """
                    )

        # formulaire pour renseigner les métadonnées Dublin Core
        with gr.Row():

            with gr.Column(
                scale=12,
                elem_classes=["bordered-box"]
            ):

                with gr.Accordion(
                    "Métadonnées",
                    open=False
                ):

                    # explique où les métadonnées seront ajoutées
                    gr.Markdown(
                        "Ces valeurs sont écrites dans l'en-tête de chaque page Markdown générée. "
                        "Modifiez-les et cliquez sur **Sauvegarder & appliquer** pour les appliquer à toutes les pages existantes."
                    )

                    meta_inputs = {}

                    # récupération des différents champs Dublin Core
                    keys = list(
                        DUBLIN_CORE_METADATA.keys()
                    )

                    # séparation des champs en deux groupes
                    # permet de les afficher dans deux colonnes
                    half = (
                        len(keys) + 1
                    ) // 2

                    with gr.Row():

                        with gr.Column():

                            # création des champs de la première colonne
                            for key in keys[:half]:
                                meta_inputs[key] = gr.Textbox(
                                    label=DUBLIN_CORE_LABELS[key],
                                    value=DUBLIN_CORE_METADATA[key],
                                )

                        with gr.Column():

                            # création des champs de la deuxième colonne
                            for key in keys[half:]:
                                meta_inputs[key] = gr.Textbox(
                                    label=DUBLIN_CORE_LABELS[key],
                                    value=DUBLIN_CORE_METADATA[key],
                                )

                    # bouton pour sauvegarder et appliquer les métadonnées
                    btn_save_meta = gr.Button(
                        "Sauvegarder & appliquer à chaque document",
                        variant="primary"
                    )

                    # affiche le résultat de l'application des métadonnées
                    meta_status = gr.Textbox(
                        show_label=False,
                        interactive=False
                    )

        # zone de suivi du traitement et des exports
        with gr.Row():

            with gr.Column(scale=6):

                # affiche l'avancement des différents traitements
                status_output = gr.Textbox(
                    label="PROGRESSION",
                    placeholder="Statut de l'exécution...",
                    interactive=False,
                )

            with gr.Column(scale=3):

                # lance le déploiement du site
                btn_deploy = gr.Button(
                    "DÉPLOYER"
                )

                deploy_status = gr.Textbox(
                    show_label=False,
                    interactive=False
                )

            with gr.Column(scale=3):

                # crée une archive du site
                btn_save = gr.Button(
                    "Sauvegarder le site"
                )

                # fichier ZIP généré par la sauvegarde
                site_zip_output = gr.File(
                    label="Télécharger le site",
                    interactive=False
                )

        # zone d'export de la visualisation des entités
        with gr.Row():

            with gr.Column(
                scale=12,
                elem_classes=["bordered-box"]
            ):

                # permet de télécharger le résultat de la datavisualisation
                export_dataviz = gr.File(
                    label="Télécharger la datavisualisation",
                    interactive=False,
                )

        # affichage de l'avertissement sur le traitement des documents
        with gr.Row(
            elem_id="warning-footer-row"
        ):

            gr.Markdown(
                f"""
                **Avertissement / Warning**  
                **FR :** {WARNING['fr']}  
                **EN :** {WARNING['en']}
                """
            )

        # informations sur le projet et lien vers le dépôt Github
        with gr.Row(
            elem_id="footer-row"
        ):

            gr.Markdown(
                "Projet réalisé par Aristide Curtelin en 2026, dans le cadre de son stage au sein du consortium pictorIA et du projet TORNE-H."
                "L'ensemble du projet est disponible sur Github : https://github.com/Aristide111 "
            )

        # vérifie d'abord si un site existe avant de lancer le traitement
        # si un site est trouvé ==> affiche la demande de confirmation
        btn_transform.click(
            fn=check_existing_site,
            inputs=[pdf_input],
            outputs=[
                status_output,
                confirm_group
            ],
        )

        # supprime l'ancien site puis lance le traitement OCR
        btn_confirm_yes.click(
            fn=lambda files: run_ocr_and_build(
                files,
                clean_site=True
            ),
            inputs=[pdf_input],
            outputs=[
                status_output,
                confirm_group
            ],
        )

        # garde l'ancien site puis lance le traitement OCR
        btn_confirm_no.click(
            fn=lambda files: run_ocr_and_build(
                files,
                clean_site=False
            ),
            inputs=[pdf_input],
            outputs=[
                status_output,
                confirm_group
            ],
        )

        # lance l'extraction des entités nommées
        # génère ensuite la visualisation correspondante
        btn_ner.click(
            fn=run_ner_pipeline,
            inputs=[],
            outputs=[
                status_output,
                export_dataviz
            ],
        )

        # récupère les valeurs saisies dans les champs Dublin Core
        # applique les métadonnées à tous les documents existants
        btn_save_meta.click(
            fn=save_and_apply_metadata,
            inputs=[
                meta_inputs[k]
                for k in keys
            ],
            outputs=[meta_status],
        )

        # lance le déploiement du site généré
        btn_deploy.click(
            fn=deploy_site,
            inputs=[],
            outputs=[deploy_status],
        )

        # crée une archive ZIP du site
        # permet ensuite de récupérer le site complet
        btn_save.click(
            fn=save_website_archive,
            inputs=[],
            outputs=[
                site_zip_output,
                status_output
            ],
        )

    return demo


# lance l'application Gradio
# construit d'abord l'interface puis démarre le serveur
# applique le CSS personnalisé au lancement

def launch_app():

    # création de l'interface
    demo = build_interface()

    # lancement de Gradio avec le CSS personnalisé
    demo.launch(
        css=CSS_CUSTOM
    )
