from django.shortcuts import render
from shop.models import *
from django.db.models import Count,Subquery, Sum
from django.core.paginator import Paginator
from django.db import connection
from django.core.cache import cache
from django.db.models import Sum, Avg, F

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




from django.db.models import Q

from django.shortcuts import render
from django.db.models import Q, Count, F
from django.core.cache import cache
from django.core.paginator import Paginator
from .models import ShopOrderproduct, ShopDepartment

def main(request, page_number=0):
    
    page_number = int(request.GET.get('page_number', 1))
    products_per_page = 25

    
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort_by', 'product_count')

    # Формируем ключ кэша с учетом фильтров
    cache_key = f"top_products_page_{page_number}_search_{search_query}_department_{department_filter}_min_{min_price}_max_{max_price}_sort_{sort_by}"
    top_products = cache.get(cache_key)

    if top_products is None:
        all_products = (
            ShopOrderproduct.objects
            .values('product_id', 'product__product_name', 'product__price', 'product__department__department')
            .annotate(
                product_count=Sum('add_to_cart_order'),
                margin=F('product__price') - F('product__price_z')
            )
        )

        # Фильтрация по поисковому запросу
        if search_query:
            all_products = all_products.filter(Q(product__product_name__icontains=search_query))

        
        if department_filter:
            all_products = all_products.filter(product__department__id=department_filter)

        
        if min_price:
            all_products = all_products.filter(product__price__gte=min_price)
        if max_price:
            all_products = all_products.filter(product__price__lte=max_price)

      
        if sort_by == 'product_count':
            all_products = all_products.order_by('-product_count')
        elif sort_by == 'margin':
            all_products = all_products.order_by('-margin')

        # Пагинация
        paginator = Paginator(all_products, products_per_page)
        top_products = paginator.get_page(page_number)

        # Добавляем изображения к продуктам
        for i in top_products:
            department = i['product__department__department']
            i['image'] = f"{department}.jpg"  # Путь к изображению

        # Кэшируем результаты на 50 минут
        cache.set(cache_key, top_products, 3000)

    # Получаем все категории для фильтрации
    departments = ShopDepartment.objects.all()

    
    previous_page_url = None if not top_products.has_previous() else f"?page_number={top_products.previous_page_number()}&search={search_query}"
    next_page_url = None if not top_products.has_next() else f"?page_number={top_products.next_page_number()}&search={search_query}"

    
    return render(request, 'main.html', {
        "data": top_products,
        "previous_page_url": previous_page_url,
        "next_page_url": next_page_url,
        "page_number": page_number,
        "search_query": search_query,
        "departments": departments,  
        "department_filter": department_filter,
        "min_price": min_price,
        "max_price": max_price,
        "sort_by": sort_by,
    })




from django.db.models import Count, Sum

def product1(request, id):
    # Формируем ключ для кэша
    cache_key = f'product1_recommendations_{id}'

    # Попробуем получить данные из кэша
    results = cache.get(cache_key)

    if results is None:
        # Если данные не в кэше, выполняем запрос
        results = (
            ShopOrderproduct.objects
            .filter(order__in=ShopOrderproduct.objects.filter(product_id=id).values('order'))  # Заказы с выбранным товаром
            .exclude(product_id=id)  
            .values('product_id', 'product__price', 'product__product_name', 'product__department__department')
            .annotate(
                product_count=Count('product_id'),  
                product_sum=Sum('add_to_cart_order')  
            )
            .order_by('-product_count')[:5]  
        )

       
        for i in results:
            i['image'] = i['product__department__department'] + '.jpg'

        cache.set(cache_key, results, 3000)

    
    try:
        current_product = ShopProduct.objects.filter(id=id).values('product_name', 'price', 'department__department')[0]
        current_product['image'] = current_product['department__department'] + '.jpg'
    except IndexError:
        current_product = None


    sales_info = (
        ShopOrderproduct.objects
        .filter(product_id=id)
        .aggregate(total_sales=Sum('add_to_cart_order'), total_revenue=Sum(F('add_to_cart_order') * F('product__price')))
    )

    sales_data = (
    ShopOrderproduct.objects
    .filter(product_id=id)  
    .values('order__order_dow')  
    .annotate(total_sales=Sum('add_to_cart_order'))  
    .order_by('order__order_dow')  
    )


    days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']  
    sales_counts = [0] * 7  

    for entry in sales_data:
        sales_counts[entry['order__order_dow']] = entry['total_sales']  


    return render(request, 'product1.html', {
        "product": current_product,
        "data": results,
        "sales_counts": sales_counts,  
        "days_of_week": days_of_week,
        "total_sales": sales_info['total_sales'],
        "total_revenue": sales_info['total_revenue'],
    })

from django.db.models import Sum, F, Avg

def calculate_purchase_recommendations(request):
    desired_profit_percentage = float(request.GET.get('desired_profit_percentage', 0.2))

    
    sales_data = (
        ShopOrderproduct.objects
        .values('product__product_name')
        .annotate(
            total_quantity=Sum('add_to_cart_order'),
            avg_price=Avg('product__price'),
            avg_price_z=Avg('product__price_z'),
            margin=F('avg_price') - F('avg_price_z'),
        )
        [:1000]
    )

    # Собираем данные по категориям
    category_sales = (
        ShopOrderproduct.objects
        .values('product__department__department')
        .annotate(category_quantity=Sum('add_to_cart_order'))
        .order_by('product__department__department')
    )

    total_quantity_sum = sales_data.aggregate(total=Sum('total_quantity'))['total']
    total_profit = 0
    recommendations = []

    for item in sales_data:
        if total_quantity_sum > 0:
            popularity = item['total_quantity'] / total_quantity_sum
            purchase_recommendation = item['margin'] * popularity * item['total_quantity']
            total_profit += item['margin'] * item['total_quantity']

            recommendations.append({
                'product_name': item['product__product_name'],
                'total_quantity': item['total_quantity'],
                'margin': item['margin'],
                'popularity': popularity,
                'purchase_recommendation': purchase_recommendation,
            })

    sort_by = request.GET.get('sort_by', 'purchase_recommendation')
    recommendations.sort(key=lambda x: x[sort_by], reverse=True)

    purchase_budget = total_profit * (1 - desired_profit_percentage)
    total_spent = 0
    final_recommendations = []

    for recommendation in recommendations:
        product_cost = recommendation['margin'] * recommendation['purchase_recommendation'] / recommendation['total_quantity']
        if total_spent + product_cost <= purchase_budget:
            recommendation['needed_quantity'] = round(recommendation['purchase_recommendation'] / recommendation['margin'])
            final_recommendations.append(recommendation)
            total_spent += product_cost
        else:
            break

    context = {
        'total_profit': total_profit,
        'purchase_budget': purchase_budget,
        'recommendations': final_recommendations,
        'desired_profit_percentage': desired_profit_percentage,
        'category_sales': list(category_sales),  # Данные для круговой диаграммы
    }

    return render(request, 'recommendations.html', context)
