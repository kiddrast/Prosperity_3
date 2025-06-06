import datetime
import os
from datetime import datetime

import pandas as pd
from matplotlib import pyplot as plt
from tqdm import tqdm

from main import Listing, OrderDepth, Trade, TradingState


# Instructions on how to run this simulator can be found in the readme file
def process_trades(last_prices, last_result):
    # Computes if any trades have been performed and outputs a dictionary containing a list of traded products

    own_trades = {}
    last_result = last_result[0]
    for product in last_result.keys():

        own_trades[product] = []
        product_orders = last_result[product]
        product_row = last_prices[last_prices["product"] == product]

        for order in product_orders:
            quantity = order.quantity
            price = order.price

            if order.quantity < 0:
                # Calculate if the product was indeed sold
                for i in [1, 2, 3]:
                    if product_row[f"bid_price_{i}"].item() == product_row[f"bid_price_{i}"].item() \
                            and product_row[f"bid_price_{i}"].item() >= price \
                            and quantity != 0:
                        sold_quantity = max(quantity, -product_row[f"bid_volume_{i}"].item())
                        own_trades[product].append(
                            Trade(product, product_row[f"bid_price_{i}"].item(), sold_quantity, "", "",
                                  product_row["timestamp"].item()))
                        # Update remaining quantity
                        quantity = min(0, product_row[f"bid_volume_{i}"].item() + quantity)

            if order.quantity > 0:
                # Calculate if the product was indeed bought
                for i in [1, 2, 3]:
                    if product_row[f"ask_price_{i}"].item() == product_row[f"ask_price_{i}"].item() \
                            and product_row[f"ask_price_{i}"].item() <= price \
                            and quantity != 0:
                        bought_quantity = min(quantity, product_row[f"ask_volume_{i}"].item())
                        own_trades[product].append(
                            Trade(product, product_row[f"ask_price_{i}"].item(), bought_quantity, "", "",
                                  product_row["timestamp"]))
                        # Update remaining quantity
                        quantity = max(0, product_row[f"ask_volume_{i}"].item() + quantity)

    return own_trades


