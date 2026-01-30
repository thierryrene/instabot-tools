import os
import time
import random
import sys
import xml.etree.ElementTree as ET
import re
from datetime import timedelta

# --- CONFIGURAÇÃO ---
TARGET_PROFILE = "stealthelook"
TARGET_LIKES = 15

# [NAVEGAÇÃO]
CENTER_X = 540
CENTER_Y = 1000 # Um pouco mais pra cima pra garantir que pegue a foto
# --------------------

def run_adb_cmd(cmd):
    return os.popen(cmd).read().strip()

def random_sleep(min_time=1.5, max_time=3.5):
    time.sleep(random.uniform(min_time, max_time))

def get_coords_from_bounds(bounds_str):
    try:
        matches = re.findall(r'\d+', bounds_str)
        nums = [int(x) for x in matches]
        cx = (nums[0] + nums[2]) // 2
        cy = (nums[1] + nums[3]) // 2
        return cx, cy
    except: return None, None

def find_element(match_text=None, match_desc=None, match_id=None, min_y=0):
    try:
        os.system("adb shell uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1")
        xml_content = run_adb_cmd("adb shell cat /data/local/tmp/uidump.xml")
        if not xml_content: return None
        root = ET.fromstring(xml_content)
        for node in root.iter():
            text = node.attrib.get('text', '')
            desc = node.attrib.get('content-desc', '')
            res_id = node.attrib.get('resource-id', '')
            bounds = node.attrib.get('bounds', '')
            match = False
            if match_id and match_id in res_id: match = True
            if match_text and match_text.lower() in text.lower(): match = True
            if match_desc and match_desc.lower() in desc.lower(): match = True
            if match:
                cx, cy = get_coords_from_bounds(bounds)
                if cy > min_y: return cx, cy
        return None
    except: return None

def smart_nav_search():
    print("🚀 Navegando até o perfil...")
    
    # 1. Busca
    coords = find_element(match_desc="Pesquisar e explorar") or (778, 2285)
    os.system(f"adb shell input tap {coords[0]} {coords[1]}")
    time.sleep(2)
    
    # 2. Barra
    os.system("adb shell input tap 600 180")
    time.sleep(1)
    os.system(f"adb shell input text '{TARGET_PROFILE}'")
    time.sleep(1)
    os.system("adb shell input keyevent 66") # Enter
    time.sleep(3)
    
    # 3. Clica no user
    coords = find_element(match_id="row_search_user_", min_y=250) or find_element(match_text=TARGET_PROFILE, min_y=300)
    if coords: os.system(f"adb shell input tap {coords[0]} {coords[1]}")
    else: os.system("adb shell input tap 673 460")
    random_sleep(4, 5)

    # 4. CLICA NA PRIMEIRA FOTO (Modo Grade)
    print("🖼️  Abrindo a primeira foto da grade...")
    # Tenta achar a grade
    tab = find_element(match_desc="Grade de perfil")
    if tab:
        # Clica na primeira celula da grade (logo abaixo da aba)
        # O offset X=150 garante a 1ª coluna. Y+200 garante a linha de cima.
        os.system(f"adb shell input tap 150 {tab[1] + 200}")
    else:
        # Fallback cego
        os.system("adb shell input tap 150 1500")
    
    random_sleep(2, 3)

def check_heart_state():
    """Verifica se o botão de coração está ativo (vermelho)"""
    try:
        os.system("adb shell uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1")
        xml_content = run_adb_cmd("adb shell cat /data/local/tmp/uidump.xml")
        root = ET.fromstring(xml_content)
        
        for node in root.iter():
            desc = node.attrib.get('content-desc', '')
            res_id = node.attrib.get('resource-id', '')
            
            # Procura especificamente o botão de like da interface de post
            if 'row_feed_button_like' in res_id or 'Like' in desc or 'Curtir' in desc or 'Unlike' in desc:
                # No modo galeria, o botão like fica visível abaixo da foto
                if 'Unlike' in desc or 'Descurtir' in desc: return True
                if node.attrib.get('selected') == 'true': return True
                
        return False
    except: return False

def swipe_next_post():
    """Desliza da DIREITA para a ESQUERDA (Avança cronologicamente)"""
    # Movimento horizontal longo
    print("   👉 Indo para o próximo post (Swipe Lateral)...")
    os.system("adb shell input swipe 900 1000 100 1000 400")

def double_tap():
    print("   ❤️  Double Tap!")
    os.system(f"adb shell input tap {CENTER_X} {CENTER_Y}")
    time.sleep(0.1)
    os.system(f"adb shell input tap {CENTER_X} {CENTER_Y}")

def main():
    os.system("adb shell am force-stop com.instagram.android")
    os.system("adb shell monkey -p com.instagram.android -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1")
    time.sleep(5)
    
    smart_nav_search()
    
    new_likes = 0
    skipped = 0
    count = 0
    
    print(f"\n⚡ INICIANDO MODO CARROSSEL ({TARGET_LIKES} likes)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        while new_likes < TARGET_LIKES:
            count += 1
            print(f"[{count:02}] Analisando...", end="\r")
            
            is_liked = check_heart_state()
            
            if is_liked:
                print(f"[{count:02}] ⏭️  JÁ CURTIDO. Pulando.             ")
                skipped += 1
            else:
                print(f"[{count:02}] ✅ NOVO! Curtindo...                ")
                double_tap()
                new_likes += 1
                time.sleep(0.5)
            
            # Vai para o próximo (Lateral)
            swipe_next_post()
            random_sleep(1.5, 2.5)

    except KeyboardInterrupt:
        print("\nParada manual.")
    
    print("\n" + "═"*30)
    print(f"✅ Finalizado!")
    print(f"Novos Likes: {new_likes}")
    print(f"Pulados:     {skipped}")
    print("═"*30)

if __name__ == "__main__":
    main()
