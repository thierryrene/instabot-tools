from database_manager import DatabaseManager
import sqlite3

# Força a inicialização para rodar a migração
db = DatabaseManager()
print("✅ DatabaseManager instanciado (migrações devem ter rodado).")

# Verifica colunas
conn = sqlite3.connect("instabot.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(stories)")
columns = [row[1] for row in cursor.fetchall()]
print(f"Colunas encontradas: {columns}")

if "full_text" in columns and "view_duration" in columns:
    print("✅ Schema verificado: colunas novas presente.")
else:
    print("❌ Schema falhou: colunas ausentes.")
    
conn.close()
