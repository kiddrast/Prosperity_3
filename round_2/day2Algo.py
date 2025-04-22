from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy as np

# --- Strategia per i BASKET (PICNIC_BASKET1 e PICNIC_BASKET2) ---
# Ogni basket è una combinazione di prodotti:
# - PICNIC_BASKET1 = 6 CROISSANTS + 3 JAMS + 1 DJEMBE
# - PICNIC_BASKET2 = 4 CROISSANTS + 2 JAMS
# Calcolo il fair value del basket sommando i prezzi medi (mid price) dei singoli prodotti moltiplicati per i loro pesi.
# Se il prezzo di mercato del basket (best_bid o best_ask) è molto più alto del fair value → vendo il basket (è sopravvalutato).
# Se è molto più basso → compro il basket (è sottovalutato).
# È una strategia di arbitraggio: cerco di sfruttare differenze tra il valore reale del basket e il suo prezzo sul mercato.

# --- Strategia per gli ASSET singoli (DJEMBES e RAINFOREST_RESIN) ---
# Per questi asset faccio market making.
# Guardo il miglior bid e il miglior ask.
# Se lo spread tra ask e bid è almeno 2 punti, vuol dire che posso provare a guadagnare facendo da \"intermediario\".
# In questo caso:
# - piazzo un ordine di acquisto leggermente sopra il miglior bid (per aumentare la probabilità che venga eseguito)
# - piazzo un ordine di vendita leggermente sotto il miglior ask
# L’idea è comprare basso, vendere alto e incassare la differenza (spread).
# Tengo conto anche della posizione corrente per non superare i limiti massimi definiti.

class Trader:
    def __init__(self):
        # Limiti di posizione per ogni prodotto
        self.position_limit = {
            'CROISSANTS': 250,
            'JAMS': 350,
            'DJEMBES': 60,
            'PICNIC_BASKET1': 60,
            'PICNIC_BASKET2': 100,
            'RAINFOREST_RESIN': 50
        }
        # Prezzo medio precedente per ogni prodotto
        self.last_mid_price = {product: {} for product in self.position_limit}
        # Prezzo medio esponenziale (EMA) per ogni prodotto
        self.ema_price = {product: {} for product in self.position_limit}

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        # --- Step 1: Calcolo dei prezzi medi dei prodotti base ---
        mid_prices = {}
        for product in ['CROISSANTS', 'JAMS', 'DJEMBES']:
            order_depth = state.order_depths[product]
            if order_depth.buy_orders and order_depth.sell_orders:
                # Calcolo del prezzo medio come media tra il miglior bid e il miglior ask
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                mid_price = (best_ask + best_bid) / 2
                mid_prices[product] = mid_price
                self.last_mid_price[product] = mid_price
            else:
                # Se non ci sono ordini, utilizza l'ultimo prezzo medio noto
                mid_prices[product] = self.last_mid_price[product]

        # --- Step 2: Calcolo dei valori equi (fair values) per i cesti ---
        # Valore equo del primo cesto basato sui pesi dei prodotti
        basket1_fv = 6 * mid_prices['CROISSANTS'] + 3 * mid_prices['JAMS'] + 1 * mid_prices['DJEMBES']
        # Valore equo del secondo cesto basato sui pesi dei prodotti
        basket2_fv = 4 * mid_prices['CROISSANTS'] + 2 * mid_prices['JAMS']

        # --- Step 3: Logica di arbitraggio sui cesti ---
        for basket, fv in [('PICNIC_BASKET1', basket1_fv), ('PICNIC_BASKET2', basket2_fv)]:
            order_depth = state.order_depths[basket]
            current_position = state.position.get(basket, 0)
            # Calcolo dei limiti legali per comprare e vendere
            legal_buy = min(self.position_limit[basket] - current_position, self.position_limit[basket])
            legal_sell = max(-(self.position_limit[basket] + current_position), -self.position_limit[basket])
            orders = []

            if order_depth.buy_orders:
                # Se il miglior bid è significativamente maggiore del valore equo, vendi
                best_bid = max(order_depth.buy_orders.keys())
                if best_bid > fv + 2:
                    volume = min(-order_depth.buy_orders[best_bid], legal_sell)
                    print(f"SELL {basket} @ {best_bid}, FV={fv}")
                    orders.append(Order(basket, best_bid, volume))

            if order_depth.sell_orders:
                # Se il miglior ask è significativamente minore del valore equo, compra
                best_ask = min(order_depth.sell_orders.keys())
                if best_ask < fv - 2:
                    volume = min(-order_depth.sell_orders[best_ask], legal_buy)
                    print(f"BUY {basket} @ {best_ask}, FV={fv}")
                    orders.append(Order(basket, best_ask, volume))

            result[basket] = orders

        # --- Step 4: Strategia di market making per i prodotti base ---
        for product in ['DJEMBES', 'RAINFOREST_RESIN']:
            order_depth = state.order_depths[product]
            orders = []
            position = state.position.get(product, 0)
            # Calcolo dei limiti legali per comprare e vendere
            legal_buy = min(self.position_limit[product] - position, self.position_limit[product])
            legal_sell = max(-(self.position_limit[product] + position), -self.position_limit[product])

            if order_depth.buy_orders and order_depth.sell_orders:
                # Calcolo del miglior bid, miglior ask e spread
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                spread = best_ask - best_bid
                # Calcolo del prezzo medio come valore equo
                mid_price = (best_bid + best_ask) / 2
                fair_value = mid_price

                # Fornisci liquidità attorno al valore equo se lo spread è sufficiente
                if spread > 1:
                    bid_price = best_bid + 1
                    ask_price = best_ask - 1

                    bid_volume = min(legal_buy, 10)
                    ask_volume = min(-legal_sell, 10)

                    print(f"{product}: MARKET MAKING - BUY {bid_volume} @ {bid_price}, SELL {ask_volume} @ {ask_price}")
                    orders.append(Order(product, bid_price, bid_volume))
                    orders.append(Order(product, ask_price, -ask_volume))

            result[product] = orders


        traderData = ""
        conversions = 1
        return result, conversions, traderData
