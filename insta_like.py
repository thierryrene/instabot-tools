import os
import time
import random
from datetime import timedelta

# --- CONFIGURAÇÃO (COORDENADAS FIXAS) ---
TARGET_PROFILE = "stealthelook"
TARGET_LIKES = 15

# Seus dados atualizados
SEARCH_TAB_X = 778
SEARCH_TAB_Y = 2285
SEARCH_BAR_X = 602
SEARCH_BAR_Y = 186
FIRST_RESULT_X = 673
FIRST_RESULT_Y = 460
FIRST_POST_X = 235
FIRST_POST_Y = 1696
CENTER_X = 590
CENTER_Y = 1140

# Ajuste de Scroll (Para não passar do ponto)
SCROLL_START_Y = 1800
SCROLL_END_Y = 750  # Distância média para um post
# ----------------------------------------

def tap(x, y):
    # Clica com um pequeno erro de 5 pixels para não ser um robô perfeito
    rx = x + random.randint(-5, 5)
    ry = y + random.randint(-5, 5)
    os.system(f"adb shell input tap {rx} {ry}")

def double_tap(x, y):
    # Simula o clique duplo de curtida
    tap(x, y)
    time.sleep(0.12)
    tap(x, y)

def swipe_next():
    # Rola para o próximo post de forma controlada
    # Usando duração maior para evitar inércia (momentum)
    duration = random.randint(800, 1100)
    os.system(f"adb shell input swipe 540 {SCROLL_START_Y} 540 {SCROLL_END_Y} {duration}")

def start_instagram():
    print("🚀 Abrindo Instagram...")
    os.system("adb shell am force-stop com.instagram.android")
    os.system("adb shell monkey -p com.instagram.android -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1")
    time.sleep(7)

def main():
    start_time = time.time()
    start_instagram()
    
    # 1. Navegação Direta
    print(f"🔍 Buscando perfil: {TARGET_PROFILE}")
    tap(SEARCH_TAB_X, SEARCH_TAB_Y)
    time.sleep(2.5)
    
    tap(SEARCH_BAR_X, SEARCH_BAR_Y)
    time.sleep(1.5)
    
    print(f"✍️  Digitando nome do perfil...")
    os.system(f"adb shell input text '{TARGET_PROFILE}'")
    time.sleep(4.0) # Espera a lista de sugestões aparecer abaixo
    
    print("👆 Selecionando primeiro resultado da lista...")
    tap(FIRST_RESULT_X, FIRST_RESULT_Y)
    time.sleep(5)
    
    print("🖼️  Abrindo primeira foto...")
    tap(FIRST_POST_X, FIRST_POST_Y)
    time.sleep(3)
    
    # 2. Loop de Curtidas
    print(f"\n❤️  Iniciando sessão de {TARGET_LIKES} curtidas...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        for i in range(1, TARGET_LIKES + 1):
            # Pausa para "ler" o post
            wait = random.uniform(2.5, 4.5)
            print(f"   [{i}/{TARGET_LIKES}] Curtindo...                  ", end="\r")
            
            double_tap(CENTER_X, CENTER_Y)
            time.sleep(1)
            
            print(f"   [{i}/{TARGET_LIKES}] ✅ Curtido! Rolando... ({wait:.1f}s)")
            swipe_next()
            
            time.sleep(wait)

    except KeyboardInterrupt:
        print("\n\n🛑 Interrompido pelo usuário.")

    # 3. Relatório Final
    duration = time.time() - start_time
    print("\n" + "═"*40)
    print("📊 RELATÓRIO FINAL")
    print(f"⏱️ Tempo total: {str(timedelta(seconds=int(duration)))}")
    print(f"✅ Posts processados: {TARGET_LIKES}")
    print("═"*40)

if __name__ == "__main__":
    main()
