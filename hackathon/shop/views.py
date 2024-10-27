from django.shortcuts import render
from shop.models import *
from django.db.models import Count,Subquery, Sum
from django.core.paginator import Paginator
from django.db import connection
from django.core.cache import cache

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




def main(request, page_number=0):
    # Извлечение page_number из GET параметров
    page_number = int(request.GET.get('page_number', 0))  # Получаем номер страницы из параметров запроса
    if page_number == 0:
        page_number = 1
    products_per_page = 25

    # Формируем ключ для кэша
    cache_key = f'top_products_page_{page_number}'

    # Попробуем получить данные из кэша
    top_products = cache.get(cache_key)

    if top_products is None:
        # Если данные не в кэше, выполняем запрос
        all_products = (
            ShopOrderproduct.objects
            .values('product_id', 'product__product_name', 'product__price', 'product__department__department')
            .annotate(product_count=Count('product_id'))
            .order_by('-product_count')
        )

        total_products = all_products.count()
        paginator = Paginator(all_products, products_per_page)

        # Получаем продукты для текущей страницы
        top_products = paginator.get_page(page_number)  # Paginator использует 1-базированный индекс

        # Добавляем изображения к продуктам
        for i in top_products:
            i['image'] = i['product__department__department'] + '.jpg'

        # Сохраняем результаты в кэше на 5 минут
        cache.set(cache_key, top_products, 3000)

    # Определяем ссылки на предыдущую и следующую страницы
    previous_page_url = None if not top_products.has_previous() else f"?page_number={top_products.previous_page_number()}"
    next_page_url = None if not top_products.has_next() else f"?page_number={top_products.next_page_number()}"

    # Передаем результат в шаблон
    return render(request, 'main.html', {
        "data": top_products,
        "previous_page_url": previous_page_url,
        "next_page_url": next_page_url,
        "page_number": page_number,
    })




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
            .exclude(product_id=id)  # Исключаем выбранный товар
            .values('product_id', 'product__price', 'product__product_name', 'product__department__department')
            .annotate(
                product_count=Count('product_id'),  # Количество покупок
                product_sum=Sum('add_to_cart_order')  # Общая сумма покупок
            )
            .order_by('-product_count')[:5]  # Берем 5 самых популярных товаров
        )

        # Добавляем изображения к продуктам
        for i in results:
            i['image'] = i['product__department__department'] + '.jpg'

        # Сохраняем результаты в кэше на 5 минут
        cache.set(cache_key, results, 300)

    # Получаем информацию о текущем товаре
    try:
        current_product = ShopProduct.objects.filter(id=id).values('product_name', 'price', 'department__department')[0]
        current_product['image'] = current_product['department__department'] + '.jpg'
    except IndexError:
        current_product = None

    return render(request, 'product1.html', {
        "product": current_product,
        "data": results,
    })