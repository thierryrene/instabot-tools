# 🤖 Instagram Stories Bot - Pro Edition

Um robô avançado de automação de Instagram Stories com foco em **Inteligência de Dados** e **Insights Real-time**.

## 🚀 Principais Funcionalidades

- **Visualização Automática**: Navega por stories de forma humanizada.
- **Like VIP**: Curte automaticamente todos os stories de um perfil alvo.
- **Detector de Anúncios**: Identifica e pula anúncios poupando seu tempo.
- **Dashboard em Tempo Real**: Visualize métricas de economia de tempo, densidade de anúncios e categorias de conteúdo enquanto o bot roda.
- **Análise via Regex**: Detecta preços, links e chamadas para ação (CTAs) automaticamente no texto dos stories.
- **Persistência em SQLite**: Log completo de todas as execuções para análise semanal.

## 📁 Estrutura do Projeto

```text
insta-bot-teste/
├── insta_bot_gui.py     # Interface Gráfica (Painel de Controle)
├── database_manager.py  # Gerenciador do Banco de Dados SQLite
├── insights_engine.py   # Motor de Análise de Texto e Métricas
├── instabot.db          # Banco de dados local (gerado automaticamente)
└── README.md            # Este guia
```

## 🛠️ Como Usar

1. **Requisitos**: Tenha o ADB configurado e um dispositivo/emulador Android conectado com o Instagram aberto.
2. **Executar**:
   ```bash
   python3 insta_bot_gui.py
   ```
3. **Configurar**: Ajuste as coordenadas de clique conforme a tela do seu dispositivo.
4. **Insights**: Acompanhe a aba **"Live Intelligence"** para dados analíticos em tempo real.

## 📊 Relatórios
Para gerar um relatório consolidado de todas as sessões passadas:
```bash
python3 insights_report.py
```

## 📈 Próximos Passos
- [ ] Implementação de OCR visual para textos em imagens complexas.
- [ ] Exportação de relatórios em PDF/Excel.
- [ ] Análise de sentimento baseada em IA.

---
**Versão atual**: 1.2.0
**Status**: Operacional ⚡
