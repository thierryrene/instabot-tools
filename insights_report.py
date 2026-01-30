import sqlite3
from collections import Counter
import datetime

DB_NAME = "instabot.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def generate_report():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\n📊 RELATÓRIO DE INSIGHTS DO INSTABOT 📊")
    print("="*40)
    
    # 1. Visão Geral
    cursor.execute("SELECT COUNT(*), SUM(total_stories), SUM(total_likes), SUM(duration_seconds) FROM sessions")
    sessions_count, total_stories, total_likes, total_duration = cursor.fetchone()
    
    # Tratamento para valores None (caso nenhuma sessão tenha terminado)
    total_stories = total_stories or 0
    total_likes = total_likes or 0
    total_duration = total_duration or 0

    print(f"\n🔹 Visão Geral:")
    print(f"   Sessões Totais: {sessions_count}")
    print(f"   Total de Stories Vistos: {total_stories}")
    print(f"   Total de Likes Dados: {total_likes}")
    print(f"   Tempo Total de Uso: {datetime.timedelta(seconds=int(total_duration))}")

    # 2. Top Criadores (Quem posta mais?)
    print(f"\n🔹 Top 5 Criadores (Mais Stories):")
    cursor.execute('''
        SELECT username, COUNT(*) as count 
        FROM stories 
        WHERE is_ad = 0 AND username != 'Desconhecido' AND username != 'TurboMode'
        GROUP BY username 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    for row in cursor.fetchall():
        print(f"   1. @{row[0]}: {row[1]} stories")

    # 3. Análise de Ads
    cursor.execute("SELECT COUNT(*) FROM stories WHERE is_ad = 1")
    ad_count = cursor.fetchone()[0] or 0
    total_stories_records = cursor.execute("SELECT COUNT(*) FROM stories").fetchone()[0] or 1 # Avoid div/0
    
    ad_ratio = (ad_count / total_stories_records) * 100
    print(f"\n🔹 Frequência de Anúncios:")
    print(f"   Total Detectado: {ad_count}")
    print(f"   Taxa de Ads: {ad_ratio:.1f}% dos stories")
    
    # 4. Palavras-Chave (Tentativa simples de extrair contexto do full_text)
    # Requer que a coluna full_text esteja populada
    try:
        cursor.execute("SELECT full_text FROM stories WHERE full_text IS NOT NULL AND full_text != ''")
        texts = cursor.fetchall()
        all_words = []
        ignore_words = ['o', 'a', 'de', 'e', 'do', 'da', 'em', 'um', 'uma', 'com', 'para', 'na', 'no', 'que', 'se', 'dos', 'das', 'por', 'mais', 'as', 'os']
        
        for (text,) in texts:
            # Limpeza básica
            words = text.lower().replace('||', ' ').split()
            valid_words = [w for w in words if len(w) > 3 and w not in ignore_words]
            all_words.extend(valid_words)
            
        if all_words:
            print(f"\n🔹 Nuvem de Palavras (Contexto dos Stories):")
            common = Counter(all_words).most_common(5)
            for word, count in common:
                print(f"   '{word}': {count}x")
    except Exception as e:
        print(f"   (Erro na análise de texto: {e})")

    conn.close()
    print("\n" + "="*40)

if __name__ == "__main__":
    generate_report()
