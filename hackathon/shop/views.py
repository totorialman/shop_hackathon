from django.shortcuts import render
from shop.models import *
from django.db.models import Count,Subquery
from django.core.paginator import Paginator
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

def main(request, page_number=1):
    print("STARTED")
    
    # Получаем список уникальных product_id из ShopOrderproduct, отсортированных по количеству покупок
    unique_products = ShopOrderproduct.objects.select_related('product') \
                      .values('product_id') \
                      .annotate(purchase_count=Count('product_id')) \
                      .order_by('-purchase_count')
    
    # Используем Subquery, чтобы избежать промежуточного списка, передавая подзапрос напрямую
    products = ShopProduct.objects.filter(id__in=Subquery(unique_products.values('product_id'))) \
                .select_related('department') \
                .order_by('product_name')

    print("TWO QUERY")
    
    p = Paginator(products, 25)
    data = p.get_page(10)
    # Передаем результат в шаблон
    return render(request, 'main.html', {
        "data": data
    })
    

def product1(request):
    return render(request, 'product1.html')