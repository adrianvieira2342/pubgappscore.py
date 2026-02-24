import os

print("====================================")
print("🚀 INICIANDO TESTE DE VARIÁVEIS")
print("====================================\n")

print("🔎 Listando todas variáveis de ambiente disponíveis:\n")

for key, value in os.environ.items():
    print(f"{key} = {value}")

print("\n====================================")
print("🔎 TESTE ESPECÍFICO DAS VARIÁVEIS")
print("====================================\n")

database_url = os.environ.get("DATABASE_URL")
pubg_api_key = os.environ.get("PUBG_API_KEY")

print("DATABASE_URL encontrada?:", database_url is not None)
print("PUBG_API_KEY encontrada?:", pubg_api_key is not None)

print("\nValor DATABASE_URL:")
print(database_url)

print("\nValor PUBG_API_KEY:")
print(pubg_api_key)

print("\n====================================")
print("✅ FIM DO TESTE")
print("====================================")
