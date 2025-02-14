import time
import requests
import websocket
import json
import os
from threading import Thread
from threading import Thread
from datetime import datetime, timedelta


    
class ExchangeAPI:
    def __init__(self, name, base_url, api_key, api_secret):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.prices = {}
        self.funding_rates = {}
        self.position_open = False  # Estado para evitar órdenes repetidas
    
    def fetch_data(self):
        """Fetch real-time data from the exchange using HTTP requests."""
        while True:
            try:
                if self.name == "OKX":
                    ticker_url = f"{self.base_url}/market/ticker?instId=BTC-USDT-SWAP"
                    funding_url = f"{self.base_url}/public/funding-rate?instId=BTC-USDT-SWAP"
                    
                    ticker_response = requests.get(ticker_url, timeout=5).json()
                    funding_response = requests.get(funding_url, timeout=5).json()
                    
                    if "data" in ticker_response and isinstance(ticker_response["data"], list) and len(ticker_response["data"]) > 0:
                        self.prices["BTCUSDT"] = float(ticker_response["data"][0].get("last", 0))
                    else:
                        print(f"Unexpected response from {self.name} ticker: {ticker_response}")

                    if "data" in funding_response and isinstance(funding_response["data"], list) and len(funding_response["data"]) > 0:
                        self.funding_rates["BTCUSDT"] = round(float(funding_response["data"][0].get("fundingRate", 0)), 6)
                    else:
                        print(f"Unexpected response from {self.name} funding: {funding_response}")
                
                elif self.name == "Deribit":
                    # Obtener precio del índice
                    ticker_url = f"{self.base_url}/public/get_index_price?index_name=btc_usd"
                    ticker_response = requests.get(ticker_url, timeout=5).json()
                    if "result" in ticker_response:
                        self.prices["BTCUSDT"] = float(ticker_response["result"].get("index_price", 0))
                    else:
                        print(f"Unexpected response from {self.name} ticker: {ticker_response}")
                    
                    # Obtener funding rate con timestamp
                    start_timestamp = int((datetime.utcnow() - timedelta(hours=24)).timestamp() * 1000)
                    end_timestamp = int(datetime.utcnow().timestamp() * 1000)
                    funding_url = f"{self.base_url}/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL&start_timestamp={start_timestamp}&end_timestamp={end_timestamp}"
                    funding_response = requests.get(funding_url, timeout=5).json()
                    
                    if "result" in funding_response and isinstance(funding_response["result"], list) and len(funding_response["result"]) > 0:
                        self.funding_rates["BTCUSDT"] = round(float(funding_response["result"][0].get("interest_8h", 0)) * 100, 6)  # Convertir a porcentaje
                    else:
                        print(f"Unexpected response from {self.name} funding: {funding_response}")
                
                print(f"{self.name} - Price: {self.prices.get('BTCUSDT', 'N/A')}, Funding Rate: {self.funding_rates.get('BTCUSDT', 'N/A'):.6f}")
            
            except requests.RequestException as e:
                print(f"Error fetching data for {self.name}: {e}")
            except (KeyError, IndexError, TypeError, ValueError) as e:
                print(f"Unexpected data format from {self.name}: {e}")
            
            time.sleep(5)  # Esperar 5 segundos antes de la próxima consulta
    
    def execute_order(self, side, quantity, order_type="market"):
        """Execute an order on the exchange."""
        try:
            endpoint = f"{self.base_url}/private/{order_type}"
            payload = {
                "direction": side,
                "amount": quantity,
                "instrument_name": "BTC-PERPETUAL"
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
            
            if response.status_code != 200:
                print(f"Error executing order on {self.name}: {response.text}")
                return None
            
            return response.json()
        except requests.RequestException as e:
            print(f"Error executing order on {self.name}: {e}")
            return None

class ArbitrageBot:
    def __init__(self, exchange_a, exchange_b, leverage=4):
        self.exchange_a = exchange_a
        self.exchange_b = exchange_b
        self.leverage = leverage
    
    def check_opportunity(self):
        """Check if there is a profitable arbitrage opportunity."""
        funding_a = float(self.exchange_a.funding_rates.get('BTCUSDT', 0))
        funding_b = float(self.exchange_b.funding_rates.get('BTCUSDT', 0))
        
        if funding_b > funding_a:
            print(f"Arbitrage opportunity: Short on {self.exchange_b.name}, Long on {self.exchange_a.name}")
            return "short", self.exchange_b, self.exchange_a  # Short en B, Long en A
        elif funding_a > funding_b:
            print(f"Arbitrage opportunity: Short on {self.exchange_a.name}, Long on {self.exchange_b.name}")
            return "short", self.exchange_a, self.exchange_b  # Short en A, Long en B
        return None
    
    def execute_trade(self):
        """Execute arbitrage trade if conditions are met."""
        if self.exchange_a.position_open or self.exchange_b.position_open:
            print("Skipping trade: Position already open")
            return
        
        opportunity = self.check_opportunity()
        if opportunity:
            short_side, short_exch, long_exch = opportunity
            quantity = 1  # Ajustar según balance disponible
            
            if long_exch.execute_order("buy", quantity) and short_exch.execute_order("sell", quantity):
                long_exch.position_open = True
                short_exch.position_open = True
                print(f"Opened long on {long_exch.name}, short on {short_exch.name}")
    
    def run(self):
        """Main loop to check opportunities and trade."""
        while True:
            self.execute_trade()
            time.sleep(10)

# Load API keys
OKX_API_KEY = os.getenv("OKX_API_KEY", "f90aea6f-def9-41b8-b822-24c988cf675b")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "EE8F8D258BB153E91F3EC7E775BD036E")
DERIBIT_API_KEY = os.getenv("DERIBIT_CLIENT_ID", "WBmw1gcI")
DERIBIT_SECRET_KEY = os.getenv("DERIBIT_SECRET_KEY", "LaPPE-wBrlqtyTeo5ExX0SOUoq1la401mr5YvMb20QY")

exchange_okx = ExchangeAPI("OKX", "https://www.okx.com/api/v5", OKX_API_KEY, OKX_SECRET_KEY)
exchange_deribit = ExchangeAPI("Deribit", "https://www.deribit.com/api/v2", DERIBIT_API_KEY, DERIBIT_SECRET_KEY)

okx_thread = Thread(target=exchange_okx.fetch_data, daemon=True)
deribit_thread = Thread(target=exchange_deribit.fetch_data, daemon=True)

okx_thread.start()
deribit_thread.start()

# Iniciar bot de arbitraje
bot = ArbitrageBot(exchange_okx, exchange_deribit)
bot.run()