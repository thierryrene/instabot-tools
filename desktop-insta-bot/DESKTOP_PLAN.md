# 🖥️ Desktop Instagram Bot (PyAutoGUI + OpenCV)

## 🎯 Objetivo
Portar a lógica do "Stories Bot" para rodar no Desktop (Ubuntu), controlando o navegador Chrome/Firefox visualmente, sem injeção de código (Selenium), simulando um usuário humano real.

## 🛠️ Stack Tecnológica

### 1. Controle de Mouse/Teclado
- **PyAutoGUI:** Biblioteca principal. Substitui o `adb shell input tap`.
  - `pyautogui.click(x, y)`
  - `pyautogui.write('texto')`
  - `pyautogui.scroll(-10)`

### 2. Visão Computacional (Substitui XML Parsing)
No Desktop, não temos o XML da tela. Usamos reconhecimento de imagem.
- **OpenCV + Confidence:** Para achar botões mesmo com pequenas variações.
- **Pillow (PIL):** Para tirar screenshots parciais.
- **PyAutoGUI Locator:** `pyautogui.locateOnScreen('images/heart_icon.png', confidence=0.8)`

### 3. Interface Gráfica
- **PyQt5:** Reaproveitamos a GUI moderna que já criamos, apenas trocando o "backend" (de ADBHelper para DesktopHelper).

## 🔄 Comparativo: Android ADB vs Desktop GUI

| Ação | Android (ADB) | Desktop (PyAutoGUI) |
|------|--------------|---------------------|
| **Clicar** | `adb shell input tap x y` | `pyautogui.click(x, y)` |
| **Digitar** | `adb shell input text ...` | `pyautogui.write(...)` |
| **Achar Elemento** | XML Dump (`resource-id`) | `locateOnScreen('botao.png')` |
| **Scroll** | `adb shell input swipe` | `pyautogui.scroll()` |
| **Verificação** | `dumpsys window` | `pyautogui.pixelMatchesColor()` |

## 📂 Estrutura Proposta

```
desktop-insta-bot/
├── assets/                  # Banco de imagens para reconhecimento
│   ├── story_ring.png       # Círculo do story não visto
│   ├── like_heart.png       # Coração vazio
│   ├── like_filled.png      # Coração cheio
│   ├── next_arrow.png       # Seta p/ direita
│   └── comment_box.png      # Campo de comentário
├── src/
│   ├── desktop_helper.py    # Wrapper do PyAutoGUI (Substitui adb_helper)
│   ├── vision.py            # Lógica de OpenCV
│   └── bot_logic.py         # Fluxo principal
├── main.py
└── requirements.txt
```

## 🧠 Lógica de Navegação no Desktop

1. **Abrir Browser:** O bot abre o Chrome e vai para `instagram.com`.
2. **Detectar Stories:** Procura visualmente por círculos coloridos na barra superior.
3. **Loop de Stories:**
   - Clica no centro da tela (pausa/play).
   - Procura o nome do usuário (OCR ou posição fixa).
   - Verifica se é VIP -> `locateOnScreen('heart.png')` -> Click.
   - Procura "Patrocinado" (OCR).
   - Clica na seta direita (Next).

## ⚠️ Desafios e Soluções

1. **Ocupação do Mouse:**
   - *Solução:* O bot terá uma tecla de "Kill Switch" (ex: mover mouse para o canto da tela para parar imediatamente).

2. **Resolução Variável:**
   - *Solução:* O bot deve redimensionar a janela do browser para um tamanho fixo (ex: 400x800 - modo mobile) ao iniciar.

3. **OCR no Desktop:**
   - *Solução:* Usar `pytesseract` para ler o nome do usuário na tela, similar ao que fazíamos com XML.

## 🚀 Próximos Passos

1. Criar script para capturar os "assets" (recortar pedaços da tela).
2. Criar `DesktopHelper` com as mesmas funções do `ADBHelper` (para facilitar migração).
3. Adaptar a GUI para chamar esse novo backend.
