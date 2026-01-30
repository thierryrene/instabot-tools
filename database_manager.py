import sqlite3
import datetime
import os

DB_NAME = "instabot.db"

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._init_db()
        self.current_session_id = None

    def _init_db(self):
        """Inicializa o banco de dados e cria as tabelas se não existirem."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabela de Sessões
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                target_profile TEXT,
                total_stories INTEGER DEFAULT 0,
                total_ads INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                unique_profiles INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0
            )
        ''')

        # Tabela de Stories/Ações Individuais
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username TEXT,
                is_ad BOOLEAN DEFAULT 0,
                is_live BOOLEAN DEFAULT 0,
                action_taken TEXT, -- 'view', 'like', 'skip'
                full_text TEXT, -- Todo o texto lido da tela
                view_duration REAL DEFAULT 0, -- Tempo que o bot ficou no story
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')

        # Tabela de Entidades Extraídas (Hashtags, Menções, Marcas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS story_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER,
                type TEXT, -- 'hashtag', 'mention', 'brand'
                value TEXT,
                FOREIGN KEY(story_id) REFERENCES stories(id)
            )
        ''')
        
        # Índices para story_entities
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_story ON story_entities(story_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type_value ON story_entities(type, value)")
        
        # Migração Automática (Adiciona colunas se não existirem)
        # Verifica se colunas novas existem, se não, adiciona
        try:
            cursor.execute("SELECT full_text FROM stories LIMIT 1")
        except sqlite3.OperationalError:
            print("⚠️ Migrando banco de dados: Adicionando coluna 'full_text'...")
            cursor.execute("ALTER TABLE stories ADD COLUMN full_text TEXT")
            
        try:
            cursor.execute("SELECT view_duration FROM stories LIMIT 1")
        except sqlite3.OperationalError:
            print("⚠️ Migrando banco de dados: Adicionando coluna 'view_duration'...")
            cursor.execute("ALTER TABLE stories ADD COLUMN view_duration REAL DEFAULT 0")

        # Índices para Performance (Idempotente com IF NOT EXISTS)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_is_ad ON stories(is_ad)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_timestamp ON stories(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stories_username ON stories(username)")

        conn.commit()
        conn.close()

    def start_session(self, target_profile):
        """Inicia uma nova sessão de execução."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (target_profile, start_time)
            VALUES (?, ?)
        ''', (target_profile, datetime.datetime.now()))
        
        self.current_session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return self.current_session_id

    def log_story(self, username, is_ad=False, is_live=False, action_taken="view", full_text="", view_duration=0):
        """Registra um story individual processado e retorna o ID inserido."""
        if not self.current_session_id:
            return None
            
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO stories (session_id, username, is_ad, is_live, action_taken, timestamp, full_text, view_duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.current_session_id, username, is_ad, is_live, action_taken, datetime.datetime.now(), full_text, view_duration))
            
            story_id = cursor.lastrowid
            conn.commit()
            return story_id
        finally:
            conn.close()

    def save_entities(self, story_id, entities_dict):
        """Salva as entidades extraídas (hashtags, mentions, brands) para um story."""
        if not story_id:
            return

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            for entity_type, values in entities_dict.items():
                if entity_type not in ['hashtags', 'mentions', 'brands']:
                    continue
                
                # O dict da análise vem no plural, o DB guarda no singular para o tipo
                db_type = entity_type.rstrip('s') 
                
                for val in values:
                    cursor.execute('''
                        INSERT INTO story_entities (story_id, type, value)
                        VALUES (?, ?, ?)
                    ''', (story_id, db_type, val))
            conn.commit()
        except Exception as e:
            print(f"Erro ao salvar entidades: {e}")
        finally:
            conn.close()

    def end_session(self, total_stories, total_ads, total_likes, unique_profiles, duration_seconds=0):
        """Finaliza a sessão atual atualizando as estatísticas."""
        if not self.current_session_id:
            return

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions 
            SET end_time = ?, 
                total_stories = ?, 
                total_ads = ?, 
                total_likes = ?,
                unique_profiles = ?,
                duration_seconds = ?
            WHERE id = ?
        ''', (datetime.datetime.now(), total_stories, total_ads, total_likes, unique_profiles, duration_seconds, self.current_session_id))
        
        conn.commit()
        conn.close()
        self.current_session_id = None

    def get_recent_sessions(self, limit=5):
        """Retorna as sessões mais recentes para debug/visualização."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
