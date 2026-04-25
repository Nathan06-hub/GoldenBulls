"""
db.py - Couche base de données SQLite pour BRVM Bot
====================================================
Remplace les 38 fichiers CSV par un seul fichier SQLite.

Structure de la table principale :
    CREATE TABLE ohlcv (
        ticker  TEXT    NOT NULL,
        date    DATE    NOT NULL,
        open    REAL,
        high    REAL,
        low     REAL,
        close   REAL    NOT NULL,
        volume  REAL,
        PRIMARY KEY (ticker, date)
    )

Usage :
    from db import BRVMDatabase
    db = BRVMDatabase()                         # Ouvre/crée brvm_data.db
    db.insert_df("SGBC.ci", df)                 # Insère un DataFrame OHLCV
    df = db.load_ticker("SGBC.ci")              # Charge un ticker
    df = db.load_all()                          # Charge tout (pour l'analyseur)
    tickers = db.list_tickers()                 # Liste des tickers disponibles
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "brvm_data.db"


class BRVMDatabase:
    """Interface SQLite pour les données OHLCV de la BRVM."""

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._init_db()

    # ========================================================================
    # INITIALISATION
    # ========================================================================

    def _init_db(self):
        """Crée la table si elle n'existe pas encore."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    ticker  TEXT NOT NULL,
                    date    DATE NOT NULL,
                    open    REAL,
                    high    REAL,
                    low     REAL,
                    close   REAL NOT NULL,
                    volume  REAL DEFAULT 0,
                    PRIMARY KEY (ticker, date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker_date
                ON ohlcv (ticker, date)
            """)
            conn.commit()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")   # Meilleures performances
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    # ========================================================================
    # ÉCRITURE
    # ========================================================================

    def insert_df(self, ticker: str, df: pd.DataFrame) -> int:
        """
        Insère ou met à jour les données d'un ticker dans la base.
        Le DataFrame doit avoir les colonnes : d (date), o, h, l, c, v
        Retourne le nombre de lignes insérées / mises à jour.
        """
        if df is None or df.empty:
            return 0

        # Normaliser les colonnes
        df = df.copy()
        df["d"] = pd.to_datetime(df["d"], errors="coerce")
        df = df.dropna(subset=["d"])

        rows = []
        for _, row in df.iterrows():
            rows.append((
                ticker,
                row["d"].strftime("%Y-%m-%d"),
                float(row.get("o", row.get("c", 0)) or 0),
                float(row.get("h", row.get("c", 0)) or 0),
                float(row.get("l", row.get("c", 0)) or 0),
                float(row.get("c", 0) or 0),
                float(row.get("v", 0) or 0),
            ))

        with self._connect() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO ohlcv
                    (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()

        return len(rows)

    # ========================================================================
    # LECTURE
    # ========================================================================

    def load_ticker(self, ticker: str, from_date: str = None) -> pd.DataFrame:
        """
        Charge les données d'un ticker.
        Retourne un DataFrame avec les colonnes standard du projet :
            Date, Valeur, Open, High, Low, Close, Volume
        """
        query = "SELECT * FROM ohlcv WHERE ticker = ?"
        params = [ticker]

        if from_date:
            query += " AND date >= ?"
            params.append(from_date)

        query += " ORDER BY date ASC"

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            return df

        df = df.rename(columns={
            "date":   "Date",
            "ticker": "Valeur",
            "open":   "Open",
            "high":   "High",
            "low":    "Low",
            "close":  "Close",
            "volume": "Volume",
        })
        df["Date"] = pd.to_datetime(df["Date"])
        return df

    def load_all(self, from_date: str = None) -> pd.DataFrame:
        """
        Charge toutes les données de tous les tickers.
        Retourne un DataFrame avec les colonnes standard du projet :
            Date, Valeur, Open, High, Low, Close, Volume
        Compatible avec le format attendu par AnalyseurBRVM.
        """
        query = "SELECT * FROM ohlcv"
        params = []

        if from_date:
            query += " WHERE date >= ?"
            params.append(from_date)

        query += " ORDER BY ticker, date ASC"

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params if params else None)

        if df.empty:
            return df

        df = df.rename(columns={
            "date":   "Date",
            "ticker": "Valeur",
            "open":   "Open",
            "high":   "High",
            "low":    "Low",
            "close":  "Close",
            "volume": "Volume",
        })
        df["Date"] = pd.to_datetime(df["Date"])

        # Extraire le nom court du ticker (ex: "SGBC.ci" → "SGBC")
        df["Valeur"] = df["Valeur"].str.split(".").str[0].str.upper()

        return df

    # ========================================================================
    # INFORMATIONS
    # ========================================================================

    def list_tickers(self) -> list:
        """Retourne la liste des tickers présents dans la base."""
        with self._connect() as conn:
            cur = conn.execute("SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker")
            return [row[0] for row in cur.fetchall()]

    def get_last_date(self, ticker: str):
        """Retourne la dernière date connue pour un ticker (ou None)."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT MAX(date) FROM ohlcv WHERE ticker = ?", (ticker,)
            )
            result = cur.fetchone()[0]
        return result   # Format "YYYY-MM-DD" ou None

    def stats(self) -> dict:
        """Retourne des statistiques globales sur la base."""
        with self._connect() as conn:
            n_tickers = conn.execute(
                "SELECT COUNT(DISTINCT ticker) FROM ohlcv"
            ).fetchone()[0]
            n_rows = conn.execute(
                "SELECT COUNT(*) FROM ohlcv"
            ).fetchone()[0]
            min_date = conn.execute(
                "SELECT MIN(date) FROM ohlcv"
            ).fetchone()[0]
            max_date = conn.execute(
                "SELECT MAX(date) FROM ohlcv"
            ).fetchone()[0]

        size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

        return {
            "tickers":  n_tickers,
            "rows":     n_rows,
            "min_date": min_date,
            "max_date": max_date,
            "size_mb":  round(size_mb, 2),
        }

    # ========================================================================
    # MIGRATION DEPUIS LES CSV EXISTANTS
    # ========================================================================

    def migrate_from_csv(self, csv_dir: str = "brvm_data") -> dict:
        """
        Importe tous les fichiers CSV du dossier brvm_data/ dans la base SQLite.
        Compatible avec l'ancien format des CSV (colonnes d, o, h, l, c, v).
        """
        csv_dir = Path(csv_dir)
        stats = {"ok": 0, "skip": 0, "err": 0}

        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            print(f"⚠️  Aucun fichier CSV trouvé dans {csv_dir}")
            return stats

        print(f"📦 Migration de {len(csv_files)} fichiers CSV → SQLite...")

        for csv_file in sorted(csv_files):
            ticker = csv_file.stem   # ex: "SGBC.ci"
            try:
                df = pd.read_csv(csv_file)
                if "c" not in df.columns:
                    print(f"   ⚠️  {ticker} : format CSV invalide, ignoré")
                    stats["skip"] += 1
                    continue

                n = self.insert_df(ticker, df)
                print(f"   ✅ {ticker} : {n} lignes importées")
                stats["ok"] += 1

            except Exception as e:
                print(f"   ❌ {ticker} : {e}")
                stats["err"] += 1

        s = self.stats()
        print(f"\n✅ Migration terminée !")
        print(f"   📊 {s['tickers']} tickers | {s['rows']:,} lignes | {s['size_mb']} MB")
        return stats


# ============================================================================
# SCRIPT STANDALONE : python db.py --migrate
# ============================================================================

if __name__ == "__main__":
    import sys

    db = BRVMDatabase()

    if len(sys.argv) > 1 and sys.argv[1] == "--migrate":
        db.migrate_from_csv()

    elif len(sys.argv) > 1 and sys.argv[1] == "--stats":
        s = db.stats()
        print(f"📊 Base : {s['tickers']} tickers | {s['rows']:,} lignes")
        print(f"   Période : {s['min_date']} → {s['max_date']}")
        print(f"   Taille  : {s['size_mb']} MB")

    else:
        print("Usage:")
        print("  python db.py --migrate   # Importer les CSV existants")
        print("  python db.py --stats     # Afficher les statistiques")
