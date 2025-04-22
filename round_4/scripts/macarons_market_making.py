from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy as np



class Trader:
    def __init__(self):
        # Limiti di posizione per ogni prodotto
        self.position_limit = {
            'CROISSANTS': 250,
            'JAMS': 350,
            'DJEMBES': 60,
            'PICNIC_BASKET1': 60,
            'PICNIC_BASKET2': 100,
            'RAINFOREST_RESIN': 50,
            'SQUID_INK': 50,
            'VOLCANIC_ROCK': 400,
            'VOLCANIC_ROCK_VOUCHER_9500': 200,
            'VOLCANIC_ROCK_VOUCHER_9750': 200,
            'VOLCANIC_ROCK_VOUCHER_10000': 200,
            'VOLCANIC_ROCK_VOUCHER_10250': 200,
            'VOLCANIC_ROCK_VOUCHER_10500': 200,
            'MAGNIFICENT_MACARONS': 75,
        }
        self.voucher_strikes = {
            'VOLCANIC_ROCK_VOUCHER_9500': 9500,
            'VOLCANIC_ROCK_VOUCHER_9750': 9750,
            'VOLCANIC_ROCK_VOUCHER_10000': 10000,
            'VOLCANIC_ROCK_VOUCHER_10250': 10250,
            'VOLCANIC_ROCK_VOUCHER_10500': 10500,
        }
        # Prezzo medio precedente per ogni prodotto
        self.last_mid_price = {product: {} for product in self.position_limit}
        # Prezzo medio esponenziale (EMA) per ogni prodotto
        self.ema_price = {product: {} for product in self.position_limit}
        self.assets = list(self.position_limit.keys())
        self.sma = {product: 0.0 for product in self.position_limit}
        self.price_action = {product: [] for product in self.position_limit}
        self.CSI = 45 # Critical Sunlight Index (CSI) per la strategia di market making






    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}


        for product in ['MAGNIFICENT_MACARONS']:
            orders: List[Order] = []
            
            order_depth = state.order_depths[product]
            best_bid = max(order_depth.buy_orders)
            best_ask = min(order_depth.sell_orders)


            # Retrieve sunlight only
            conv_obs = state.observations.conversionObservations[product]
            sunlight = getattr(conv_obs, "sunlightIndex")
            print(f'Sunlight: {sunlight} | CSI: {self.CSI}')


            # Position and limits
            position = state.position.get(product, 0)
            limit = self.position_limit[product]
            legal_buy = max(0, limit - position)
            legal_sell = max(0, position + limit)
            # Market making when sunlight < CSI
            if sunlight < self.CSI:
                spread = best_ask - best_bid
                
                if spread >= 1:
                    bid_price = best_bid + 1
                    ask_price = best_ask - 1
                    bid_volume = min(10, legal_buy)
                    ask_volume = min(10, legal_sell)

                    print(f"[MM BUY] {bid_volume}x @ {bid_price}, Sunlight={sunlight}")
                    print(f"[MM SELL] {ask_volume}x @ {ask_price}, Sunlight={sunlight}")
                    orders.append(Order(product, bid_price, bid_volume))
                    orders.append(Order(product, ask_price, -ask_volume))

                result[product] = orders



        traderData = ""
        conversions = 0
        return result, conversions, traderData