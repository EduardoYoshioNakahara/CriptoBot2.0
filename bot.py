import time
import requests
import pandas as pd
import ccxt

# ================= CONFIGURAÇÕES =================
TOKEN = '8194783339:AAHa0wW2QiFdvocAwk1vVowOD2QrQRGlD4U'
CHAT_ID = '2091781134'

PARES = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT']
TIMEFRAME = '30m'
INTERVALO = 60 * 5  # 5 minutos

# Mínima diferença entre EMAs no cruzamento (em % do preço)
DIFERENCA_EMA_MINIMA = 0.0005  # 0.05%

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

# Função para enviar mensagens no Telegram
def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': mensagem,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

# Função para buscar dados do par
def buscar_dados(par):
    try:
        ohlcv = exchange.fetch_ohlcv(par, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"Erro ao buscar dados de {par}: {e}")
        return None

# Função para calcular EMA e RSI
def indicadores(df):
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['RSI'] = calcular_rsi(df['close'], 14)
    return df

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Função para analisar sinais
def analisar_par(par):
    df = buscar_dados(par)
    if df is None or len(df) < 22:
        return
    df = indicadores(df)

    try:
        preco_atual = df['close'].iloc[-1]

        # Distância das EMAs no último candle
        distancia_ema = abs(df['EMA9'].iloc[-1] - df['EMA21'].iloc[-1])

        # Detectar compra
        if (
            df['EMA9'].iloc[-2] < df['EMA21'].iloc[-2] and
            df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1] and
            df['RSI'].iloc[-1] > 40 and
            distancia_ema > preco_atual * DIFERENCA_EMA_MINIMA and
            df['close'].iloc[-1] > df['open'].iloc[-1]
        ):
            entrada = preco_atual
            stop_loss = df['low'].iloc[-5:-1].min()
            take_profit = entrada + (entrada - stop_loss) * 2
            mensagem = f"""
🔔 <b>NOVO SINAL DE SCALPING</b>
<b>Par:</b> {par}
<b>Tipo:</b> 🟢 COMPRA
<b>Preço de Entrada:</b> {entrada:.4f}
🎯 <b>Take Profit:</b> {take_profit:.4f}
🛑 <b>Stop Loss:</b> {stop_loss:.4f}
⏰ <b>Timeframe:</b> 30m
"""
            enviar_telegram(mensagem)

        # Detectar venda
        elif (
            df['EMA9'].iloc[-2] > df['EMA21'].iloc[-2] and
            df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1] and
            df['RSI'].iloc[-1] < 60 and
            distancia_ema > preco_atual * DIFERENCA_EMA_MINIMA and
            df['close'].iloc[-1] < df['open'].iloc[-1]
        ):
            entrada = preco_atual
            stop_loss = df['high'].iloc[-5:-1].max()
            take_profit = entrada - (stop_loss - entrada) * 2
            mensagem = f"""
🔔 <b>NOVO SINAL DE SCALPING</b>
<b>Par:</b> {par}
<b>Tipo:</b> 🔴 VENDA
<b>Preço de Entrada:</b> {entrada:.4f}
🎯 <b>Take Profit:</b> {take_profit:.4f}
🛑 <b>Stop Loss:</b> {stop_loss:.4f}
⏰ <b>Timeframe:</b> 30m
"""
            enviar_telegram(mensagem)

    except Exception as e:
        print(f"Erro ao analisar {par}: {e}")

# Loop principal
def main():
    enviar_telegram("🚀 Bot de Scalping Trade iniciado com sucesso! Aguardando sinais...")
    while True:
        for par in PARES:
            analisar_par(par)
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()
