"""
Price Tracker - Monitoramento de Variação de Preços
Registra e detecta mudanças em valores de produtos/links detectados via OCR/Regex.
"""
import sqlite3
import datetime

DB_NAME = "instabot.db"

class PriceTracker:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                price REAL,
                currency TEXT,
                username TEXT,
                timestamp DATETIME
            )
        ''')
        # Tabela auxiliar para o "último preço" conhecido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS latest_prices (
                item_id TEXT PRIMARY KEY,
                last_price REAL,
                currency TEXT,
                last_update DATETIME
            )
        ''')
        conn.commit()
        conn.close()

    def update_price(self, item_identifier, price_value, currency, username):
        """Registra um novo preço e retorna se houve variação."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # 1. Busca preço anterior
            cursor.execute("SELECT last_price FROM latest_prices WHERE item_id = ?", (item_identifier,))
            result = cursor.fetchone()
            
            variation = None
            if result:
                old_price = result[0]
                if price_value < old_price: variation = "📉 Queda"
                elif price_value > old_price: variation = "📈 Alta"
            
            # 2. Registra no histórico
            cursor.execute('''
                INSERT INTO price_history (item_id, price, currency, username, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_identifier, price_value, currency, username, datetime.datetime.now()))
            
            # 3. Atualiza último preço
            cursor.execute('''
                INSERT OR REPLACE INTO latest_prices (item_id, last_price, currency, last_update)
                VALUES (?, ?, ?, ?)
            ''', (item_identifier, price_value, currency, datetime.datetime.now()))
            
            conn.commit()
            return variation
        finally:
            conn.close()

    def get_price_insights(self, limit=5):
        """Retorna itens com variações recentes."""
        # Por enquanto simplificado para as últimas entradas
        conn = sqlite3.connect(self.db_name)
        # ... lógica de consulta ...
        conn.close()
        return []
