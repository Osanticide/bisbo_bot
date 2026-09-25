import sqlite3

def consertar_banco():
    print("--- 🔧 Iniciando Reparo no Banco de Dados ---")
    
    try:
        conn = sqlite3.connect("cindy_database.db")
        cursor = conn.cursor()
        
        # 1. Tenta adicionar a coluna 'banco' na tabela economia
        print("1. Tentando adicionar coluna 'banco'...")
        try:
            cursor.execute("ALTER TABLE economia ADD COLUMN banco INTEGER DEFAULT 0")
            print("   ✅ Sucesso! Coluna 'banco' criada.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️ A coluna 'banco' já existia. Ignorando.")
            else:
                print(f"   ❌ Erro estranho: {e}")

        # 2. Verifica se a tabela 'social_profiles' existe (só por garantia)
        print("2. Verificando tabela 'social_profiles'...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_profiles (
                user_id TEXT PRIMARY KEY,
                xp_atual INTEGER DEFAULT 0,
                nivel INTEGER DEFAULT 1,
                bio TEXT DEFAULT 'Um aventureiro misterioso...',
                titulo_equipado TEXT DEFAULT 'Nenhum',
                titulos_desbloqueados TEXT DEFAULT 'Nenhum',
                cor_tema INTEGER DEFAULT 3447003
            )
        ''')
        print("   ✅ Tabela social verificada/criada.")

        conn.commit()
        conn.close()
        print("\n✨ Tudo pronto! Pode iniciar a Cindy novamente.")
        
    except Exception as e:
        print(f"\n❌ Erro fatal ao conectar no banco: {e}")

if __name__ == "__main__":
    consertar_banco()