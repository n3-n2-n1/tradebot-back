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

class ExchangeAPI:
    def __init__(self, name, base_url, api_key, api_secret):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.prices = {}
        self.funding_rates = {}
        self.position_open = False  
    
    async def fetch_data(self):
        """Obtiene datos en tiempo real de la API de forma asíncrona."""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    if self.name == "OKX":
                        ticker_url = f"{self.base_url}/market/ticker?instId=BTC-USDT-SWAP"
                        funding_url = f"{self.base_url}/public/funding-rate?instId=BTC-USDT-SWAP"

                        async with session.get(ticker_url, timeout=5) as ticker_response:
                            ticker_data = await ticker_response.json()

                        async with session.get(funding_url, timeout=5) as funding_response:
                            funding_data = await funding_response.json()

                        if "data" in ticker_data and ticker_data["data"]:
                            self.prices["BTCUSDT"] = float(ticker_data["data"][0].get("last", 0))

                        if "data" in funding_data and funding_data["data"]:
                            funding_rate_raw = funding_data["data"][0].get("fundingRate", "0")
                            try:
                                self.funding_rates["BTCUSDT"] = round(float(funding_rate_raw), 6)
                            except ValueError:
                                print(f"Error: No se pudo convertir a float {funding_rate_raw}")
                                self.funding_rates["BTCUSDT"] = 0.0  

                    elif self.name == "Deribit":
                        ticker_url = f"{self.base_url}/public/get_index_price?index_name=btc_usd"
                        end_timestamp = int(datetime.utcnow().timestamp() * 1000)
                        start_timestamp = end_timestamp - (24 * 60 * 60 * 1000)
                        funding_url = (
                            f"{self.base_url}/public/get_funding_rate_history"
                            f"?instrument_name=BTC-PERPETUAL&start_timestamp={start_timestamp}&end_timestamp={end_timestamp}"
                        )

                        async with session.get(ticker_url, timeout=5) as ticker_response:
                            ticker_data = await ticker_response.json()

                        async with session.get(funding_url, timeout=5) as funding_response:
                            funding_data = await funding_response.json()

                        if "result" in ticker_data:
                            self.prices["BTCUSDT"] = float(ticker_data["result"].get("index_price", 0))
                        if "result" in funding_data and isinstance(funding_data["result"], list) and len(funding_data["result"]) > 0:
                            funding_rate_raw = funding_data["result"][0].get("interest_8h", "0")

                            try:
                                self.funding_rates["BTCUSDT"] = round(float(funding_rate_raw) * 100, 6)
                            except ValueError:
                                print(f"Error: No se pudo convertir a float {funding_rate_raw}, Tipo: {type(funding_rate_raw)}")
                                self.funding_rates["BTCUSDT"] = 0.0  

                    print(f"{self.name} - Price: {self.prices.get('BTCUSDT', 'N/A'):.2f}, Funding Rate: {self.funding_rates.get('BTCUSDT', 'N/A'):.6f}")
                
                except Exception as e:
                    print(f"Error en {self.name}: {e}")
                
                await asyncio.sleep(2)

class ArbitrageBot:
    def __init__(self, exchange_a, exchange_b, leverage=4):
        self.exchange_a = exchange_a
        self.exchange_b = exchange_b
        self.leverage = leverage
    
    async def check_opportunity(self):
        """Check if there is a profitable arbitrage opportunity and execute orders."""
        funding_a = self.exchange_a.funding_rates.get("BTCUSDT", None)
        funding_b = self.exchange_b.funding_rates.get("BTCUSDT", None)

        if funding_a is None or funding_b is None:
            print("Funding rates not available yet, waiting for data...")
            return
        
        print(f"Checking arbitrage opportunity: OKX funding {funding_a}, Deribit funding {funding_b}")

        if funding_b > funding_a:
            print(f"Opportunity found! Short on {self.exchange_b.name} ({funding_b}), Long on {self.exchange_a.name} ({funding_a})")
            await self.execute_trade("short", self.exchange_b, self.exchange_a)
        elif funding_a > funding_b:
            print(f"Opportunity found! Short on {self.exchange_a.name} ({funding_a}), Long on {self.exchange_b.name} ({funding_b})")
            await self.execute_trade("short", self.exchange_a, self.exchange_b)
        else:
            print("No arbitrage opportunity detected.")

    async def execute_trade(self, short_side, short_exch, long_exch):
        """Execute the arbitrage trade."""
        print(f"Executing trade: Short on {short_exch.name}, Long on {long_exch.name}")
    
    async def run(self):
        """Main loop to check opportunities and trade every 2 seconds."""
        while True:
            await self.check_opportunity()
            await asyncio.sleep(2)



# Iniciar bot de arbitraje
exchange_okx = ExchangeAPI("OKX", "https://www.okx.com/api/v5", OKX_API_KEY, OKX_SECRET_KEY)
exchange_deribit = ExchangeAPI("Deribit", "https://www.deribit.com/api/v2", DERIBIT_API_KEY, DERIBIT_SECRET_KEY)

# Iniciar bot de arbitraje correctamente
bot = ArbitrageBot(exchange_okx, exchange_deribit)
asyncio.create_task(bot.run())
