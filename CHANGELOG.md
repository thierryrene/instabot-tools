# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0] - 2026-01-30
### Added
- **TextAnalyzer**: Módulo avançado para extração de entidades (hashtags, menções, marcas, URLs).
- **Detecção de Tópicos**: Classificação automática de stories em categorias (Moda, Tech, Fitness, etc).
- **Nova Aba "Deep Analysis"**: Visualização de Hashtags/Menções Trending, Marcas Detectadas, e Gráfico de Tópicos.
- **Métodos de Trending**: `get_trending_hashtags()`, `get_trending_mentions()`, `get_brand_exposure()`, `get_topic_distribution()`.

## [1.3.0] - 2026-01-30
### Added
- **Visual OCR**: Suporte para extração de texto via processamento de imagem (adb screenshot + pytesseract).
- **Exportadores**: Novos botões para exportar dados para PDF (fpdf) e Excel (pandas/openpyxl).
- **Análise de Sentimento**: Classificação automática de agressividade/positividade do conteúdo (🟢/🔴/🟡).
- **Novos KPIs**: Preços, Links e Sentimento agora visíveis no Dashboard.

## [1.2.0] - 2026-01-30
### Added
- **Real-time Insights Dashboard**: New "Live Intelligence" tab in GUI.
- **Regex Detection**: Automatic detection of prices (R$, $) and links/CTAs in stories.
- **Enhanced Categorization**: Stories are now categorized into Sales, News, Content, and CTAs.
- **Improved Data Collection**: Capturing full screen text and exact view duration.

## [1.1.0] - 2026-01-30
### Added
- **Persistent Logging**: SQLite integration (`instabot.db`) to save all bot executions.
- **Database Manager**: New module `database_manager.py` for structured data storage.
- **Verification Tools**: `verify_logging.py` and `test_insights.py`.

## [1.0.0] - 2026-01-30
### Added
- **Initial Project Organization**: Moved files to `insta-bot-teste`.
- **Git Initialization**: First commit and `.gitignore` setup.
- **Core Bot Functionality**: Stories viewing, Ad detection, and VIP Like system.
