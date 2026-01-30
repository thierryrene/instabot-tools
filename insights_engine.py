import sqlite3
import datetime
from collections import Counter

DB_NAME = "instabot.db"

class InsightsEngine:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def _get_conn(self):
        return sqlite3.connect(self.db_name)

    def get_live_stats(self, session_id=None):
        """Retorna estatísticas em tempo real da sessão atual ou geral."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Filtro de tempo: Última hora
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        
        stats = {
            "ad_trend_last_hour": 0,
            "top_category": "Variado",
            "estimated_savings": 0
        }

        try:
            # 1. Trend de Ads na última hora
            cursor.execute('''
                SELECT COUNT(*), SUM(is_ad) 
                FROM stories 
                WHERE timestamp > ?
            ''', (one_hour_ago,))
            total, ads = cursor.fetchone()
            if total and total > 0:
                stats["ad_trend_last_hour"] = (ads / total) * 100

            # 2. Economia estimada (baseado em sessões recentes)
            # Assume 5s por story humano vs view_duration real
            cursor.execute('''
                SELECT SUM(5.0 - view_duration)
                FROM stories
                WHERE view_duration > 0
            ''')
            savings = cursor.fetchone()[0]
            if savings:
                stats["estimated_savings"] = savings

        except Exception as e:
            print(f"Erro no InsightsEngine: {e}")
        
        conn.close()
        return stats

    def get_content_categories(self):
        """Analisa o texto dos stories para categorizar o conteúdo."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        categories = {
            "Promo/Venda": 0,
            "Conteúdo": 0,
            "Notícia": 0,
            "Outros": 0
        }
        
        promo_keywords = ['promo', 'oferta', 'desconto', 'cupom', 'venda', 'off', 'lançamento', 'shop', 'comprar', 'frete', 'grátis']
        news_keywords = ['notícia', 'urgente', 'agora', 'acaba de', 'informação', 'reportagem', 'fofoca', 'polêmica']
        
        try:
            # Pega os últimos 100 stories com texto
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE full_text IS NOT NULL AND full_text != "" 
                ORDER BY id DESC LIMIT 100
            ''')
            rows = cursor.fetchall()
            
            for (text,) in rows:
                text_lower = text.lower()
                if any(k in text_lower for k in promo_keywords):
                    categories["Promo/Venda"] += 1
                elif any(k in text_lower for k in news_keywords):
                    categories["Notícia"] += 1
                else:
                    categories["Conteúdo"] += 1 # Assumimos conteúdo geral se não for venda explícita
                    
        except Exception:
            pass
            
        conn.close()
        return categories

    def get_top_keywords(self, limit=5):
        """Retorna as palavras mais frequentes."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        conn = self._get_conn()
        cursor = conn.cursor()
        all_words = []
        ignore = ['o', 'a', 'de', 'e', 'do', 'da', 'em', 'um', 'uma', 'com', 'para', 'na', 'no', 'que', 'se', 'dos', 'das', 'por', 'mais', 'as', 'os', 'story', 'time', 'post']
        
        try:
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE full_text IS NOT NULL AND full_text != "" 
                ORDER BY id DESC LIMIT 50
            ''')
            rows = cursor.fetchall()
            
            for (text,) in rows:
                words = text.lower().replace("||", " ").split()
                valid = [w for w in words if len(w) > 3 and w not in ignore]
                all_words.extend(valid)
                
            return Counter(all_words).most_common(limit)
            
        except Exception:
            return []
        finally:
            conn.close()
