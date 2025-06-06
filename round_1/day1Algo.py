from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy as np

#ISTRUZIONI PER IL BACKTESTING
#Per fare il backtesting, bisogna installare il modulo prosperity3bt tramite il comando "pip install -U prosperity3bt" sul terminale
#Per eseguire il backtesting del round 0, bisogna usare il comando "prosperity3bt tutorial.py 0" sempre sul terminale
#L'output dovrebbe essere di un profitto di 3724

class Trader:
    # define data members
    def __init__(self):
        self.position_limit = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}
        self.last_mid_price = {'RAINFOREST_RESIN': 10000, 'KELP': 2020, 'SQUID_INK': 10000}
        self.mid_price = {'RAINFOREST_RESIN': {0: 10000}, 'KELP': {0: 2010}, 'SQUID_INK': {0: 10000}}
        self.ema_price = {'RAINFOREST_RESIN': {0: 10000}, 'KELP': {0: 2010}, 'SQUID_INK': {0: 10000}}
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}
        # Iterate over all the keys (the available products) contained in the order dephts
        for product in state.order_depths.keys():
            # Check if the current product is the 'RAINFOREST_RESIN' product, only then run the order logic
            if product == 'RAINFOREST_RESIN':
                N = 50
                
                
                # Retrieve the Order Depth containing all the market BUY and SELL orders for RAINFOREST_RESIN
                order_depth: OrderDepth = state.order_depths[product]
                # quote volume limit
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = order_depth.sell_orders[best_ask]
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                mid_price = (best_ask * np.abs(best_ask_volume) + best_bid * np.abs(best_bid_volume)) / (np.abs(best_ask_volume) + np.abs(best_bid_volume))
                ema_price = (2 * mid_price + (N - 1) * self.ema_price[product][list(self.ema_price[product].keys())[-1]]) / (N + 1)
                self.mid_price[product][state.timestamp] = mid_price
                self.ema_price[product][state.timestamp] = ema_price
                # print(f'{state.timestamp}: The mid price of {product} is {self.mid_price[product][state.timestamp]}.')
                if product in state.position.keys():
                    current_position = state.position[product]
                else:
                    current_position = 0
                legal_buy_vol = np.minimum(self.position_limit[product] - current_position,self.position_limit[product])
                legal_sell_vol = np.maximum(-(self.position_limit[product] + current_position),-self.position_limit[product])
               

                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                # Define a fair value for the PEARLS.
                acceptable_price = ema_price

                # If statement checks if there are any SELL orders in the RAINFOREST_RESINS market
                if len(order_depth.sell_orders) > 0:

                    # Sort all the available sell orders by their price,
                    # and select only the sell order with the lowest price
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]

                    # Check if the lowest ask (sell order) is lower than the above defined fair value
                    if best_ask <= acceptable_price:

                        # In case the lowest ask is lower than our fair value,
                        # This presents an opportunity for us to buy cheaply
                        # The code below therefore sends a BUY order at the price level of the ask,
                        # with the same quantity
                        # We expect this order to trade with the sell order
                        print("BUY", str(-best_ask_volume) + "x", best_ask)
                        orders.append(Order(product, best_ask, int(np.minimum(-best_ask_volume,legal_buy_vol))))
                    if best_bid + 1 <= acceptable_price:
                        print("BUY", str(-best_ask_volume) + "x", best_bid + 1)
                        orders.append(Order(product, best_bid + 1, int(np.minimum(-best_ask_volume,legal_buy_vol))))

                # The below code block is similar to the one above,
                # the difference is that it find the highest bid (buy order)
                # If the price of the order is higher than the fair value
                # This is an opportunity to sell at a premium
                if len(order_depth.buy_orders) != 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    if best_bid >= acceptable_price:
                        print("SELL", str(best_bid_volume) + "x", best_bid)
                        orders.append(Order(product, best_bid, int(np.maximum(-best_bid_volume,legal_sell_vol))))
                    if best_ask - 1 >= acceptable_price:
                        print("SELL", str(-best_bid_volume) + "x", best_ask - 1)
                        orders.append(Order(product, best_ask - 1, int(np.minimum(-best_bid_volume,legal_sell_vol))))

                # Add all the above the orders to the result dict
                result[product] = orders

                # Return the dict of orders
                # These possibly contain buy or sell orders for PEARLS
                # Depending on the logic above
            elif product == 'KELP':

                # Retrieve the Order Depth containing all the market BUY and SELL orders for KELP
                order_depth: OrderDepth = state.order_depths[product]

                # quote volume limit
                if product in state.position.keys():
                    current_position = state.position[product]
                else:
                    current_position = 0
                legal_buy_vol = np.minimum(self.position_limit[product] - current_position,self.position_limit[product])
                legal_sell_vol = np.maximum(-(self.position_limit[product] + current_position),-self.position_limit[product])
                
                if len(order_depth.sell_orders) != 0 and len(order_depth.buy_orders) != 0:
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    avg_buy_price = sum([np.abs(order_depth.buy_orders[i]) * i for i in order_depth.buy_orders.keys()])/sum([np.abs(order_depth.buy_orders[i]) for i in order_depth.buy_orders.keys()])
                    avg_sell_price = sum([np.abs(order_depth.sell_orders[i]) * i for i in order_depth.sell_orders.keys()])/sum([np.abs(order_depth.sell_orders[i]) for i in order_depth.sell_orders.keys()])
                    mid_price = (avg_sell_price + avg_buy_price)/2
                else:
                    mid_price = self.last_mid_price[product]
                self.last_mid_price[product] = mid_price
                acceptable_price = mid_price
                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                # Calculate the mid price of the PEARLS market
                if len(order_depth.sell_orders) > 0:

                    # Sort all the available sell orders by their price,
                    # and select only the sell order with the lowest price
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]

                    # Check if the lowest ask (sell order) is lower than the above defined fair value
                    if best_ask <= acceptable_price:

                        # In case the lowest ask is lower than our fair value,
                        # This presents an opportunity for us to buy cheaply
                        # The code below therefore sends a BUY order at the price level of the ask,
                        # with the same quantity
                        # We expect this order to trade with the sell order
                        print("BUY", str(-best_ask_volume) + "x", best_ask)
                        orders.append(Order(product, best_ask, int(np.minimum(-best_ask_volume,legal_buy_vol))))
                    if best_ask - 1 >= acceptable_price:
                        print("SELL", str(-best_bid_volume) + "x", best_ask - 1)
                        orders.append(Order(product, best_ask - 1, int(np.minimum(-best_bid_volume,legal_sell_vol))))

                # The below code block is similar to the one above,
                # the difference is that it find the highest bid (buy order)
                # If the price of the order is higher than the fair value
                # This is an opportunity to sell at a premium
                if len(order_depth.buy_orders) != 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    if best_bid >= acceptable_price:
                        print("SELL", str(best_bid_volume) + "x", best_bid)
                        orders.append(Order(product, best_bid, int(np.maximum(-best_bid_volume,legal_sell_vol))))
                    
                    if best_bid + 1 <= acceptable_price:
                        print("BUY", str(-best_ask_volume) + "x", best_bid + 1)
                        orders.append(Order(product, best_bid + 1, int(np.minimum(-best_ask_volume,legal_buy_vol))))
                # Add all the above the orders to the result dict
                result[product] = orders
                


