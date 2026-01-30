import os
import time
import random
import xml.etree.ElementTree as ET
import sys
import subprocess
from datetime import timedelta

# --- CONFIGURAÇÃO ---
STORY_X = 745
STORY_Y = 400
NEXT_X = 980
NEXT_Y = 1000

# Perfil VIP (O robô vai curtir tudo dessa pessoa)
TARGET_PROFILE = "stealthelook"

# Coordenada do Coração (Canto inferior direito - Ajuste se necessário)
HEART_X = 950
HEART_Y = 2150 

PACKAGE_NAME = "com.instagram.android"
HUMAN_AVG_VIEW_TIME = 5.0 # Segundos que um humano gastaria por story
# --------------------

def run_adb_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("⚠️ Comando ADB timeout")
        return ""
    except Exception as e:
        print(f"⚠️ Erro ao executar comando ADB: {e}")
        return ""

def tap(x, y, randomize=True):
    if randomize:
        x += random.randint(-5, 5)
        y += random.randint(-5, 5)
    os.system(f"adb shell input tap {x} {y}")

def swipe(x1, y1, x2, y2, duration=300):
    os.system(f"adb shell input swipe {x1} {y1} {x2} {y2} {duration}")

def like_current_story():
    """Tenta clicar no botão de coração com precisão cirúrgica"""
    print(f"      💖 Curtindo story VIP...", end="\r")
    try:
        # Tenta achar via XML primeiro
        os.system("adb shell uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1")
        xml_content = run_adb_cmd("adb shell cat /data/local/tmp/uidump.xml")
        
        if not xml_content:
            raise Exception("XML vazio")
            
        root = ET.fromstring(xml_content)
        found = False
        for node in root.iter():
            desc = node.attrib.get('content-desc', '')
            res_id = node.attrib.get('resource-id', '')
            if 'toolbar_like_button' in res_id or 'Curtir' in desc:
                bounds = node.attrib.get('bounds', '')
                import re
                matches = re.findall(r'\d+', bounds)
                if len(matches) == 4:
                    cx = (int(matches[0]) + int(matches[2])) // 2
                    cy = (int(matches[1]) + int(matches[3])) // 2
                    tap(cx, cy, randomize=True)
                    found = True
                    break
        if not found: 
            tap(HEART_X, HEART_Y, randomize=True)
    except ET.ParseError as e:
        print(f"\n⚠️ Erro ao parsear XML: {e}")
        tap(HEART_X, HEART_Y, randomize=True)
    except Exception as e:
        print(f"\n⚠️ Erro ao dar like: {e}")
        tap(HEART_X, HEART_Y, randomize=True)
    time.sleep(0.5)

def get_screen_details():
    try:
        os.system("adb shell uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1")
        xml_content = run_adb_cmd("adb shell cat /data/local/tmp/uidump.xml")
        
        if not xml_content or 'resource-id="com.instagram.android:id/tab_bar"' in xml_content or 'content-desc="Início"' in xml_content:
             return "feed", None, False

        root = ET.fromstring(xml_content)
        found_username = "Desconhecido"
        is_sponsored = False

        for node in root.iter():
            text = node.attrib.get('text', '')
            res_id = node.attrib.get('resource-id', '')
            
            if text in ["Patrocinado", "Sponsored", "Publicidade"]:
                is_sponsored = True

            if 'reel_viewer_title' in res_id or 'row_feed_photo_profile_name' in res_id:
                if text: found_username = text
                
        return "story", found_username, is_sponsored
    except ET.ParseError as e:
        print(f"\n⚠️ Erro ao parsear XML na detecção de tela: {e}")
        return "story", "Desconhecido", False
    except Exception as e:
        print(f"\n⚠️ Erro ao detectar detalhes da tela: {e}")
        return "story", "Desconhecido", False

def draw_bar(percentage, length=20, char='█'):
    fill = int(length * percentage / 100)
    bar = char * fill + '░' * (length - fill)
    return bar

def format_time(seconds):
    return str(timedelta(seconds=int(seconds)))

def wake_and_unlock():
    dump = run_adb_cmd("adb shell dumpsys window | grep mWakefulness")
    if "Awake" not in dump:
        os.system("adb shell input keyevent KEYCODE_WAKEUP")
        time.sleep(1)
        swipe(500, 2000, 500, 500)
    os.system("adb shell input keyevent 82")

def start_instagram_robust():
    print("🚀 Iniciando Stories Bot vMax...")
    wake_and_unlock()
    os.system(f"adb shell am force-stop {PACKAGE_NAME}")
    os.system(f"adb shell monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1")
    time.sleep(6)

