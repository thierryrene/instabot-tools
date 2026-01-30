# Changelog

All notable changes to this project will be documented in this file.

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