##########################################################################################################################################
                 
            elif product == 'SQUID_INK':

                # Retrieve the Order Depth containing all the market BUY and SELL orders for KELP
                order_depth: OrderDepth = state.order_depths[product]

                # quote volume limit
                if product in state.position.keys():
                    current_position = state.position[product]
                else:
                    current_position = 0
                legal_buy_vol = np.minimum(self.position_limit[product] - current_position,self.position_limit[product])
                legal_sell_vol = np.maximum(-(self.position_limit[product] + current_position),-self.position_limit[product])
                
                if len(order_depth.sell_orders) != 0 and len(order_depth.buy_orders) != 0:
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]


                    avg_buy_price =  sum([np.abs(order_depth.buy_orders[i])  * i for i in order_depth.buy_orders.keys()])/sum([np.abs(order_depth.buy_orders[i]) for i in order_depth.buy_orders.keys()])
                    avg_sell_price = sum([np.abs(order_depth.sell_orders[i]) * i for i in order_depth.sell_orders.keys()])/sum([np.abs(order_depth.sell_orders[i]) for i in order_depth.sell_orders.keys()])
                    mid_price = (avg_sell_price + avg_buy_price)/2


                else:
                    mid_price = self.last_mid_price[product]
                self.last_mid_price[product] = mid_price
                acceptable_price = mid_price
                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []



                # Calculate the mid price of the PEARLS market
                if len(order_depth.sell_orders) > 0:
                    # Sort all the available sell orders by their price,
                    # and select only the sell order with the lowest price
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]

                    # Check if the lowest ask (sell order) is lower than the above defined fair value
                    if best_ask <= acceptable_price:
                        print("BUY", str(-best_ask_volume) + "x", best_ask)
                        orders.append(Order(product, best_ask, int(np.minimum(-best_ask_volume,legal_buy_vol))))
                    if best_ask - 1 >= acceptable_price:
                        print("SELL", str(-best_bid_volume) + "x", best_ask - 1)
                        orders.append(Order(product, best_ask - 1, int(np.minimum(-best_bid_volume,legal_sell_vol))))

                if len(order_depth.buy_orders) != 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    if best_bid >= acceptable_price:
                        print("SELL", str(best_bid_volume) + "x", best_bid)
                        orders.append(Order(product, best_bid, int(np.maximum(-best_bid_volume,legal_sell_vol))))
                    
                    if best_bid + 1 <= acceptable_price:
                        print("BUY", str(-best_ask_volume) + "x", best_bid + 1)
                        orders.append(Order(product, best_bid + 1, int(np.minimum(-best_ask_volume,legal_buy_vol))))




##########################################################################################################################################
                # Add all the above the orders to the result dict
                result[product] = orders

        # String value holding Trader state data required. 
		# It will be delivered as TradingState.traderData on next execution.
        traderData = "SAMPLE" 
        
		# Sample conversion request. Check more details below. 
        conversions = 1
        return result, conversions, traderData
    