def print_final_report(start_time, total_stories, profile_map, total_ads, liked_count):
    end_time = time.time()
    bot_duration = end_time - start_time
    
    # Métricas Calculadas
    human_estimated_time = total_stories * HUMAN_AVG_VIEW_TIME
    time_saved = human_estimated_time - bot_duration
    if time_saved < 0: time_saved = 0
    
    real_stories = total_stories - total_ads
    unique_profiles = len(profile_map)
    
    if total_stories > 0:
        ad_percentage = (total_ads / total_stories) * 100
        content_percentage = 100 - ad_percentage
        freq_ad = int(real_stories / total_ads) if total_ads > 0 else 0
        speed = total_stories / (bot_duration/60)
    else:
        ad_percentage = 0; content_percentage = 0; freq_ad = 0; speed = 0

    print("\n\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           📊 RELATÓRIO DE INTELIGÊNCIA & INSIGHTS        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║ ⏱️  Duração da Sessão:   {format_time(bot_duration)}")
    print(f"║ ⚡  Velocidade do Bot:   {speed:.1f} stories/min")
    print(f"║ 💎  Tempo Economizado:   {format_time(time_saved)} (vs Humano)")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║ 🎯 AÇÃO DO ROBÔ                                          ║")
    print(f"║    Stories Vistos:       {total_stories}")
    print(f"║    Likes em @{TARGET_PROFILE}: {liked_count}")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║ ⚖️  ECONOMIA DA ATENÇÃO (Ads vs Conteúdo)                 ║")
    print("║                                                          ║")
    print(f"║  Conteúdo ({real_stories}): {draw_bar(content_percentage, 15)} {content_percentage:.1f}%")
    print(f"║  Anúncios ({total_ads}): {draw_bar(ad_percentage, 15)} {ad_percentage:.1f}%")
    print("║                                                          ║")
    if freq_ad > 0:
        print(f"║  👉 O Instagram te mostra 1 anúncio a cada {freq_ad} stories.")
    else:
        print(f"║  👉 Sessão limpa! Nenhum anúncio detectado.")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║ 🏆  RANKING DE FLOODERS (Quem posta mais?)               ║")
    
    sorted_profiles = sorted(profile_map.items(), key=lambda x: x[1], reverse=True)[:5]
    if sorted_profiles:
        for i, (user, count) in enumerate(sorted_profiles, 1):
            bar = draw_bar((count / total_stories) * 100, 10, '■')
            print(f"║  {i}. @{user:<18} {count:>3} stories {bar}")
    else:
        print("║  (Sem dados suficientes)")
        
    print("╚══════════════════════════════════════════════════════════╝")

def main():
    start_instagram_robust()
    tap(STORY_X, STORY_Y, randomize=False)
    time.sleep(2)

    total_stories = 0
    total_ads = 0
    liked_count = 0
    profile_map = {} 
    last_user = None
    user_story_count = 0
    session_start = time.time()
    
    print(f"\n⚡ MONITOR ATIVO | Alvo de Like: @{TARGET_PROFILE}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        while True:
            screen_type, username, is_ad = get_screen_details()
            
            if screen_type == "feed":
                print(f"\n✅ Fim da fila de stories.")
                break
            
            total_stories += 1
            
            # Formatação visual
            display_name = username
            emoji = "✨"
            if is_ad:
                total_ads += 1
                display_name = f"{username} (Ad)"
                emoji = "💸"
            else:
                # Se não for anúncio, conta para o ranking de criadores
                if username != "Desconhecido":
                    profile_map[username] = profile_map.get(username, 0) + 1

            # Logica de exibição hierarquica
            if display_name != last_user:
                print(f"{emoji} @{display_name}")
                last_user = display_name
                user_story_count = 1
            else:
                user_story_count += 1
            
            # Logica de Like VIP
            action_tag = ""
            if username.lower() == TARGET_PROFILE.lower():
                like_current_story()
                liked_count += 1
                action_tag = " [💖 LIKE]"
            
            print(f"   🎞️  Story #{user_story_count}{action_tag}")

            # Rate limiting: pausa a cada 50 stories
            if total_stories % 50 == 0:
                pause_time = random.uniform(10, 30)
                print(f"\n⏸️  Pausa estratégica ({pause_time:.1f}s)...")
                time.sleep(pause_time)

            # Timing humanizado entre stories
            view_time = random.uniform(0.8, 2.5)
            time.sleep(view_time)
            tap(NEXT_X, NEXT_Y)
            time.sleep(0.5) 

    except KeyboardInterrupt:
        print("\n🛑 Parada pelo usuário.")
    except Exception as e:
        print(f"\n⚠️ Erro: {e}")
    finally:
        print_final_report(session_start, total_stories, profile_map, total_ads, liked_count)

if __name__ == "__main__":
    main()
