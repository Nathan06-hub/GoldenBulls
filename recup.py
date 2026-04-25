"""
recup.py - Mise à jour données BRVM (VERSION AUTOMATIQUE)
=========================================================
Utilise l'endpoint SikaFinance GetHistos (POST JSON) :
  https://www.sikafinance.com/api/general/GetHistos

✅ Aucun GUID nécessaire — fonctionne sans manipulation du navigateur.
✅ Récupère les données par tranches de 80 jours (limite API).
✅ Met à jour uniquement les nouvelles données depuis la dernière date connue.
✅ Écrit dans la base SQLite (brvm_data.db) ET dans les CSV (compatibilité).
"""

import requests
import pandas as pd
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from db import BRVMDatabase

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR     = "brvm_data"
API_URL      = "https://www.sikafinance.com/api/general/GetHistos"
CHUNK_DAYS   = 80    # Tranches de 80 jours (l'API refuse les périodes trop longues)

# En-têtes simulant un vrai navigateur (nécessaires pour éviter un blocage 403)
HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Accept":          "*/*",
    "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
    "Content-Type":    "application/json",
    "Origin":          "https://www.sikafinance.com",
    "Sec-Fetch-Dest":  "empty",
    "Sec-Fetch-Mode":  "cors",
    "Sec-Fetch-Site":  "same-origin",
    "Connection":      "keep-alive",
}

# Format exact des tickers requis par l'API SikaFinance (ticker.pays)
TICKERS_BRVM = [
    "BOAB.bj",  "BOABF.bf", "BOAM.ml",  "BOAN.ne",  "BOAS.sn",
    "BICC.ci",  "BNBC.ci",  "ECOC.ci",  "ETIT.tg",  "SGBC.ci",  "SIBC.ci",
    "ABJC.ci",  "CABC.ci",  "CFAC.ci",  "NEIC.ci",  "NTLC.ci",  "ONTBF.bf",
    "PALC.ci",  "PRSC.ci",  "SAFC.ci",  "SCRC.ci",  "SDCC.ci",
    "SIVC.ci",  "SLBC.ci",  "SMBC.ci",  "SNTS.sn",  "SOGC.ci",
    "SPHC.ci",  "STAC.ci",  "STBC.ci",  "TTLS.sn",
    "UNLC.ci",  "UNXC.ci",  "CBIBF.bf", "FTSC.ci",  "NSBC.ci",  "ORGT.tg",  "SHEC.ci",
]


def get_filename(ticker):
    """Retourne le nom de fichier CSV (ex: SGBC.ci -> SGBC.ci.csv)."""
    return f"{ticker}.csv"


# ============================================================================
# RÉCUPÉRATION VIA L'API SIKA FINANCE (SANS GUID)
# ============================================================================

def fetch_chunk(ticker, date_debut, date_fin):
    """
    Récupère les données historiques pour UNE tranche de dates.
    Retourne un DataFrame ou None.
    """
    headers = dict(HEADERS)
    headers["Referer"] = f"https://www.sikafinance.com/marches/historiques/{ticker}"

    payload = {
        "ticker":  ticker,
        "datedeb": date_debut,
        "datefin": date_fin,
        "xperiod": "0",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=25)
            break   # Succès → on sort de la boucle
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)   # Backoff : 1s, 2s, 4s
                continue
            return None   # Toutes les tentatives épuisées
        except Exception:
            return None

    try:
        if r.status_code != 200:
            return None

        data = r.json()

        # L'API retourne {"lst": [{...}], ...}
        rows = data.get("lst", None)
        if not rows or isinstance(rows, str):
            # "lst": "" signifie pas de données pour cette période
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Normaliser les colonnes → format interne [d, o, h, l, c, v]
        rename = {
            "Date":   "d",
            "Open":   "o",
            "High":   "h",
            "Low":    "l",
            "Close":  "c",
            "Volume": "v",
        }
        df = df.rename(columns=rename)

        # Garde uniquement les colonnes utiles
        keep = [c for c in ["d", "o", "h", "l", "c", "v"] if c in df.columns]
        df = df[keep].copy()

        # Les dates sont au format "DD/MM/YYYY" → convertir en datetime
        df["d"] = pd.to_datetime(df["d"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["d"])
        df = df.sort_values("d").reset_index(drop=True)
        return df

    except Exception:
        return None


def fetch_ticker_range(ticker, date_debut_str, date_fin_str):
    """
    Récupère toutes les données entre deux dates en découpant en tranches de CHUNK_DAYS.
    Retourne un DataFrame complet ou None.
    """
    start = datetime.strptime(date_debut_str, "%Y-%m-%d")
    end   = datetime.strptime(date_fin_str,   "%Y-%m-%d")

    all_chunks = []
    current = start

    while current <= end:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS), end)
        df_chunk = fetch_chunk(
            ticker,
            current.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d"),
        )
        if df_chunk is None:
            return None
        if not df_chunk.empty:
            all_chunks.append(df_chunk)

        current = chunk_end + timedelta(days=1)
        time.sleep(0.3)   # Petite pause entre les chunks

    if not all_chunks:
        return pd.DataFrame()

    return pd.concat(all_chunks, ignore_index=True).drop_duplicates(subset=["d"]).sort_values("d")


# ============================================================================
# MISE À JOUR D'UN TICKER (INCRÉMENTALE)
# ============================================================================

def update_ticker(ticker):
    """
    Met à jour les données d'un ticker en récupérant uniquement les nouvelles entrées.
    Retourne : "updated" | "up_to_date" | "error"
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, get_filename(ticker))

    df_old  = pd.DataFrame()
    date_debut = "2020-01-01"   # Historique par défaut si pas de fichier existant

    if os.path.exists(path):
        try:
            df_old = pd.read_csv(path)
            df_old["d"] = pd.to_datetime(df_old["d"], errors="coerce")
            df_old = df_old.dropna(subset=["d"])
            if not df_old.empty:
                last_date  = df_old["d"].max()
                date_debut = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"   ⚠️  {ticker} : erreur lecture CSV — {e}")

    date_fin = datetime.now().strftime("%Y-%m-%d")

    if date_debut > date_fin:
        print(f"   {ticker} : déjà à jour")
        return "up_to_date"

    df_new = fetch_ticker_range(ticker, date_debut, date_fin)

    if df_new is None:
        print(f"   ❌ {ticker} : erreur réseau")
        return "error"

    if df_new.empty:
        print(f"   {ticker} : déjà à jour (aucune nouvelle donnée)")
        return "up_to_date"

    # Fusion et sauvegarde CSV
    if not df_old.empty:
        df_combined = (
            pd.concat([df_old, df_new], ignore_index=True)
            .drop_duplicates(subset=["d"])
            .sort_values("d")
        )
    else:
        df_combined = df_new

    df_combined.to_csv(path, index=False)

    # Sauvegarde SQLite
    try:
        db = BRVMDatabase()
        db.insert_df(ticker, df_new)
    except Exception as e:
        print(f"   ⚠️  {ticker} SQLite : {e}")

    print(f"   📥 {ticker} : +{len(df_new)} lignes → {len(df_combined)} total")
    return "updated"


# ============================================================================
# TÉLÉCHARGEMENT COMPLET (PREMIER LANCEMENT / --full)
# ============================================================================

def download_all(depuis="2020-01-01"):
    """Téléchargement complet de tous les tickers depuis une date de départ."""
    print(f"\n{'='*60}")
    print(f"📦 Téléchargement complet depuis {depuis}")
    print(f"{'='*60}\n")

    os.makedirs(DATA_DIR, exist_ok=True)
    date_fin = datetime.now().strftime("%Y-%m-%d")
    stats = {"ok": 0, "err": 0}

    db = BRVMDatabase()
    for ticker in TICKERS_BRVM:
        df = fetch_ticker_range(ticker, depuis, date_fin)
        if df is not None and not df.empty:
            path = os.path.join(DATA_DIR, get_filename(ticker))
            df.to_csv(path, index=False)
            db.insert_df(ticker, df)
            print(f"   ✅ {ticker} : {len(df)} lignes")
            stats["ok"] += 1
        else:
            print(f"   ❌ {ticker} : échec ou aucune donnée")
            stats["err"] += 1
        time.sleep(0.5)

    print(f"\n✅ Terminé : {stats['ok']} succès, {stats['err']} erreurs")


# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

def main():
    print("=" * 60)
    print(f"🚀 Mise à jour BRVM — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("   Source : SikaFinance API (GetHistos) — sans GUID ✅")
    print("=" * 60)

    # Test de connectivité
    print("\n🔌 Test de connexion à SikaFinance...")
    try:
        r = requests.get("https://www.sikafinance.com", timeout=8)
        print(f"✅ Connexion OK (HTTP {r.status_code})\n")
    except Exception as e:
        print(f"❌ Impossible de joindre SikaFinance : {e}")
        sys.exit(1)

    stats = {"updated": 0, "up_to_date": 0, "error": 0}

    for ticker in TICKERS_BRVM:
        result = update_ticker(ticker)
        stats[result] = stats.get(result, 0) + 1
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(
        f"✅ Terminé | "
        f"Mis à jour: {stats['updated']} | "
        f"Déjà OK: {stats['up_to_date']} | "
        f"Erreurs: {stats['error']}"
    )
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        download_all(depuis="2020-01-01")
    else:
        main()
