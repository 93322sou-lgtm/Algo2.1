# algo_engine.py
import Clock_header_module
from data.candle_builder import CandleBuilder
from indicators.ema import ema5, ema9
from indicators.rsi14 import rsi14
from indicators.bb20 import bb20
from indicators.adx14 import adx14
from indicators.volume_ma import volume_ma5, volume_ma100

from ws.ws_client import ws_connect
from ws.ws_handler import WSMessageHandler

from strategy.signal_engine import SignalEngine
from strategy.risk_manager import RiskManager
from strategy.pnl_manager import PnLManager

from orders.order_api import place_order
from orders.order_ws import OrderWS

from utils.logger import logger

from queue import Queue
import threading
import time


class AlgoEngine:
    def __init__(self, symbol="BTCUSD"):
        self.symbol = symbol
        self.log = logger.getChild("AlgoEngine")

        # Queues
        self.ohlc_queue = Queue()

        # Builders & engines
        self.candle_builder = CandleBuilder(symbol)
        self.signal_engine = SignalEngine(symbol)
        self.risk_manager = RiskManager()
        self.pnl_manager = PnLManager()

        # Order WebSocket with callback
        self.order_ws = OrderWS(on_update=self.on_order_update)

    # -----------------------------
    # Order WebSocket callback
    # -----------------------------
    def on_order_update(self, msg):
        self.log.info(f"📦 Order update: {msg}")
        self.pnl_manager.process_order_update(msg)

    # -----------------------------
    # Tick handler from WS
    # -----------------------------
    def on_tick(self, tick):
        candle = self.candle_builder.add_tick(tick)
        if candle:
            self.ohlc_queue.put(candle)

    # -----------------------------
    # 15m Candle loop
    # -----------------------------
    def candle_loop(self):
        fifteen_candles = []

        while True:
            candle = self.ohlc_queue.get()
            fifteen = self.candle_builder.build_15m(candle)
            if fifteen is None:
                continue

            fifteen_candles.append(fifteen)
            fifteen_candles = fifteen_candles[-100:]

            closes = [c['close'] for c in fifteen_candles]

            ema5_v = ema5(closes)
            ema9_v = ema9(closes)
            rsi_v = rsi14(closes)
            bb_u, bb_m, bb_l = bb20(closes)
            adx_v = adx14(fifteen_candles)
            vol_ma5_v = volume_ma5(fifteen_candles)
            vol_ma20_v = volume_ma100(fifteen_candles)

            self.log.info(
                f"15mC: {fifteen['close']} | EMA5={ema5_v:.2f} EMA9={ema9_v:.2f} "
                f"RSI={rsi_v:.2f} BB={bb_m:.2f} ADX={adx_v:.2f}"
            )

            # Signal
            signal = self.signal_engine.get_signal(ema5_v, ema9_v, rsi_v, adx_v, fifteen)
            qty, sl, tp = self.risk_manager.get_order_params(signal, fifteen)

            if signal != "NONE":
                order_id = place_order(symbol=self.symbol, side=signal, qty=qty, sl=sl, tp=tp)
                self.log.info(f"Order placed: {order_id}")

            # Update PnL
            self.pnl_manager.update(fifteen)

    # -----------------------------
    # Start engine
    # -----------------------------
    def start(self):
        # Candle thread
        threading.Thread(target=self.candle_loop, daemon=True).start()

        # Order WS
        self.order_ws.start(symbols=[self.symbol])

        # Market WS
        handler = WSMessageHandler(
            builder=self.on_tick,
            queue=self.ohlc_queue,
            symbols=[self.symbol]
        )
        ws_connect(
            tickers=[self.symbol],
            ohlc=[self.symbol],
            on_message=handler.handle
        )


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    engine = AlgoEngine("BTCUSD")
    engine.start()
    while True:
        time.sleep(1)