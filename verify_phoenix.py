import os
import sys
import httpx
import asyncio
from src.config.settings import settings

async def verify_phoenix():
    print("🔍 Diagnosticando Integración con Phoenix (Arize)...")
    
    # 1. Verificar Configuración
    enabled = settings.phoenix_enabled
    endpoint = settings.phoenix_collector_endpoint
    project = settings.phoenix_project_name
    
    print(f"\n📋 Configuración:")
    print(f"  - PHOENIX_ENABLED: {enabled}")
    print(f"  - PHOENIX_COLLECTOR_ENDPOINT: {endpoint}")
    print(f"  - PHOENIX_PROJECT_NAME: {project}")
    print(f"  - PHOENIX_PROTOCOL: {settings.phoenix_protocol}")

    if not enabled:
        print("\n⚠️ Phoenix está deshabilitado en settings.")
        print("  Habilítalo con PHOENIX_ENABLED=true en .env")
        return

    # 2. Verificar Conexión HTTP (UI/API)
    # Asumimos que la UI está en el puerto 6006 por defecto si no se especifica otro
    ui_url = "http://localhost:6006"
    if "localhost" not in endpoint and "127.0.0.1" not in endpoint:
         # Si el endpoint apunta a otro lado, intentar inferir UI url
         base = endpoint.split(":")[0] + ":" + endpoint.split(":")[1]
         ui_url = f"{base}:6006"
    
    print(f"\n📡 Verificando Accesibilidad UI/API ({ui_url})...")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(ui_url)
            if resp.status_code == 200:
                print("  ✅ UI/API de Phoenix accesible.")
            else:
                print(f"  ⚠️ UI respondió con código {resp.status_code}")
    except Exception as e:
        print(f"  ❌ No se pudo conectar a la UI de Phoenix: {str(e)}")
        print("     (Esto es normal si Phoenix corre en Docker y este script en el host sin puerto expuesto, o si no está corriendo)")

    # 3. Verificar Collector Endpoint
    print(f"\n🔌 Verificando Collector ({endpoint})...")
    # Es difícil testear gRPC con httpx, pero si es HTTP podemos intentar
    if settings.phoenix_protocol == "http/protobuf":
        try:
            # v1/traces es para HTTP
            trace_url = f"{endpoint}/v1/traces"
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Solo ping, esperaremos 405 Method Not Allowed o similar, pero conexión exitosa
                resp = await client.post(trace_url, json={})
                # Phoenix devuelve 400 o processed
                print(f"  ✅ Collector HTTP accesible (Status: {resp.status_code})")
        except Exception as e:
            print(f"  ❌ Falló conexión al Collector HTTP: {str(e)}")
    else:
        print("  ℹ️ Modo gRPC configurado. No se puede verificar conectividad simple sin librerías gRPC.")
        print("  Asegúrese de que el puerto 4317 esté expuesto y accesible.")

    print("\n✅ Diagnóstico finalizado.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(verify_phoenix())
