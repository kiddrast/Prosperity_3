from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy as np

class Trader:
    def __init__(self):
        self.position_limit = {'MAGNIFICENT_MACARONS': 75}
        self.assets = list(self.position_limit.keys())
        self.sma = {product: 0.0 for product in self.position_limit}
        self.price_action = {product: [] for product in self.position_limit}
        self.CSI = 41 # Critical Sunlight Index (CSI) per la strategia di market making

    def run(self, state: TradingState) -> Dict[str, List[Order]]:

        result = {}


        for product in self.assets:

            order_depth = state.order_depths[product]

            if order_depth.buy_orders and order_depth.sell_orders:
                # Best bid and ask
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                best_ask_volume = order_depth.sell_orders[best_ask]
                # Avg price computation
                avg_buy_price = sum([np.abs(order_depth.buy_orders[i]) * i for i in order_depth.buy_orders.keys()]) / sum([np.abs(order_depth.buy_orders[i]) for i in order_depth.buy_orders.keys()])
                avg_sell_price = sum([np.abs(order_depth.sell_orders[i]) * i for i in order_depth.sell_orders.keys()])/sum([np.abs(order_depth.sell_orders[i]) for i in order_depth.sell_orders.keys()])
                price = (avg_sell_price + avg_buy_price)/2
                # Price action
                self.price_action[product].append(price)

                orders = []
                sma_window = 50

                # SMA computation
                if len(self.price_action[product]) > sma_window: 
                    sma_value = np.mean(self.price_action[product][-sma_window:])             
                    self.sma[product] = sma_value                                    

                    # Position limits
                    position = state.position.get(product, 0)
                    legal_buy = self.position_limit[product] - position
                    legal_sell = max(-(self.position_limit[product] + position), -self.position_limit[product])
                    buy_volume = min(legal_buy, best_ask_volume,10)
                    sell_volume = min(-legal_sell, best_bid_volume,10)


                    # Retrieve sunlight only
                    conv_obs = state.observations.conversionObservations[product]
                    sunlight = getattr(conv_obs, "sunlightIndex")
                    print(f'Sunlight: {sunlight} | CSI: {self.CSI}')

                    if sunlight < self.CSI:
                        # Order placement logic on SMA
                        if self.sma[product] +5 < price:
                            print("BUY", str(-best_ask_volume) + "x", best_ask)
                            orders.append(Order(product, best_ask, buy_volume))
                        elif self.sma[product] -5 > price:
                             print("SELL", str(-best_bid_volume) + "x", best_ask - 1)
                             orders.append(Order(product, best_ask, -sell_volume))

            result[product] = orders

        traderData = ""
        conversions = 1
        return result, conversions, traderData
