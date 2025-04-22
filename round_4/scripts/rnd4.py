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

# --- Strategia per i VOUCHER VOLCANIC_ROCK ---
# Ogni voucher ti dà il diritto di acquistare VOLCANIC_ROCK a un certo prezzo (strike) alla scadenza.
# Calcolo il valore "intrinseco" del voucher come:
#     valore_intrinseco = max(0, prezzo_mid_VOLCANIC_ROCK - strike)
# Se trovo un voucher in vendita (best_ask) a un prezzo MOLTO inferiore rispetto al suo valore intrinseco, lo compro.
# Se trovo un bid sul voucher molto maggiore del suo valore intrinseco, vendo (shorto) il voucher.
# In pratica, cerco di comprare voucher sottovalutati e vendere quelli sopravvalutati.
# Questa è una strategia di arbitraggio basata sul confronto tra prezzo di mercato del voucher e il suo valore teorico.

# --- Strategia su VOLCANIC_ROCK (sottostante) ---
# Se il book ha sia bid che ask e lo spread tra i due è abbastanza ampio (es. ≥2),
# faccio market making per guadagnare dallo spread.
# In questo caso:
# - piazzo un ordine di acquisto a best_bid + 1
# - piazzo un ordine di vendita a best_ask - 1
# In questo modo mi posiziono tra bid e ask e provo a "fare il mercato".
# Naturalmente rispetto sempre i limiti di posizione (legal_buy e legal_sell).

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
                if best_bid > fv + 4:
                    volume = min(-order_depth.buy_orders[best_bid], legal_sell)
                    print(f"SELL {basket} @ {best_bid}, FV={fv}")
                    orders.append(Order(basket, best_bid, volume))

            if order_depth.sell_orders:
                # Se il miglior ask è significativamente minore del valore equo, compra
                best_ask = min(order_depth.sell_orders.keys())
                if best_ask < fv - 4:
                    volume = min(-order_depth.sell_orders[best_ask], legal_buy)
                    print(f"BUY {basket} @ {best_ask}, FV={fv}")
                    orders.append(Order(basket, best_ask, volume))

            result[basket] = orders

        # --- Step 4: Strategia di market making per i prodotti base ---
        for product in ['DJEMBES', 'RAINFOREST_RESIN']:
            order_depth = state.order_depths[product]
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

                # Fornisci liquidità attorno al valore equo se lo spread è sufficiente
                if spread > 1:
                    bid_price = best_bid + 1
                    ask_price = best_ask - 1

                    bid_volume = min(legal_buy, 15)
                    ask_volume = -min(legal_sell, 15)

                    print(f"{product}: BUY {bid_volume} @ {bid_price}, SELL {ask_volume} @ {ask_price}")
                    orders.append(Order(product, bid_price, bid_volume))
                    orders.append(Order(product, ask_price, -ask_volume))

            result[product] = orders
            

        for product in ['SQUID_INK', 'CROISSANTS', 'JAMS']:
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
                    buy_volume = min(legal_buy, best_ask_volume,20)
                    sell_volume = min(-legal_sell, best_bid_volume,20)

                    # Order placement logic on SMA
                    if self.sma[product] < price:
                        print("BUY", str(-best_ask_volume) + "x", best_ask)
                        orders.append(Order(product, best_ask, buy_volume))
                    elif self.sma[product] > price:
                        print("SELL", str(-best_bid_volume) + "x", best_ask - 1)
                        orders.append(Order(product, best_ask, -sell_volume))
                    
            result[product] = orders

        for product in ['MAGNIFICENT_MACARONS']:
            orders: List[Order] = []

            order_depth = state.order_depths[product]
            if not order_depth.buy_orders or not order_depth.sell_orders:
                result[product] = []
                return result, 1, ""

            best_bid = max(order_depth.buy_orders)
            best_ask = min(order_depth.sell_orders)
            mid_price = (best_bid + best_ask) / 2
            sugar = state.observations.plainValueObservations.get("SUGAR", 100)
            sunlight = state.observations.plainValueObservations.get("SUNLIGHT", 200)
            sunlight_sq = sunlight ** 2
            transport = state.observations.plainValueObservations.get("TRANSPORT_FEE", 1)
            export_tariff = state.observations.plainValueObservations.get("EXPORT_TARIFF", 1)
            import_tariff = state.observations.plainValueObservations.get("IMPORT_TARIFF", 1)

            # Calculate fair value from regression model
            fair_value = (
                -173.43 +
                (-75.37 * transport) +
                (-61.49 * export_tariff) +
                (-34.63 * import_tariff) +
                (7.59 * sugar) +
                (-4.76 * sunlight) +
                (0.0336 * sunlight_sq)
            )

            position = state.position.get(product, 0)
            limit = self.position_limit[product]
            legal_buy = max(0, limit - position)
            legal_sell = max(0, position + limit)

            # --- Trading Logic based on deviation from fair value ---
            if best_ask < fair_value:
                ask_volume = -order_depth.sell_orders[best_ask]
                volume = min(ask_volume, legal_buy)
                if volume > 0:
                    print(f"[REGRESSION BUY] {volume}x @ {best_ask} < FV({fair_value:.2f})")
                    orders.append(Order(product, best_ask, volume))

            if best_bid > fair_value:
                bid_volume = order_depth.buy_orders[best_bid]
                volume = min(bid_volume, legal_sell)
                if volume > 0:
                    print(f"[REGRESSION SELL] {volume}x @ {best_bid} > FV({fair_value:.2f})")
                    orders.append(Order(product, best_bid, -volume))   
            
            result[product] = orders

        # --- Step 5: Strategia di arbitraggio per i voucher di VOLCANIC_ROCK ---
        # Step 1: Calcolo dei valori equi per i voucher
        # Calcolo del fair value per ogni voucher in base al prezzo medio di VOLCANIC_ROCK
        # e al prezzo di esercizio (strike price) associato    
        # Calcolo del prezzo medio di VOLCANIC_ROCK
        rock_orders = state.order_depths.get('VOLCANIC_ROCK', OrderDepth())
        if rock_orders.buy_orders and rock_orders.sell_orders:
            best_bid = max(rock_orders.buy_orders.keys())
            best_ask = min(rock_orders.sell_orders.keys())
            rock_mid = (best_bid + best_ask) / 2
        else:
            rock_mid = 10300  #in caso non ci siano informazioni di mercato

        # Step 2: Iterazione attraverso ogni voucher e applicazione della logica di arbitraggio
        for voucher, strike in self.voucher_strikes.items():
            orders: List[Order] = []
            order_depth = state.order_depths.get(voucher, OrderDepth())
            position = state.position.get(voucher, 0)
            limit = self.position_limit[voucher]
            legal_buy = max(0, min(limit - position, limit))
            legal_sell = max(0, min(position + limit, limit))

            intrinsic_value = max(0, rock_mid - strike)
            threshold = 0  #minimo edge per agire, cioè differenza tra prezzo di mercato e valore intrinseco. Piu' è basso, piu' è rischioso

            if order_depth.sell_orders:
                best_ask = min(order_depth.sell_orders.keys())
                ask_volume = order_depth.sell_orders[best_ask]
            if best_ask < intrinsic_value - threshold:
                buy_volume = min(-ask_volume, legal_buy)
                if buy_volume > 0:
                    print(f"BUY {buy_volume} {voucher} @ {best_ask} (IV={intrinsic_value})")
                    orders.append(Order(voucher, best_ask, buy_volume))

            if order_depth.buy_orders:
                best_bid = max(order_depth.buy_orders.keys())
                bid_volume = order_depth.buy_orders[best_bid]
                if best_bid > intrinsic_value + threshold:
                    sell_volume = min(bid_volume, legal_sell) 
                    if sell_volume > 0:
                        print(f"SELL {sell_volume} {voucher} @ {best_bid} (IV={intrinsic_value})")
                        orders.append(Order(voucher, best_bid, -sell_volume))

            result[voucher] = orders

        # Step 3: Market making per il sottostante VOLCANIC_ROCK
        rock_position = state.position.get('VOLCANIC_ROCK', 0)
        rock_limit = self.position_limit['VOLCANIC_ROCK']
        legal_buy = max(0, min(rock_limit - rock_position, rock_limit))
        legal_sell = max(0, min(rock_position + rock_limit, rock_limit))
        rock_orders_list: List[Order] = []
        if rock_orders.buy_orders and rock_orders.sell_orders:
            spread = best_ask - best_bid
            if spread >= 1:
                rock_orders_list.append(Order('VOLCANIC_ROCK', best_bid + 1, min(15, legal_buy)))
                rock_orders_list.append(Order('VOLCANIC_ROCK', best_ask - 1, -min(15, legal_sell)))
        result['VOLCANIC_ROCK'] = rock_orders_list

        traderData = ""
        conversions = 1
        return result, conversions, traderData