class Simulator:
    def __init__(self, prices_round: str, trades_round: str, trader):
        self.prices_round_name = prices_round
        self.trades_round_name = trades_round
        self.prices: pd.DataFrame = pd.read_csv(prices_round, delimiter=";")
        self.trades: pd.DataFrame = pd.read_csv(trades_round, delimiter=";")
        self.trader = trader

        self.position = {}
        self.position_history = {}
        for symbol in self.prices["product"].unique():
            self.position[symbol] = 0
            self.position_history[symbol] = []
            self.position_history[symbol].append(0)
        self.money_profit = {}
        self.total_pnl = {}

    def simulate(self):
        # Simulates one round of the trading game

        own_trades = {}
        unique_timestamps = self.prices["timestamp"].unique()

        for timestamp in tqdm(unique_timestamps):
            # Get the next state

            state = self.load_trading_sate(timestamp, own_trades)
            last_result = self.trader.run(state)
            # Simulate the market
            last_prices = self.prices[self.prices['timestamp'] == timestamp]
            own_trades = process_trades(last_prices, last_result)
            # Calculate the profits
            self.process_position_profit(own_trades)
            self.calculate_pnl(last_prices)

        self.plot_pnl()
        self.plot_positions()

        # Print total profit
        sum = 0
        for prod in self.total_pnl.keys():
            sum += self.total_pnl[prod][-1]
        print(f"Total profit: {sum}")

    def load_trading_sate(self, timestamp, own_trades=None):
        # Creates a new trading state given the timestamp and the own trades that have been performed in the last round

        curr_prices = self.prices[self.prices['timestamp'] == timestamp]
        listings = {}
        order_depths = {}
        market_trades = {}
        observations = {}

        for prod_row in curr_prices.iterrows():
            # Get the symbol of the product
            product = prod_row[1]["product"]
            # Set observations if sighted dolphins
            if product == "DOLPHIN_SIGHTINGS":
                observations[product] = prod_row[1]["mid_price"]
                continue
            # Add product to the listing
            listings[product] = Listing(symbol=product, product=product, denomination="SEASHELLS")

            # Add buy and sell order to the order depths
            buy_orders = {}
            if prod_row[1]["bid_price_1"] == prod_row[1]["bid_price_1"]:
                buy_orders[prod_row[1]["bid_price_1"]] = prod_row[1]["bid_volume_1"]
            if prod_row[1]["bid_price_2"] == prod_row[1]["bid_price_2"]:
                buy_orders[prod_row[1]["bid_price_2"]] = prod_row[1]["bid_volume_2"]
            if prod_row[1]["bid_price_3"] == prod_row[1]["bid_price_3"]:
                buy_orders[prod_row[1]["bid_price_3"]] = prod_row[1]["bid_volume_3"]

            sell_orders = {}
            if prod_row[1]["ask_price_1"] == prod_row[1]["ask_price_1"]:
                sell_orders[prod_row[1]["ask_price_1"]] = -prod_row[1]["ask_volume_1"]
            if prod_row[1]["ask_price_2"] == prod_row[1]["ask_price_2"]:
                sell_orders[prod_row[1]["ask_price_2"]] = -prod_row[1]["ask_volume_2"]
            if prod_row[1]["ask_price_3"] == prod_row[1]["ask_price_3"]:
                sell_orders[prod_row[1]["ask_price_3"]] = -prod_row[1]["ask_volume_3"]

            order_depths[product] = OrderDepth(buy_orders=buy_orders, sell_orders=sell_orders)

        # Update traded products
        traded_products = self.trades[self.trades["timestamp"] == timestamp]
        for traded_row in traded_products.iterrows():
            product = traded_row[1]['symbol']
            if product not in market_trades.keys():
                market_trades[product] = []
            market_trades[product].append(
                Trade(traded_row[1]['symbol'], traded_row[1]['price'], traded_row[1]['quantity'],
                      traded_row[1]['buyer'], traded_row[1]['seller'], timestamp))

        state = TradingState(
            "{}",
            timestamp=timestamp,
            listings=listings,
            order_depths=order_depths,
            own_trades=own_trades,
            market_trades=market_trades,
            observations=observations,
            position=self.position
        )

        return state

    def process_position_profit(self, traded_products):
        # Calculates and update the position and profit change given the trades made by the agent

        for product in traded_products.keys():
            product_trades = traded_products[product]

            pos_change = 0
            profit_change = 0
            for trade in product_trades:
                profit_change -= trade.price * trade.quantity
                pos_change += trade.quantity

            # Update product position
            if product not in self.position.keys():
                self.position[product] = pos_change
            else:
                self.position[product] += pos_change
            self.position_history[product].append(self.position[product])
            # Update product profit
            if product not in self.money_profit.keys():
                self.money_profit[product] = profit_change
            else:
                self.money_profit[product] += profit_change

    def calculate_pnl(self, curr_prices):
        # Calculates the current total profit and loss given the products' prices, positions and money profit

        pnl = {}
        for prod_row in curr_prices.iterrows():
            product = prod_row[1]["product"]
            if product not in self.money_profit.keys():
                continue
            pnl[product] = self.money_profit[product] + prod_row[1]["mid_price"] * self.position[product]
            if product not in self.total_pnl.keys():
                self.total_pnl[product] = []
            self.total_pnl[product].append(pnl[product])
        return pnl

    # PLOTTING FUNCTIONS
    def plot_pnl(self):
        # Plots the profit and loss after the game has been finished

        if not os.path.exists("simulator/results/pnl"):
            os.makedirs("simulator/results/pnl")

        for prod in self.total_pnl.keys():
            plt.plot(self.total_pnl[prod], label=prod)
            plt.legend()
            curr_time = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            plt.savefig(f"simulator/results/pnl/pnl_{prod}_{self.prices_round_name.replace('/', '_')}_{curr_time}.jpg")
            plt.clf()

    def plot_midprices(self):
        # Plots mid_prices found in the csv file

        if not os.path.exists("simulator/results/midprices"):
            os.makedirs("simulator/results/midprices")

        unique_prods = self.prices["product"].unique()
        for product in unique_prods:
            prod_rows = self.prices[self.prices["product"] == product]
            # print(prod_rows["mid_price"].reset_index())
            plt.plot(prod_rows["mid_price"].reset_index(drop=True))
            plt.savefig(f"simulator/results/midprices/mid_price_{product}_{self.prices_round_name.replace('/', '_')}.jpg")
            plt.clf()

    def plot_positions(self):
        # Plots positions of the products after the game has been finished

        if not os.path.exists("simulator/results/positions"):
            os.makedirs("simulator/results/positions")

        unique_prods = self.prices["product"].unique()
        for product in unique_prods:
            plt.plot(self.position_history[product])
            curr_time = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            plt.savefig(f"simulator/results/positions/positions_{product}_{self.prices_round_name.replace('/', '_')}_{curr_time}.jpg")
            plt.clf()
