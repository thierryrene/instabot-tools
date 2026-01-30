import sqlite3
import pandas as pd
from fpdf import FPDF
import datetime
import os

DB_NAME = "instabot.db"

class DataExporter:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def _get_conn(self):
        return sqlite3.connect(self.db_name)

    def export_to_excel(self, output_path="instabot_report.xlsx"):
        """Exporta o histórico de stories e sessões para Excel."""
        conn = self._get_conn()
        try:
            stories_df = pd.read_sql_query("SELECT * FROM stories", conn)
            sessions_df = pd.read_sql_query("SELECT * FROM sessions", conn)
            entities_df = pd.read_sql_query("SELECT * FROM story_entities", conn)
            prices_df = pd.read_sql_query("SELECT * FROM price_history", conn)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                stories_df.to_excel(writer, sheet_name='Stories', index=False)
                sessions_df.to_excel(writer, sheet_name='Sessões', index=False)
                entities_df.to_excel(writer, sheet_name='Entidades Extraídas', index=False)
                prices_df.to_excel(writer, sheet_name='Histórico de Preços', index=False)
            
            return True, output_path
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def export_to_pdf(self, output_path="instabot_summary.pdf"):
        """Gera um relatório PDF visual com resumo dos dados."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Coleta KPIs básicos
            cursor.execute("SELECT COUNT(*) FROM stories")
            total_stories = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM stories WHERE is_ad = 1")
            total_ads = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            pdf = FPDF()
            pdf.add_page()
            
            # Título
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="Relatório de Atividade - Instagram Bot", ln=True, align='C')
            pdf.ln(10)
            
            # Data do Relatório
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Gerado em: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True, align='R')
            pdf.ln(10)
            
            # KPIs
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Visão Geral:", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.cell(200, 8, txt=f"- Total de Stories Analisados: {total_stories}", ln=True)
            pdf.cell(200, 8, txt=f"- Total de Anúncios Identificados: {total_ads}", ln=True)
            pdf.cell(200, 8, txt=f"- Sessões Executadas: {total_sessions}", ln=True)
            
            if total_stories > 0:
                ad_percentage = (total_ads / total_stories) * 100
                pdf.cell(200, 8, txt=f"- Taxa de Anúncios: {ad_percentage:.1f}%", ln=True)
            
            pdf.ln(10)
            
            # Top Criadores
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Top 5 Criadores (Frequência):", ln=True)
            pdf.set_font("Arial", size=11)
            
            cursor.execute('''
                SELECT username, COUNT(*) as count 
                FROM stories 
                WHERE is_ad = 0 AND username != "Desconhecido" 
                GROUP BY username 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            for row in cursor.fetchall():
                pdf.cell(200, 8, txt=f"  @{row[0]}: {row[1]} stories", ln=True)

            # Top Hashtags
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Top 5 Hashtags:", ln=True)
            pdf.set_font("Arial", size=11)
            cursor.execute("SELECT value, COUNT(*) as c FROM story_entities WHERE type='hashtag' GROUP BY value ORDER BY c DESC LIMIT 5")
            for row in cursor.fetchall():
                pdf.cell(200, 8, txt=f"  #{row[0]}: {row[1]}x", ln=True)

            # Variações de Preço
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Últimas Variações de Preço:", ln=True)
            pdf.set_font("Arial", size=11)
            cursor.execute("SELECT username, price, currency, timestamp FROM price_history ORDER BY timestamp DESC LIMIT 5")
            for row in cursor.fetchall():
                pdf.cell(200, 8, txt=f"  @{row[0]}: {row[2]}{row[1]} em {row[3][:16]}", ln=True)

            pdf.output(output_path)
            return True, output_path
            
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

if __name__ == "__main__":
    exporter = DataExporter()
    success, msg = exporter.export_to_excel()
    print(f"Excel: {success} ({msg})")
    success, msg = exporter.export_to_pdf()
    print(f"PDF: {success} ({msg})")
