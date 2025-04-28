import ccxt
import pandas as pd
import numpy as np
import requests
import time

# Configurações do Telegram
TELEGRAM_TOKEN = '7986770725:AAHD3vqPIZNLHvyWVZnrHIT3xGGI1R9ZeoY'
CHAT_ID = '2091781134'

# Configurações do Bot
par = 'BTC/USDC'
timeframe = '30m'
exchange = ccxt.binance({
    'enableRateLimit': True
})

# Função para calcular indicadores
def calcular_indicadores(df):
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()
    df['EMA50'] = df['close'].ewm(span=50).mean()

    df['EMA_alinhadas'] = (df['EMA9'] > df['EMA21']) & (df['EMA21'] > df['EMA50'])

    df['MACD_line'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    df['Signal_line'] = df['MACD_line'].ewm(span=9).mean()
    df['MACD_cross'] = df['MACD_line'] > df['Signal_line']

    df['RSI6'] = rsi(df['close'], 6)
    df['RSI12'] = rsi(df['close'], 12)
    df['RSI24'] = rsi(df['close'], 24)

    df['RSI_ok'] = df['RSI6'] > 55

    # Stochastic RSI
    df['RSI14'] = rsi(df['close'], 14)
    df['StochRSI_K'], df['StochRSI_D'] = stochastic_rsi(df['RSI14'])
    df['StochRSI_cross'] = (df['StochRSI_K'] > df['StochRSI_D']) & (df['StochRSI_K'].shift(1) < df['StochRSI_D'].shift(1)) & (df['StochRSI_K'] < 20)

    return df

# Função RSI
def rsi(series, period):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Função Stochastic RSI
def stochastic_rsi(rsi_series, period=14, smoothK=3, smoothD=3):
    min_rsi = rsi_series.rolling(window=period).min()
    max_rsi = rsi_series.rolling(window=period).max()
    stoch_rsi = (rsi_series - min_rsi) / (max_rsi - min_rsi)
    stoch_rsi_k = stoch_rsi.rolling(window=smoothK).mean() * 100
    stoch_rsi_d = stoch_rsi_k.rolling(window=smoothD).mean()
    return stoch_rsi_k, stoch_rsi_d

# Função para enviar mensagem no Telegram
def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem}
    requests.post(url, data=payload)

# Puxar dados
def puxar_dados():
    ohlcv = exchange.fetch_ohlcv(par, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Bot loop
while True:
    try:
        df = puxar_dados()
        df = calcular_indicadores(df)

        ultimo = df.iloc[-1]

        if ultimo['EMA_alinhadas'] and ultimo['MACD_cross'] and ultimo['RSI_ok'] and ultimo['StochRSI_cross']:
            mensagem = (f"\u2728 SINAL DE COMPRA DETECTADO! \u2728\n"
                        f"\nAtivo: {par}"
                        f"\nTimeframe: {timeframe}"
                        f"\nPreço atual: {ultimo['close']:.2f}"
                        f"\n\nConfirmações:\n- EMAs alinhadas\n- MACD cruzado\n- RSI forte\n- Stochastic RSI cruzando")
            print(mensagem)
            enviar_telegram(mensagem)
        else:
            print(f"Sem sinal ainda... ({time.strftime('%H:%M:%S')})")

        time.sleep(60)

    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(60)
