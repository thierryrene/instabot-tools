"""
Text Analyzer - Deep OCR Analysis Module
Extrai entidades, detecta tópicos e analisa sinais de engajamento.
"""
import re
from collections import Counter

class TextAnalyzer:
    # Marcas populares para detecção
    KNOWN_BRANDS = [
        'nike', 'adidas', 'shein', 'zara', 'renner', 'c&a', 'riachuelo',
        'samsung', 'apple', 'iphone', 'xiaomi', 'motorola',
        'netflix', 'spotify', 'amazon', 'mercado livre', 'shopee', 'magalu',
        'nubank', 'itau', 'bradesco', 'santander', 'picpay', 'inter',
        'coca-cola', 'pepsi', 'nestle', 'ambev', 'heineken',
        'burger king', 'mcdonalds', 'subway', 'ifood', 'rappi', 'uber eats',
        'loreal', 'natura', 'boticario', 'avon', 'maybelline',
        'nba', 'flamengo', 'corinthians', 'palmeiras', 'sao paulo'
    ]
    
    # Tópicos e suas palavras-chave
    TOPICS = {
        "👗 Moda": ['moda', 'roupa', 'look', 'outfit', 'estilo', 'tendência', 'fashion', 'dress', 'jeans', 'camiseta', 'tênis', 'bolsa'],
        "💪 Fitness": ['treino', 'academia', 'exercício', 'dieta', 'gym', 'musculação', 'corrida', 'yoga', 'saúde', 'emagrecer', 'peso'],
        "🍔 Comida": ['comida', 'receita', 'restaurante', 'almoço', 'jantar', 'lanche', 'pizza', 'hamburguer', 'sushi', 'doce', 'bolo', 'café'],
        "📱 Tech": ['tech', 'tecnologia', 'celular', 'app', 'aplicativo', 'iphone', 'android', 'computador', 'notebook', 'gadget', 'software'],
        "💰 Finanças": ['dinheiro', 'investimento', 'renda', 'economia', 'pix', 'cartão', 'banco', 'financeiro', 'lucro', 'bitcoin', 'cripto'],
        "🎮 Games": ['jogo', 'game', 'gamer', 'playstation', 'xbox', 'pc', 'streamer', 'live', 'twitch', 'esports'],
        "🎬 Entretenimento": ['filme', 'série', 'netflix', 'novela', 'música', 'show', 'cinema', 'artista', 'celebridade', 'fofoca'],
        "✈️ Viagem": ['viagem', 'viajar', 'praia', 'hotel', 'avião', 'turismo', 'férias', 'destino', 'mala', 'passagem']
    }
    
    # Sinais de engajamento/CTA
    ENGAGEMENT_SIGNALS = [
        'arrasta pra cima', 'arrasta', 'link na bio', 'clica', 'clique', 'comenta', 'curte', 
        'compartilha', 'marca', 'segue', 'inscreva', 'participe', 'vote', 'responda',
        'saiba mais', 'confira', 'acesse', 'baixe', 'download', 'compre agora'
    ]

    def extract_entities(self, text):
        """Extrai hashtags, menções, marcas e URLs do texto."""
        if not text:
            return {"hashtags": [], "mentions": [], "brands": [], "urls": []}
        
        text_lower = text.lower()
        
        # Hashtags (#exemplo)
        hashtags = re.findall(r'#(\w+)', text_lower)
        
        # Menções (@usuario)
        mentions = re.findall(r'@(\w+)', text_lower)
        
        # Marcas conhecidas
        brands_found = [brand for brand in self.KNOWN_BRANDS if brand in text_lower]
        
        # URLs
        urls = re.findall(r'(https?://\S+|bit\.ly/\S+|t\.me/\S+)', text_lower)
        
        return {
            "hashtags": list(set(hashtags)),
            "mentions": list(set(mentions)),
            "brands": list(set(brands_found)),
            "urls": list(set(urls))
        }

    def detect_topics(self, text):
        """Classifica o texto em um ou mais tópicos."""
        if not text:
            return []
        
        text_lower = text.lower()
        detected = []
        
        for topic, keywords in self.TOPICS.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(topic)
        
        return detected if detected else ["📦 Geral"]

    def get_engagement_signals(self, text):
        """Detecta sinais de engajamento/CTAs no texto."""
        if not text:
            return []
        
        text_lower = text.lower()
        return [signal for signal in self.ENGAGEMENT_SIGNALS if signal in text_lower]

    def analyze(self, text):
        """Análise completa do texto."""
        return {
            "entities": self.extract_entities(text),
            "topics": self.detect_topics(text),
            "engagement_signals": self.get_engagement_signals(text)
        }


# Teste rápido
if __name__ == "__main__":
    analyzer = TextAnalyzer()
    sample = "Olha esse look da @sheinbrasil! 😍 #moda #fashion Arrasta pra cima pro link! https://bit.ly/shein123"
    result = analyzer.analyze(sample)
    print("Entidades:", result["entities"])
    print("Tópicos:", result["topics"])
    print("Engajamento:", result["engagement_signals"])
