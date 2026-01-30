import sqlite3
import datetime
import re
from collections import Counter
from text_analyzer import TextAnalyzer

DB_NAME = "instabot.db"

class InsightsEngine:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.analyzer = TextAnalyzer()

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
            "estimated_savings": 0,
            "detected_prices_count": 0,
            "detected_links_count": 0,
            "avg_sentiment": "Neutro"
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

            # 2. Contadores de Insights (Regex) nas últimas 24h
            twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE timestamp > ? AND full_text IS NOT NULL AND full_text != ""
            ''', (twenty_four_hours_ago,))
            rows = cursor.fetchall()
            
            prices_found = 0
            links_found = 0
            # Regex patterns
            price_pattern = r'(R\$ ?\d+[\.,]\d+|US\$ ?\d+[\.,]\d+|\d+ ?€)'
            link_pattern = r'(link na bio|bit\.ly|t\.me|https?://|arrasta|clica aqui)'
            
            for (text,) in rows:
                if re.search(price_pattern, text, re.IGNORECASE): prices_found += 1
                if re.search(link_pattern, text, re.IGNORECASE): links_found += 1
                
            stats["detected_prices_count"] = prices_found
            stats["detected_links_count"] = links_found

            # 3. Análise de Sentimento das últimas 24h
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE timestamp > ? AND full_text IS NOT NULL AND full_text != ""
            ''', (twenty_four_hours_ago,))
            texts = [row[0] for row in cursor.fetchall()]
            if texts:
                sentiment_score = 0
                pos_words = ['bom', 'ótimo', 'excelente', 'legal', 'top', 'feliz', 'amando', 'perfeito', 'ganhei', 'promo', 'novo', 'sorteio']
                neg_words = ['ruim', 'chato', 'triste', 'perdi', 'odio', 'problema', 'erro', 'cansado', 'reclamar', 'pessimo', 'urgente']
                
                for text in texts:
                    t = text.lower()
                    score = sum(1 for w in pos_words if w in t) - sum(1 for w in neg_words if w in t)
                    sentiment_score += score
                
                if sentiment_score > 5: stats["avg_sentiment"] = "🟢 Positivo"
                elif sentiment_score < -5: stats["avg_sentiment"] = "🔴 Negativo"
                else: stats["avg_sentiment"] = "🟡 Neutro"

            # 4. Economia estimada
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
            "🛒 Vendas/Promo": 0,
            "🎬 Conteúdo": 0,
            "📰 Notícia": 0,
            "🔗 Call to Action": 0
        }
        
        promo_keywords = ['promo', 'oferta', 'desconto', 'cupom', 'venda', 'off', 'lançamento', 'shop', 'comprar', 'frete', 'grátis', 'R$', 'preço']
        news_keywords = ['notícia', 'urgente', 'agora', 'acaba de', 'informação', 'reportagem', 'fofoca', 'polêmica', 'revelou', 'veja']
        cta_keywords = ['link na bio', 'bit.ly', 'clica', 'arrasta', 'saiba mais', 'clique']
        
        try:
            # Pega os últimos 200 stories com texto para maior precisão
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE full_text IS NOT NULL AND full_text != "" 
                ORDER BY id DESC LIMIT 200
            ''')
            rows = cursor.fetchall()
            
            for (text,) in rows:
                text_lower = text.lower()
                if any(k in text_lower for k in promo_keywords):
                    categories["🛒 Vendas/Promo"] += 1
                elif any(k in text_lower for k in news_keywords):
                    categories["📰 Notícia"] += 1
                elif any(k in text_lower for k in cta_keywords):
                    categories["🔗 Call to Action"] += 1
                else:
                    categories["🎬 Conteúdo"] += 1 
                    
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

    def get_trending_hashtags(self, limit=10):
        """Retorna as hashtags mais frequentes na última hora."""
        conn = self._get_conn()
        cursor = conn.cursor()
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        all_hashtags = []
        
        try:
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE timestamp > ? AND full_text IS NOT NULL AND full_text != ""
            ''', (one_hour_ago,))
            for (text,) in cursor.fetchall():
                entities = self.analyzer.extract_entities(text)
                all_hashtags.extend(entities["hashtags"])
            return Counter(all_hashtags).most_common(limit)
        except:
            return []
        finally:
            conn.close()

    def get_trending_mentions(self, limit=10):
        """Retorna as menções mais frequentes na última hora."""
        conn = self._get_conn()
        cursor = conn.cursor()
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        all_mentions = []
        
        try:
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE timestamp > ? AND full_text IS NOT NULL AND full_text != ""
            ''', (one_hour_ago,))
            for (text,) in cursor.fetchall():
                entities = self.analyzer.extract_entities(text)
                all_mentions.extend(entities["mentions"])
            return Counter(all_mentions).most_common(limit)
        except:
            return []
        finally:
            conn.close()

    def get_brand_exposure(self, limit=10):
        """Retorna as marcas mais mencionadas."""
        conn = self._get_conn()
        cursor = conn.cursor()
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        all_brands = []
        
        try:
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE timestamp > ? AND full_text IS NOT NULL AND full_text != ""
            ''', (one_hour_ago,))
            for (text,) in cursor.fetchall():
                entities = self.analyzer.extract_entities(text)
                all_brands.extend(entities["brands"])
            return Counter(all_brands).most_common(limit)
        except:
            return []
        finally:
            conn.close()

    def get_topic_distribution(self):
        """Retorna a distribuição de tópicos nos últimos stories."""
        conn = self._get_conn()
        cursor = conn.cursor()
        topic_counts = Counter()
        
        try:
            cursor.execute('''
                SELECT full_text FROM stories 
                WHERE full_text IS NOT NULL AND full_text != "" 
                ORDER BY id DESC LIMIT 100
            ''')
            for (text,) in cursor.fetchall():
                topics = self.analyzer.detect_topics(text)
                topic_counts.update(topics)
            return dict(topic_counts)
        except:
            return {}
        finally:
            conn.close()
