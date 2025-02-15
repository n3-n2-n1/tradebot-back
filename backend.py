from fastapi import FastAPI, WebSocket
import asyncio
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from exchange import ExchangeAPI, ArbitrageBot
from pydantic import BaseModel

# Cargar claves API desde variables de entorno
OKX_API_KEY = os.getenv("OKX_API_KEY", "f90aea6f-def9-41b8-b822-24c988cf675b")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "EE8F8D258BB153E91F3EC7E775BD036E")
DERIBIT_API_KEY = os.getenv("DERIBIT_CLIENT_ID", "WBmw1gcI")
DERIBIT_SECRET_KEY = os.getenv("DERIBIT_SECRET_KEY", "LaPPE-wBrlqtyTeo5ExX0SOUoq1la401mr5YvMb20QY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes cambiar "*" por ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancias de las APIs
exchange_okx = ExchangeAPI("OKX", "https://www.okx.com/api/v5")
exchange_bybit = ExchangeAPI("Bybit", "https://api.bybit.com")  # Cambiado de Deribit a Bybit
bot = ArbitrageBot(exchange_okx, exchange_bybit)

@app.on_event("startup")
async def startup_event():
    """Inicia la recolección de datos y el bot de arbitraje."""
    asyncio.create_task(exchange_okx.fetch_data())
    asyncio.create_task(exchange_bybit.fetch_data())  # Cambiado de Deribit a Bybit
    asyncio.create_task(bot.run())
    
@app.get("/status")
async def get_status():
    def format_rate(rate):
        return f"{rate:.8f}" if isinstance(rate, (float, int)) else "N/A"

    return {
        "OKX": {
            "price": round(exchange_okx.price, 2) if exchange_okx.price else "N/A",
            "funding_rate": format_rate(exchange_okx.funding_rate),
        },
        "Bybit": {
            "price": round(exchange_bybit.price, 2) if exchange_bybit.price else "N/A",
            "funding_rate": format_rate(exchange_bybit.funding_rate),
        },
    }

@app.get("/arbitrage-status")
async def get_arbitrage_status():
    """Verifica si hay oportunidad de arbitraje."""
    funding_okx = exchange_okx.funding_rate
    funding_bybit = exchange_bybit.funding_rate  # Cambiado de Deribit a Bybit

    if funding_okx is None or funding_bybit is None:
        return {"error": "Datos no disponibles"}

    if funding_bybit > funding_okx:
        return {
            "short_exchange": "Bybit",  # Cambiado de Deribit a Bybit
            "long_exchange": "OKX",
            "action": "Short en Bybit, Long en OKX"
        }
    elif funding_okx > funding_bybit:
        return {
            "short_exchange": "OKX",
            "long_exchange": "Bybit",  # Cambiado de Deribit a Bybit
            "action": "Short en OKX, Long en Bybit"
        }
    else:
        return {"message": "No hay oportunidad de arbitraje"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para enviar datos en tiempo real."""
    await websocket.accept()
    while True:
        try:
            data = {
                "OKX": {
                    "price": exchange_okx.price or "N/A",
                    "funding_rate": exchange_okx.funding_rate or "N/A"
                },
                "Bybit": {  # Cambiado de Deribit a Bybit
                    "price": exchange_bybit.price or "N/A",
                    "funding_rate": exchange_bybit.funding_rate or "N/A"
                },
                "arbitrage_opportunity": await get_arbitrage_status()
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(5)
        except Exception as e:
            print(f"WebSocket error: {e}")
            break
        
class TradeRequest(BaseModel):
    side: str  # "Buy" o "Sell"
    quantity: float
    exchange: str  # "OKX" o "Bybit"

@app.post("/trade")
async def execute_trade(request: TradeRequest):
    """Ejecuta una orden en OKX o Bybit."""
    if request.exchange == "OKX":
        response = await exchange_okx.execute_order(request.side, request.quantity)
    elif request.exchange == "Bybit":
        response = await exchange_bybit.execute_order(request.side, request.quantity)
    else:
        return {"error": "Exchange no soportado"}

    return {"exchange": request.exchange, "response": response}