from database_manager import DatabaseManager
import os
import time

def test_database_logging():
    print("🧪 Iniciando teste de verificação do banco de dados...")
    
    # Remove DB antigo se existir para garantir teste limpo (opcional, aqui não vou remover pra simular persistência)
    # if os.path.exists("instabot.db"):
    #     os.remove("instabot.db")
        
    db = DatabaseManager()
    
    # 1. Start Session
    print("   ➡️  Iniciando sessão...")
    session_id = db.start_session("test_profile_vip")
    assert session_id is not None, "Falha ao criar ID de sessão"
    print(f"   ✅ Sessão iniciada com ID: {session_id}")
    
    # 2. Log Stories
    print("   ➡️  Logando stories...")
    db.log_story("user1", is_ad=False, action_taken="view")
    db.log_story("user2", is_ad=True, action_taken="view")
    db.log_story("test_profile_vip", is_ad=False, action_taken="like")
    print("   ✅ Stories logados.")
    
    # 3. End Session
    print("   ➡️  Finalizando sessão...")
    db.end_session(total_stories=3, total_ads=1, total_likes=1, unique_profiles=2, duration_seconds=10.5)
    print("   ✅ Sessão finalizada.")
    
    # 4. Verify Data
    print("   ➡️  Verificando dados salvos...")
    sessions = db.get_recent_sessions(1)
    if sessions:
        last_session = sessions[0]
        # id, start, end, target, stories, ads, likes, unique, duration
        print(f"      Dados recuperados: {last_session}")
        assert last_session[3] == "test_profile_vip", "Target profile incorreto"
        assert last_session[4] == 3, "Total stories incorreto"
        assert last_session[5] == 1, "Total ads incorreto"
        assert last_session[6] == 1, "Total likes incorreto"
        print("   ✅ Dados verificados com sucesso!")
    else:
        print("   ❌ Nenhuma sessão encontrada!")

if __name__ == "__main__":
    try:
        test_database_logging()
        print("\n🎉 Todos os testes passaram!")
    except AssertionError as e:
        print(f"\n❌ Falha no teste: {e}")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
