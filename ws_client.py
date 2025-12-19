# =====================================================
# Delta Exchange WebSocket Client - আপনার Algo Trading এর Foundation
# =====================================================
import json           # JSON ডেটা পড়ার জন্য (Delta থেকে আসে)
import websocket      # WebSocket চ্যাট করার জন্য
from threading import Thread  # Background এ চালানোর জন্য (main কোড block হবে না)

# Delta Exchange India এর চ্যাট রুমের URL
WS_URL = "wss://socket.india.delta.exchange"

def ws_connect(tickers=None, ohlc=None, on_message=None, on_error=None, on_close=None):
    """
    Delta Exchange এ রিয়েল-টাইম ডেটা নেয়ার WebSocket
    tickers=["BTCUSDT"] → লাইভ প্রাইস আপডেট
    ohlc=["BTCUSDT"]   → ১মিনিট ক্যান্ডল (OHLCV)
    on_message=আপনার_ফাংশন → ডেটা পেলে এখানে আসবে
    """
    
    tickers = tickers or []  # খালি লিস্ট দিলে []
    ohlc = ohlc or []        # খালি লিস্ট দিলে []

    # =====================================================
    # ১. ডেটা আসলে কী করবে? (সবচেয়ে গুরুত্বপূর্ণ)
    # =====================================================
    def _on_message(ws, message):
        print("RAW JSON:", message)  # Debug: raw দেখাও
        
        if on_message:               # আপনার ফাংশন আছে কিনা চেক
            try:
                data = json.loads(message)   # JSON → Python dict
                on_message(data)             # আপনার ফাংশনে পাঠাও (trading logic এখানে)
            except Exception as e:
                print("Message parse error:", e)  # JSON ভুল হলে

    # =====================================================
    # ২. Error হলে কী করবে?
    # =====================================================
    def _on_error(ws, error):
        if on_error:
            on_error(error)
        else:
            print("❌ WebSocket error:", error)

    # =====================================================
    # ৩. চ্যাট বন্ধ হলে কী করবে?
    # =====================================================
    def _on_close(ws, status, msg):
        if on_close:
            on_close(status, msg)
        else:
            print("🔴 WebSocket closed:", status, msg)

    # =====================================================
    # ৪. কানেক্ট হলে প্রথম কাজ (সবচেয়ে গুরুত্বপূর্ণ)
    # =====================================================
    def _on_open(ws):
        print("📡 WebSocket Connected ✅")
        
        # দাম আপডেট চাইলে (লাইভ প্রাইস)
        if tickers:
            payload = {
                "type": "subscribe",
                "payload": {
                    "channels": [
                        {"name": "v2/ticker", "symbols": tickers}  # "BTCUSDT দাম পাঠাও"
                    ]
                }
            }
            ws.send(json.dumps(payload))
            print(f"✅ Ticker subscribe: {tickers}")

        # ১মিনিট ক্যান্ডল চাইলে (OHLCV)
        if ohlc:
            payload = {
                "type": "subscribe",
                "payload": {
                    "channels": [
                        {"name": "candlestick_1m", "symbols": ohlc}  # "BTCUSDT ক্যান্ডল পাঠাও"
                    ]
                }
            }
            ws.send(json.dumps(payload))
            print(f"✅ OHLC subscribe: {ohlc}")

    # =====================================================
    # WebSocket App তৈরি + Background থ্রেডে চালু
    # =====================================================
    ws_app = websocket.WebSocketApp(
        WS_URL,                    # চ্যাট রুম URL
        on_open=_on_open,          # কানেক্ট হলে
        on_message=_on_message,    # ডেটা আসলে
        on_error=_on_error,        # Error হলে
        on_close=_on_close         # বন্ধ হলে
    )
    
    # Background এ চালু (main কোড block হবে না)
    thread = Thread(target=ws_app.run_forever)
    thread.daemon = True     # Main বন্ধ হলে এটিও বন্ধ
    thread.start()
    
    print("🚀 WebSocket background এ চলছে...")
    return ws_app  # Control ফেরত দাও (stop করতে পারো)

# =====================================================
# ✅ ব্যবহারের উদাহরণ (Pydroid 3/Jupyter এ copy-paste করুন)
# =====================================================
if __name__ == "__main__":
    def my_data_handler(data):  # আপনার trading logic এখানে
        if 'channel' in data:
            if data['channel'] == 'v2/ticker':
                price = data['data'][0]['price']
                symbol = data['data'][0]['symbol']
                print(f"🟢 {symbol}: ${price}")
            elif data['channel'] == 'candlestick_1m':
                print(f"📊 {data['data'][0]['symbol']} নতুন ক্যান্ডল")

    # চালু করুন
    ws = ws_connect(
        tickers=["BTCUSD", "ETHUSD","SOLUSD", "XRPUSD"],  # লাইভ দাম
        ohlc=["BTCUSD", "ETHUSD","SOLUSD", "XRPUSD"], # ১মিনিট ক্যান্ডল
        on_message=my_data_handler        # ডেটা হ্যান্ডলার
    )
    
    print("Ctrl+C দিয়ে বন্ধ করুন...")
    input("Enter চাপলে চলবে...")  # ∞ চলবে