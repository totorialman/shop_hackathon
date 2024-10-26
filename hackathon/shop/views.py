from django.shortcuts import render

from django.db import connection

def get_frequently_bought_together(product_id):
    query = f"""
    SELECT o2.product_id, COUNT(*) as product_count, SUM(o2.add_to_cart_order) as product_sum
    FROM shop_orderproduct o1 
    INNER JOIN shop_orderproduct o2 
    ON o1.order_id = o2.order_id 
    WHERE o1.product_id = {product_id} AND o2.product_id != {product_id}
    GROUP BY o2.product_id 
    ORDER BY product_count DESC 
    LIMIT 10;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return result

def main(request):
    
    return render(request, 'main.html')

def product1(request):

    return render(request, 'product1.html')