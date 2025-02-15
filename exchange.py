import time
import aiohttp
import json
import os
import asyncio
from datetime import datetime, timedelta


# Load API keys
OKX_API_KEY = os.getenv("OKX_API_KEY", "f90aea6f-def9-41b8-b822-24c988cf675b")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "EE8F8D258BB153E91F3EC7E775BD036E")
DERIBIT_API_KEY = os.getenv("DERIBIT_CLIENT_ID", "WBmw1gcI")
DERIBIT_SECRET_KEY = os.getenv("DERIBIT_SECRET_KEY", "LaPPE-wBrlqtyTeo5ExX0SOUoq1la401mr5YvMb20QY")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "TU_BYBIT_API_KEY")
BYBIT_SECRET_KEY = os.getenv("BYBIT_SECRET_KEY", "TU_BYBIT_SECRET_KEY")
class ExchangeAPI:
    def __init__(self, name, base_url):
        self.name = name
        self.base_url = base_url
        self.price = None
        self.funding_rate = None
        
    def generate_signature(self, params, secret_key):
            """Genera la firma HMAC-SHA256 para la autenticación en Bybit/OKX."""
            sorted_params = sorted(params.items())
            query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
            return hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

    async def execute_order(self, side, quantity):
        """Ejecuta una orden en el exchange."""
        order_url = f"{self.base_url}/v5/order/create"
        timestamp = str(int(time.time() * 1000))  # Timestamp en milisegundos

        order_data = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "side": side,  # "Buy" para Long, "Sell" para Short
            "orderType": "Market",
            "qty": quantity,
            "timestamp": timestamp,
        }

        if self.name == "Bybit":
            api_key = BYBIT_API_KEY
            secret_key = BYBIT_SECRET_KEY
            order_data["api_key"] = api_key
            order_data["sign"] = self.generate_signature(order_data, secret_key)

        elif self.name == "OKX":
            api_key = OKX_API_KEY
            secret_key = OKX_SECRET_KEY
            order_data["apiKey"] = api_key
            order_data["sign"] = self.generate_signature(order_data, secret_key)

        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(order_url, headers=headers, json=order_data) as resp:
                response_data = await resp.json()
                return response_data
    
    async def fetch_data(self):
            """Obtiene datos de precio y funding rate del exchange."""
            async with aiohttp.ClientSession() as session:
                try:
                    if self.name == "OKX":
                        ticker_url = f"{self.base_url}/market/ticker?instId=BTC-USDT-SWAP"
                        funding_url = f"{self.base_url}/public/funding-rate?instId=BTC-USDT-SWAP"
                    else:  # Bybit (reemplazamos Deribit)
                        ticker_url = f"{self.base_url}/v5/market/tickers?category=linear&symbol=BTCUSDT"
                        funding_url = f"{self.base_url}/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=1"


                    async with session.get(ticker_url) as resp_ticker, session.get(funding_url) as resp_funding:
                        ticker_data = await resp_ticker.json()
                        funding_data = await resp_funding.json()

                    # Procesar respuestas
                    if self.name == "OKX":
                        self.price = float(ticker_data["data"][0]["last"]) if "data" in ticker_data else None
                        self.funding_rate = float(funding_data["data"][0]["fundingRate"]) if "data" in funding_data else None
                    else:  # Bybit
                        if "result" in ticker_data and "list" in ticker_data["result"]:
                            self.price = float(ticker_data["result"]["list"][0]["lastPrice"])
                        else:
                            self.price = None

                        if "result" in funding_data and "list" in funding_data["result"]:
                            self.funding_rate = float(funding_data["result"]["list"][0]["fundingRate"])
                        else:
                            self.funding_rate = None

                except Exception as e:
                    print(f"❌ [ERROR] en {self.name}: {e}")
                    self.price, self.funding_rate = None, None
                    try:
                        if self.name == "OKX":
                            ticker_url = f"{self.base_url}/market/ticker?instId=BTC-USDT-SWAP"
                            funding_url = f"{self.base_url}/public/funding-rate?instId=BTC-USDT-SWAP"
                        else:  # Deribit
                            ticker_url = f"{self.base_url}/v5/market/tickers?category=linear&symbol=BTCUSDT"
                            funding_url = f"{self.base_url}/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=1"


                        async with session.get(ticker_url) as resp_ticker, session.get(funding_url) as resp_funding:
                            ticker_data = await resp_ticker.json()
                            funding_data = await resp_funding.json()

                        # Procesar respuestas
                        if self.name == "OKX":
                            self.price = float(ticker_data["data"][0]["last"]) if "data" in ticker_data else None
                            self.funding_rate = float(funding_data["data"][0]["fundingRate"]) if "data" in funding_data else None
                        else:  # Deribit
                            self.price = float(ticker_data["result"]["index_price"]) if "result" in ticker_data else None
                            if "result" in funding_data and isinstance(funding_data["result"], list) and len(funding_data["result"]) > 0:
                                self.funding_rate = float(funding_data["result"][0].get("funding_8h", 0) or 0)
                            else:
                                self.funding_rate = 0

                    except Exception as e:
                        print(f"❌ [ERROR] en {self.name}: {e}")
                        self.price, self.funding_rate = None, None
class ArbitrageBot:
    def __init__(self, exchange_a, exchange_b):
        self.exchange_a = exchange_a
        self.exchange_b = exchange_b

    async def check_opportunity(self):
        """Verifica oportunidades de arbitraje y ejecuta operaciones si aplica."""
        if self.exchange_a.funding_rate is None or self.exchange_b.funding_rate is None:
            return  

        if self.exchange_b.funding_rate > self.exchange_a.funding_rate:
            print(f"📈 Oportunidad: Short en {self.exchange_b.name}, Long en {self.exchange_a.name}")
        elif self.exchange_a.funding_rate > self.exchange_b.funding_rate:
            print(f"📉 Oportunidad: Short en {self.exchange_a.name}, Long en {self.exchange_b.name}")

    async def run(self):
        """Loop principal que revisa oportunidades y opera cada 5 segundos."""
        while True:
            await self.check_opportunity()
            await asyncio.sleep(5)