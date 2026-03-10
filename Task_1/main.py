from fastapi import FastAPI, Query
 
app = FastAPI()
 
# ── Temporary data — acting as our database for now ──────────
products = [
    {'id': 1, 'name': 'Wireless Mouse', 'price': 499,  'category': 'Electronics', 'in_stock': True },
    {'id': 2, 'name': 'Notebook',       'price':  99,  'category': 'Stationery',  'in_stock': True },
    {'id': 3, 'name': 'USB Hub',         'price': 799, 'category': 'Electronics', 'in_stock': False},
    {'id': 4, 'name': 'Pen Set',          'price':  49, 'category': 'Stationery',  'in_stock': True },
    {'id': 5, 'name' : 'Laptop Stand',    'price': 399, 'category':'Electronics', 'in_stock': True},
    {'id': 6, 'name' : 'Mechanical Keyboard','price': 899, 'category':'Electronics', 'in_stock': True},
    {'id': 7, 'name' : 'Webcam',    'price': 299, 'category':'Electronics', 'in_stock': False},
]
 
# ── Endpoint 0 — Home ────────────────────────────────────────
@app.get('/')
def home():
    return {'message': 'Welcome to our E-commerce API'}
 
# ── Endpoint 1 — Return all products ──────────────────────────
@app.get('/products')
def get_all_products():
    return {'products': products, 'total': len(products)}

@app.get('/products/filter')
def filter_products(
    category:  str  = Query(None, description='Electronics or Stationery'),
    max_price: int  = Query(None, description='Maximum price'),
    in_stock:  bool = Query(None, description='True = in stock only')
):
    result = products          # start with all products
 
    if category:
        result = [p for p in result if p['category'] == category]
 
    if max_price:
        result = [p for p in result if p['price'] <= max_price]
 
    if in_stock is not None:
        result = [p for p in result if p['in_stock'] == in_stock]
 
    return {'filtered_products': result, 'count': len(result)}


# Return products by category
@app.get('/products/category/{category_name}')
def get_products_category(category_name: str):

    result = [p for p in products if p['category'].lower() == category_name.lower()]

    if result:
        return {'products': result, 'count': len(result)}

    return {'message': 'No products found in this category'}

#---Endpoint for instock items----
@app.get('/products/instock')
def in_stock_items():
    result = [p for p in products if p['in_stock'] == True]
    return {"in_stock_products" : result , 'count' : len(result)}

#----Endpoint for store info----
@app.get('/store/summary')
def store_info():
    product_counts = len(products)
    instock_products = [p for p in products if p['in_stock'] == True]
    out_of_stock_products = [p for p in products if p['in_stock'] == False]
    category_wise_products = list(set([p["category"] for p in products])) 

    return {"store_name": "My E-commerce Store", "total_products": product_counts, "in_stock": len(instock_products), "out_of_stock": len(out_of_stock_products), "categories": category_wise_products}

#--product search Endpoint---
@app.get('/products/search/{keyword}')
def search_product(keyword: str):
    result = [p for p in products if keyword.lower() in p['name'].lower()]

    if result:
        return {'Products' : result , 'Count': len(result)}
    else:
        return {"message": "No products matched your search"}

#--Endpoint for best deals and premium
@app.get("/products/deals")
def get_deals():
    cheapest = min(products, key=lambda p: p["price"]) 
    expensive = max(products, key=lambda p: p["price"]) 
    
    return { "best_deal": cheapest, "premium_pick": expensive, }

 
# ── Endpoint 2 — Return one product by its ID ──────────────────
@app.get('/products/{product_id}')
def get_product(product_id: int):
    for product in products:
        if product['id'] == product_id:
            return {'product': product}
    return {'error': 'Product not found'}

