import os
import time
import logging
import sqlite3
import ccxt
import requests
import pandas as pd
import numpy as np

from dotenv import load_dotenv

# Carrega variáveis de ambiente de .env
load_dotenv()

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    filename=os.getenv("LOG_FILE", "bot.log")
)

# Configuração da exchange (Binance)
binance = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET')
})

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Parâmetros de estratégia, gestão de risco e stake fixa
CONFIG = {
    'pairs': os.getenv('PAIRS', 'BTC/USDT').split(','),
    'timeframes': os.getenv('TIMEFRAMES', '1h,4h').split(','),
    'limit': int(os.getenv('LIMIT', '100')),
    'ema_short': int(os.getenv('EMA_SHORT', '9')),
    'ema_long': int(os.getenv('EMA_LONG', '21')),
    'rsi_period': int(os.getenv('RSI_PERIOD', '14')),
    'atr_period': int(os.getenv('ATR_PERIOD', '14')),
    'volume_ma_period': int(os.getenv('VOL_MA_PERIOD', '20')),
    'risk_per_trade': float(os.getenv('RISK_PER_TRADE', '0.02')),
    'max_daily_drawdown': float(os.getenv('MAX_DAILY_DRAWDOWN', '0.05')),
    'interval_min': int(os.getenv('INTERVAL_MIN', '15')),
    'stake_usdt': float(os.getenv('STAKE_USDT', '10'))  # Valor fixo por entrada
}

# Banco de dados local
conn = sqlite3.connect(os.getenv('DB_PATH', 'trades.db'), check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS trades(
    ts TEXT,
    symbol TEXT,
    side TEXT,
    price REAL,
    result REAL
)
""")
conn.commit()

class TradeBot:
    def __init__(self, exchange, token, chat_id, config):
        self.exchange = exchange
        self.token = token
        self.chat_id = chat_id
        self.config = config
        self.last_signal = {s: None for s in config['pairs']}

    def safe_request(self, url, params, retries=3, delay=5):
        for i in range(retries):
            try:
                r = requests.get(url, params=params, timeout=10)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logging.warning(f"Request falhou ({i+1}/{retries}): {e}")
                time.sleep(delay)
        logging.error("Request falhou definitivamente")
        return None

    def send_telegram(self, message):
        url = f'https://api.telegram.org/bot{self.token}/sendMessage'
        params = {'chat_id': self.chat_id, 'text': message}
        self.safe_request(url, params)
        logging.info(f"Telegram: {message}")

    def send_open_order_status(self, symbol, side, entry, stop_loss, take_profit, status, pnl):
        msg = (
            f"📝 ORDEM EM ABERTO: {symbol}\n"
            f"Tipo: {side}\n"
            f"Entrada: {entry:.2f}\n"
            f"Stop Loss: {stop_loss:.2f}\n"
            f"Take Profit: {take_profit:.2f}\n"
            f"Status: {status}\n"
            f"Lucro/Perda: {pnl:.2f} USDT"
        )
        self.send_telegram(msg)

    def fetch_ohlcv(self, symbol, timeframe):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=self.config['limit'])
        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def calculate_indicators(self, df):
        df['ema_short'] = df['close'].ewm(span=self.config['ema_short'], adjust=False).mean()
        df['ema_long'] = df['close'].ewm(span=self.config['ema_long'], adjust=False).mean()
        # RSI
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=self.config['rsi_period'], min_periods=1).mean()
        avg_loss = loss.rolling(window=self.config['rsi_period'], min_periods=1).mean()
        df['rsi'] = 100 - (100/(1 + avg_gain/avg_loss))
        # ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=self.config['atr_period'], min_periods=1).mean()
        # Volume MA
        df['vol_ma'] = df['volume'].rolling(window=self.config['volume_ma_period'], min_periods=1).mean()
        return df

    def calculate_position_size(self, entry_price):
        stake = self.config['stake_usdt']
        return stake / entry_price if entry_price > 0 else 0

    def confirm_multitimeframe(self, symbol):
        signals = []
        for tf in self.config['timeframes']:
            df = self.fetch_ohlcv(symbol, tf)
            df = self.calculate_indicators(df)
            last, prev = df.iloc[-1], df.iloc[-2]
            if last['ema_short'] > last['ema_long'] and prev['ema_short'] < prev['ema_long'] and last['rsi']<70 and last['volume']>last['vol_ma']:
                signals.append('BUY')
            elif last['ema_short'] < last['ema_long'] and prev['ema_short'] > prev['ema_long'] and last['rsi']>30 and last['volume']>last['vol_ma']:
                signals.append('SELL')
            else:
                signals.append(None)
        return signals.count(signals[0]) == len(signals) and signals[0]

    def check_signals(self):
        for symbol in self.config['pairs']:
            signal = self.confirm_multitimeframe(symbol)
            if signal and signal != self.last_signal[symbol]:
                df = self.fetch_ohlcv(symbol, self.config['timeframes'][0])
                df = self.calculate_indicators(df)
                last = df.iloc[-1]
                entry_price = last['close']
                atr = last['atr']
                side = 'Compra' if signal=='BUY' else 'Venda'
                stop_loss = entry_price - atr
                take_profit = entry_price + 2*(entry_price - stop_loss)
                pnl_initial = 0.0
                self.send_open_order_status(symbol, side, entry_price, stop_loss, take_profit, 'Em Aberto', pnl_initial)
                self.log_trade(symbol, side, entry_price, pnl_initial)
                self.last_signal[symbol] = signal

    def run(self):
        self.send_telegram("Bot profissional iniciado com múltiplas melhorias.")
        interval_sec = self.config['interval_min'] * 60
        next_run = time.time()
        while True:
            now = time.time()
            if now >= next_run:
                self.check_signals()
                next_run = now + interval_sec
            time.sleep(1)

if __name__ == '__main__':
    bot = TradeBot(binance, TELEGRAM_TOKEN, CHAT_ID, CONFIG)
    bot.run()
