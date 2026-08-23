"""
AuraTool-Suite — E-Commerce & Workshop Store Module
=====================================================
Manages spare part purchasing, license upgrades, and technician service subscriptions.
"""

import logging
import uuid


class StoreItem:
    def __init__(self, item_id: str, name: str, category: str, price: float, stock: int):
        self.item_id = item_id
        self.name = name
        self.category = category
        self.price = price
        self.stock = stock


class ECommerceManager:
    """In-app e-commerce store engine."""

    CATALOGUE = [
        StoreItem("PART-LCD-S23", "Samsung Galaxy S23 AMOLED Display", "Screens", 189.99, 15),
        StoreItem("PART-BAT-IP15", "iPhone 15 Pro Battery Unit", "Batteries", 45.00, 30),
        StoreItem("LIC-6M-PRO", "6-Month Professional Plan Extension", "Licenses", 149.00, 999),
        StoreItem("LIC-1Y-VIP", "1-Year VIP Ultimate 2030 Subscription", "Licenses", 249.00, 999),
        StoreItem("TOOL-EDL-CABLE", "Multi-Boot EDL / BROM Auto-Switch Cable", "Tools", 29.99, 50),
    ]

    def __init__(self):
        self.logger = logging.getLogger("AuraTool.ECommerce")
        self.cart = []
        self.orders = []

    def get_catalogue(self) -> list[dict]:
        return [
            {
                "id": item.item_id,
                "name": item.name,
                "category": item.category,
                "price": item.price,
                "stock": item.stock,
            }
            for item in self.CATALOGUE
        ]

    def add_to_cart(self, item_id: str, quantity: int = 1) -> bool:
        for item in self.CATALOGUE:
            if item.item_id == item_id:
                self.cart.append({"item": item, "quantity": quantity})
                self.logger.info(f"Added {quantity}x '{item.name}' to shopping cart.")
                return True
        return False

    def checkout(self, payment_method: str = "CreditCard") -> dict:
        if not self.cart:
            return {"status": "EMPTY_CART", "total": 0.0}

        total = sum(entry["item"].price * entry["quantity"] for entry in self.cart)
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        order = {
            "order_id": order_id,
            "total_amount": round(total, 2),
            "payment_method": payment_method,
            "items_count": len(self.cart),
            "status": "COMPLETED",
        }
        self.orders.append(order)
        self.logger.info(f"Checkout completed. Order #{order_id} total: ${total:.2f}")
        self.cart.clear()
        return order
