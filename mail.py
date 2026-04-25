import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration SMTP (récupérée du .env)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
# L'adresse email qui doit recevoir les alertes (peut être la même que SENDER_EMAIL ou plusieurs séparés par des virgules)
RAW_RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", SENDER_EMAIL)


def send_brvm_alert(df, excel_path=None):
    """
    Envoie un e-mail récapitulatif avec les signaux ACHAT/VENTE.
    Attache le fichier Excel des résultats s'il est fourni.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️  Email non configuré (SENDER_EMAIL ou SENDER_PASSWORD manquants dans .env)")
        return

    print("📧 Préparation de l'e-mail d'alerte...")

    # Liste des destinataires
    receivers_list = [r.strip() for r in RAW_RECEIVER_EMAIL.split(",") if r.strip()]

    # Filtrer uniquement les signaux d'ACHAT
    buys = df[df['Signal'].str.contains('ACHAT', na=False)].sort_values(by='Score', ascending=False)
    
    # Création du message
    msg = MIMEMultipart("alternative")
    msg['Subject'] = "📈 Bot BRVM - Opportunités du Jour"
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(receivers_list)

    # Construction du corps HTML
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Résumé des Opportunités BRVM</h2>
    """

    if not buys.empty:
        html_content += f'<h3 style="color: green;">🟢 {len(buys)} Action(s) à Achat/Fort Potentiel</h3>'
        html_content += '<table border="1" style="border-collapse: collapse; padding: 5px;">'
        html_content += '<tr><th>Ticker</th><th>Prix Actuel</th><th>Nbr Actions<br>(Volume)</th><th>Stop Loss (SL)</th><th>Take Profit (TP)</th></tr>'
        for _, row in buys.iterrows():
            html_content += f"<tr><td><b>{row['Valeur']}</b></td><td>{row['Prix']:,.0f} FCFA</td><td>{row.get('Nb_Actions', 'N/A')}</td><td>{row.get('Stop_Loss', 'N/A')}</td><td>{row.get('Take_Profit', 'N/A')}</td></tr>"
        html_content += '</table><br>'
    else:
        html_content += '<p>Aucune opportunité d\'achat détectée aujourd\'hui avec ce capital.</p>'

    html_content += f"""
        <p>L'analyse complète est disponible en pièce jointe.</p>
        <hr>
        <p style="font-size: 12px; color: #777;">🤖 Message généré automatiquement par BRVM Bot Ultimate.</p>
      </body>
    </html>
    """

    # Attacher le texte
    msg.attach(MIMEText(html_content, "html"))

    # Pièce jointe (le fichier Excel)
    if excel_path and Path(excel_path).exists():
        try:
            with open(excel_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {Path(excel_path).name}",
            )
            msg.attach(part)
        except Exception as e:
            print(f"⚠️  Erreur lors de l'attachement du fichier Excel : {e}")

    # Envoi via SMTP avec sendmail pour un ou plusieurs destinataires
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receivers_list, msg.as_string())
        server.quit()
        print("✅ E-mail envoyé avec succès !")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'e-mail : {e}")


if __name__ == "__main__":
    # Test simple du SMTP si on lance mail.py seul (nécessite un DataFrame vide au min)
    import pandas as pd
    test_df = pd.DataFrame(columns=['Valeur', 'Signal', 'Score', 'Close', 'Volume', 'Tendance_Globale'])
    send_brvm_alert(test_df)
