# Golden Bulls 🐂

**BRVM Bot Ultimate** est une application d'analyse technique complète pour la Bourse Régionale des Valeurs Mobilières (BRVM). Elle permet d'identifier les meilleures opportunités d'investissement grâce à des indicateurs avancés et une gestion de portefeuille optimisée.

## 🚀 Fonctionnalités Principales

### 📊 Analyse Technique Avancée
- **RSI (Relative Strength Index)** : Détection de surachat/survente
- **Moyennes Mobiles** : Croisements et tendances (SMA 20, 50, 200)
- **MACD** : Croisements de lignes et histogramme
- **Bollinger Bands** : Volatilité et zones de compression
- **ATR (Average True Range)** : Calcul du stop loss dynamique
- **Volume Analysis** : Confirmation des mouvements

### 💰 Gestion de Portefeuille
- **Allocation Optimale** : Répartition du capital selon le score de chaque action
- **Calcul Automatique** : Nombre d'actions, stop loss, take profit
- **Simulateur** : Testez différentes stratégies d'investissement

### 📈 Interface Web Interactive
- **Tableaux de bord** : Vue d'ensemble des opportunités
- **Graphiques interactifs** : Visualisation des prix et indicateurs
- **Filtres avancés** : Personnalisez votre analyse
- **Mise à jour en temps réel** : Données fraîches depuis SikaFinance

### 📧 Alertes Automatiques
- **Notifications par e-mail** : Recevez les meilleures opportunités directement dans votre boîte mail
- **Pièces jointes** : Export Excel complet de l'analyse
- **Configuration facile** : Variables d'environnement pour personnaliser l'envoi

## 🛠️ Installation

### Prérequis
- Python 3.8+
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. **Cloner le dépôt** (ou télécharger les fichiers)

2. **Créer un environnement virtuel** (recommandé)
```bash
python -m venv .venv
.venv\Scripts\Activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
Créez un fichier `.env` à la racine du projet avec le contenu suivant :
```env
# Configuration SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=votre_email@gmail.com
SENDER_PASSWORD=votre_mot_de_passe
RECEIVER_EMAIL=destinataire@example.com

# Configuration SikaFinance
SIKAFINANCE_URL=https://www.sikafinance.com/marches/marches-boursiers/marche-actions-brvm
```

## 🚀 Utilisation

### Lancer l'application
```bash
streamlit run app.py
```

### Mettre à jour les données
```bash
python recup.py --full
```

### Envoyer une alerte par e-mail
```bash
python mail.py
```

## 📂 Structure du Projet

```
Golden_bulls/
├── app.py                 # Interface web Streamlit
├── brvm_bot_ultimate.py   # Logique d'analyse
├── recup.py               # Script de récupération des données
├── mail.py                # Envoi d'e-mails
├── .env                   # Variables d'environnement (à créer)
├── requirements.txt       # Dépendances du projet
├── brvm_data/             # Données historiques (CSV)
└── output/                # Fichiers générés (Excel, etc.)
```

## 🎯 Stratégie d'Investissement

### Signaux d'Achat
- **ACHAT FORT** : Score ≥ 80 (forte conviction)
- **ACHAT** : Score ≥ 60 (bonne opportunité)
- **SURVEILLER** : Score ≥ 40 (à observer)

### Calcul du Score
Le score est calculé sur 100 points, combinant :
- Tendance globale (40 points)
- RSI (20 points)
- MACD (15 points)
- Bollinger Bands (15 points)
- Volume (10 points)

### Gestion des Risques
- **Stop Loss** : Calculé automatiquement avec ATR (2x ATR)
- **Take Profit** : Ratio risque/récompense de 1:2
- **Allocation** : Répartition du capital selon le score

## 🤝 Contribuer

1. Créer une branche : `git checkout -b feature/nouvelle-fonctionnalite`
2. Faire les modifications
3. Tester avec : `streamlit run app.py`
4. Soumettre une Pull Request

## 📄 Licence

Ce projet est développé dans le cadre du groupe **Les Bullionaires** 🏆

## 👥 Auteur & Groupe

- **Groupe** : Les Bullionaires
- **Auteur principal (Backend & Analyse)** : [Stéphane Nathanaël MARE](https://github.com/Nathan06-hub) — marenathanael06@gmail.com

## 📞 Support

Pour toute question ou problème : **marenathanael06@gmail.com**