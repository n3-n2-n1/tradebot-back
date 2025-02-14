from fastapi import FastAPI, WebSocket
import asyncio
import json
from threading import Thread
from exchange import ExchangeAPI, ArbitrageBot  # Importar el código existente
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes cambiar "*" por ["http://localhost:3000"] si solo usas Next.js local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar claves API desde variables de entorno
OKX_API_KEY = os.getenv("OKX_API_KEY", "f90aea6f-def9-41b8-b822-24c988cf675b")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "EE8F8D258BB153E91F3EC7E775BD036E")
DERIBIT_API_KEY = os.getenv("DERIBIT_CLIENT_ID", "WBmw1gcI")
DERIBIT_SECRET_KEY = os.getenv("DERIBIT_SECRET_KEY", "LaPPE-wBrlqtyTeo5ExX0SOUoq1la401mr5YvMb20QY")

# Instancias de las APIs
exchange_okx = ExchangeAPI("OKX", "https://www.okx.com/api/v5", OKX_API_KEY, OKX_SECRET_KEY)
exchange_deribit = ExchangeAPI("Deribit", "https://www.deribit.com/api/v2", DERIBIT_API_KEY, DERIBIT_SECRET_KEY)

bot = ArbitrageBot(exchange_okx, exchange_deribit)

# Iniciar threads para obtener datos en segundo plano
okx_thread = Thread(target=exchange_okx.fetch_data, daemon=True)
deribit_thread = Thread(target=exchange_deribit.fetch_data, daemon=True)

okx_thread.start()
deribit_thread.start()

@app.get("/status")
def get_status():
    """Devuelve los últimos datos de precios y tasas de financiamiento."""
    return {
        "OKX": {
            "price": exchange_okx.prices.get("BTCUSDT", "N/A"),
            "funding_rate": exchange_okx.funding_rates.get("BTCUSDT", "N/A")
        },
        "Deribit": {
            "price": exchange_deribit.prices.get("BTCUSDT", "N/A"),
            "funding_rate": exchange_deribit.funding_rates.get("BTCUSDT", "N/A")
        }
    }

@app.get("/start")
def start_bot():
    """Inicia el bot de arbitraje."""
    bot_thread = Thread(target=bot.run, daemon=True)
    bot_thread.start()
    return {"message": "Bot started"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = {
                "OKX": {
                    "price": exchange_okx.prices.get("BTCUSDT", "N/A"),
                    "funding_rate": exchange_okx.funding_rates.get("BTCUSDT", "N/A")
                },
                "Deribit": {
                    "price": exchange_deribit.prices.get("BTCUSDT", "N/A"),
                    "funding_rate": exchange_deribit.funding_rates.get("BTCUSDT", "N/A")
                }
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(5)
        except Exception as e:
            print(f"WebSocket error: {e}")
            break