from typing import Dict, List
from datamodel import Order, OrderDepth, TradingState
import numpy as np

class Trader:
    def __init__(self):
        self.product = 'MAGNIFICENT_MACARONS'
        self.position_limit = {self.product: 75}

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}
        product = self.product
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
        return result, 1, ""
