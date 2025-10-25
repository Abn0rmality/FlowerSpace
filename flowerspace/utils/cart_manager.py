from onlineshop.models import Product
from abc import ABC, abstractmethod
from django.core.cache import cache
from django.core.exceptions import ValidationError


""" ---------- CONFIG VARIABLES ---------- """
SESSION_CART_ID = "cart"
CACHE_CART_ID = "cart"
AUTO_CART_SAVE = True # if enabled , you don't have to manually call the cart manager to save your cart.
""" ---------- **************** ---------- """


class Cart:
    """
    Internal structure:
    {
        "user_id": "1",
        "items": {
            "15": {"price": 9.99, "quantity": 2},
            ...
        }
    }
    """

    def __init__(self, user_id: str | None = None, products: dict | None = None, manager: object = None):
        # if products came from get_data(), convert its list back to a dict
        items = {}
        if products and isinstance(products.get("items"), list):
            for entry in products["items"]:
                pid = str(entry["product"]["id"])
                items[pid] = {
                    "price": float(entry["product"]["price"]),
                    "quantity": entry["quantity"],
                }
        elif products and isinstance(products.get("items"), dict):
            items = products["items"]

        self.user_id = user_id
        self.cart = {"user_id": user_id, "items": items}
        self._manager = manager # needs to be one of the managers below

    # ---------- Core ops ----------

    def _auto_save(self):
        if AUTO_CART_SAVE and self._manager:
            self._manager.save_cart(self)

    def add(self, product: Product, quantity: int = 1):
        pid = str(product.id)
        user_cart_items = self.cart["items"]
        if pid not in user_cart_items:
            user_cart_items[pid] = {
                "price": float(product.price),
                "quantity": 0,
            }
        user_cart_items[pid]["quantity"] += quantity
        self._auto_save()

    def delete(self, product_id: int):
        pid = str(product_id)
        items = self.cart["items"]
        if pid in items:
            if items[pid]["quantity"] > 1:
                items[pid]["quantity"] -= 1
            else:
                del items[pid]
        self._auto_save()

    # ---------- Derived ----------

    def items(self):
        # collect IDs once
        ids = list(self.cart["items"].keys())
        products = Product.objects.in_bulk(ids)
        for pid, info in self.cart["items"].items():
            product = products.get(int(pid))
            if not product:
                continue  # product deleted or missing
            price = product.get_discount_price() if product.discount else product.price
            yield {
                "product": product,
                "quantity": info["quantity"],
                "price": price,
                "total_price": price * info["quantity"],
            }

    def get_total_price(self) -> float:
        return sum(item["total_price"] for item in self.items())

    def get_total_quantity(self) -> int:
        return sum(item["quantity"] for item in self.items())

    def get_data(self) -> dict:
        return {
            "user_id": self.user_id,
            "items": [
                {
                    "product": {
                        "id": item["product"].id,
                        "title": item["product"].title,
                        "image": item["product"].image.url if item["product"].image else "",
                        "price": item["price"],
                    },
                    "instance": item["product"],
                    "quantity": item["quantity"],
                }
                for item in self.items()
            ],
            "total_price": self.get_total_price(),
            "total_quantity": self.get_total_quantity(),
        }



class AbstractCartManager(ABC):
    @abstractmethod
    def load_cart(self) -> Cart: ...
    @abstractmethod
    def save_cart(self, cart: Cart) -> None: ...
    @abstractmethod
    def clear(self): ...


class SessionCartManager(AbstractCartManager):
    def __init__(self, request):
        self.session = request.session
        self.user_id = str(request.user.id)

    def load_cart(self) -> Cart:
        data = self.session.get(SESSION_CART_ID)
        return Cart(self.user_id, products=data if data else None, manager=self)

    def save_cart(self, cart: Cart) -> None:
        # Store only the raw dict for serialization
        self.session[SESSION_CART_ID] = cart.get_data()
        self.session.modified = True

    def clear(self):
        if SESSION_CART_ID in self.session:
            del self.session[SESSION_CART_ID]
            self.session.modified = True


class CacheCartManager(AbstractCartManager):
    """
    This Manager can only work for users who have logged in and submitted a cart request
    """
    def __init__(self, request):
        self.user_id = str(request.user.id)
        if not request.user.is_authenticated:
            raise ValidationError("You cannot use cache cart manager when the user is anonymous.")
        self.user_cart_key = f"user:{self.user_id}:cart"

    def load_cart(self) -> Cart:
        data = cache.get(self.user_cart_key)
        return Cart(self.user_id, products=data if data else None, manager=self)

    def save_cart(self, cart: Cart) -> None:
        cache.set(self.user_cart_key, cart.get_data(), 60 * 60 * 24) # one day

    def clear(self):
        cache.delete(self.user_cart_key)

class HybridCartManager(AbstractCartManager):
    def __init__(self, request):
        self.session_manager = SessionCartManager(request)
        self.authenticated = request.user.is_authenticated
        self.cache_manager = CacheCartManager(request) if self.authenticated else None

    @staticmethod
    def merge_carts(session_cart: Cart, cache_cart: Cart) -> Cart:
        merged = Cart(user_id=session_cart.user_id)
        for src in (session_cart, cache_cart):
            for pid, info in src.cart["items"].items():
                if pid in merged.cart["items"]:
                    merged.cart["items"][pid]["quantity"] += info["quantity"]
                    merged.cart["items"][pid]["price"] = info["price"]  # always overwrite
                else:
                    merged.cart["items"][pid] = {"price": info["price"], "quantity": info["quantity"]}
        return merged

    def load_cart(self) -> Cart:
        # guests: session only
        if not self.authenticated:
            return self.session_manager.load_cart()
        # logged-in: cache is the single source of truth
        return self.cache_manager.load_cart()

    def save_cart(self, cart: Cart) -> None:
        if self.authenticated:
            self.cache_manager.save_cart(cart)
        else:
            self.session_manager.save_cart(cart)

    def clear(self) -> None:
        if self.authenticated:
            self.cache_manager.clear()
        else:
            self.session_manager.clear()



# This function runs when user logs in and merges the carts. newest price wins
def merge_session_into_cache(request):
    if not request.user.is_authenticated:
        return
    session_cart = SessionCartManager(request).load_cart()
    cache_cart = CacheCartManager(request).load_cart()

    if session_cart.get_total_quantity():
        merged = HybridCartManager.merge_carts(session_cart, cache_cart)
        CacheCartManager(request).save_cart(merged)
        SessionCartManager(request).save_cart(merged)
        SessionCartManager(request).clear()
        print("Cart merged successfully!")
