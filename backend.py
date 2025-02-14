from fastapi import FastAPI, WebSocket
import asyncio
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from exchange import ExchangeAPI, ArbitrageBot

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

@app.on_event("startup")
async def startup_event():
    """Inicia la recolección de datos en segundo plano al arrancar el servidor"""
    asyncio.create_task(exchange_okx.fetch_data())
    asyncio.create_task(exchange_deribit.fetch_data())

@app.get("/start")
async def start_bot():
    """Inicia el bot de arbitraje."""
    asyncio.create_task(bot.run())
    return {"message": "Bot started"}

@app.on_event("startup")
async def startup_event():
    """Inicia la recolección de datos en segundo plano al arrancar el servidor"""
    if not hasattr(exchange_okx, "_fetch_started"):
        exchange_okx._fetch_started = True
        asyncio.create_task(exchange_okx.fetch_data())

    if not hasattr(exchange_deribit, "_fetch_started"):
        exchange_deribit._fetch_started = True
        asyncio.create_task(exchange_deribit.fetch_data())

@app.get("/start")
async def start_bot():
    """Inicia el bot de arbitraje."""
    asyncio.create_task(bot.run())
    return {"message": "Bot started"}

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

@app.get("/arbitrage-status")
def get_arbitrage_status():
    """Devuelve los datos en tiempo real de precios, funding rates y oportunidades de arbitraje."""
    funding_okx = exchange_okx.funding_rates.get("BTCUSDT", 0)
    funding_deribit = exchange_deribit.funding_rates.get("BTCUSDT", 0)

    opportunity = None
    if funding_deribit > funding_okx:
        opportunity = {"action": "Short on Deribit, Long on OKX"}
    elif funding_okx > funding_deribit:
        opportunity = {"action": "Short on OKX, Long on Deribit"}

    return {
        "OKX": {
            "price": exchange_okx.prices.get("BTCUSDT", "N/A"),
            "funding_rate": funding_okx
        },
        "Deribit": {
            "price": exchange_deribit.prices.get("BTCUSDT", "N/A"),
            "funding_rate": funding_deribit
        },
        "arbitrage_opportunity": opportunity
    }

@app.get("/logs")
def get_logs():
    """Devuelve los últimos logs de ejecución del bot."""
    return {"message": "Últimos logs de trading disponibles en la terminal."}

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
