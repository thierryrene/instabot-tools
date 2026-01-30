from insights_engine import InsightsEngine
import time

def test_insights():
    print("🧪 Testando InsightsEngine...")
    engine = InsightsEngine()
    
    # 1. Test Live Stats
    print("   ➡️ Buscando Live Stats...")
    stats = engine.get_live_stats()
    print(f"      Resultado: {stats}")
    assert "ad_trend_last_hour" in stats
    assert "estimated_savings" in stats
    print("   ✅ Live Stats OK")

    # 2. Test Categories
    print("   ➡️ Buscando Categorias...")
    cats = engine.get_content_categories()
    print(f"      Resultado: {cats}")
    assert "Promo/Venda" in cats
    print("   ✅ Categorias OK")
    
    # 3. Test Keywords
    print("   ➡️ Buscando Keywords...")
    kw = engine.get_top_keywords()
    print(f"      Resultado: {kw}")
    print("   ✅ Keywords OK")

if __name__ == "__main__":
    try:
        test_insights()
        print("\n🎉 Engine funcionando corretamente!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
