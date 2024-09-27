import requests
import json
import time
import threading

# Load configuration settings from settings.json
settings = json.load(open("settings.json", "r"))
item_ids = settings["items"]  # Extract item IDs and prices
cookies = settings["cookies"]  # List of cookies
watch_speed = settings["watch_speed"]

# Initialize session and cookie index
session = requests.session()
cookie_index = 0  # Start with the first cookie

token = None
payload = [{ "itemType": "Asset", "id": id } for id in item_ids]
cache = []

checks = 0

# Create a dictionary to track items that have been warned and bought
item_warnings = {}

def refresh_tokens():
    while True:
        _set_auth()
        time.sleep(150)

def _set_auth():
    global token, session, cookie_index
    try:
        # Set the current cookie
        session.cookies['.ROBLOSECURITY'] = cookies[cookie_index]

        conn = session.post("https://auth.roblox.com/v2/logout")
        if conn.headers.get("x-csrf-token"):
            token = conn.headers["x-csrf-token"]
    except Exception as e:
        print(f"Error in setting auth: {e}")
        time.sleep(5)
        return _set_auth()

def get_product_id(id):
    try:
        conn = session.get(f"https://economy.roblox.com/v2/assets/{id}/details")
        data = conn.json()

        if conn.status_code == 200:
            return {
                "id": data["ProductId"],
                "creator": data["Creator"]["Id"]
            }
        else:
            time.sleep(1)
            return get_product_id(id)
    except Exception as e:
        print(f"Error getting product ID: {e}")
        time.sleep(1)
        return get_product_id(id)

def buy_item(product_id, seller_id, price):
    global logs

    try:
        body = {
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedSellerId": seller_id
        }
        headers = {
            "x-csrf-token": token,
        }
        conn = session.post(f"https://economy.roblox.com/v1/purchases/products/{product_id}", headers=headers, json=body)
        data = conn.json()
        if conn.status_code == 200:
            print("Bought")
        else:
            print(f"Failed to buy: {data}")
    except Exception as e:
        print(f"Error buying item: {e}")

def watcher():
    global token, session, checks, logs, cookie_index
    while True:
        try:
            headers = {
                "x-csrf-token": token,
                "cache-control": "no-cache",
                "pragma": "no-cache",
            }
            conn = session.post("https://catalog.roblox.com/v1/catalog/items/details", json={ "items": payload }, headers=headers)

            data = conn.json()
            if conn.status_code == 200:
                checks += 1
                if "data" in data:
                    for item in data["data"]:
                        item_id = item['id']
                        item_name = item['name']

                        if "price" in item and not item_id in cache:
                            purchase_price = item_ids.get(str(item_id))
                            if purchase_price is not None:
                                if item["price"] <= purchase_price:
                                    cache.append(item_id)
                                    r_data = get_product_id(item_id)
                                    price = item["price"]
                                    buy_item(r_data["id"], r_data["creator"], price)
            elif conn.status_code == 403:
                _set_auth()
            else:
                print(f"Error in watcher response: {data}")

            # Rotate cookie index
            cookie_index = (cookie_index + 1) % len(cookies)
        except Exception as error:
            print(f"Error in watcher: {error}")
        time.sleep(watch_speed)

if __name__ == '__main__':
    threading.Thread(target=refresh_tokens).start()
    while token is None:
        time.sleep(1)
    threading.Thread(target=watcher).start()
