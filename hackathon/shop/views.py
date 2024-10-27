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
    # Получаем номер страницы и параметры запроса
    page_number = int(request.GET.get('page_number', 1))
    products_per_page = 25

    # Получаем значения фильтров из GET-запроса
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort_by', 'product_count')

    # Формируем ключ кэша с учетом фильтров
    cache_key = f"top_products_page_{page_number}_search_{search_query}_department_{department_filter}_min_{min_price}_max_{max_price}_sort_{sort_by}"
    top_products = cache.get(cache_key)

    if top_products is None:
        # Базовый запрос на получение продуктов с аннотациями
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

        # Фильтрация по категории (department)
        if department_filter:
            all_products = all_products.filter(product__department__id=department_filter)

        # Фильтрация по ценовому диапазону
        if min_price:
            all_products = all_products.filter(product__price__gte=min_price)
        if max_price:
            all_products = all_products.filter(product__price__lte=max_price)

        # Сортировка
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

        # Кэшируем результаты на 5 минут
        cache.set(cache_key, top_products, 3000)

    # Получаем все категории для фильтрации
    departments = ShopDepartment.objects.all()

    # Определяем ссылки на предыдущую и следующую страницы
    previous_page_url = None if not top_products.has_previous() else f"?page_number={top_products.previous_page_number()}&search={search_query}"
    next_page_url = None if not top_products.has_next() else f"?page_number={top_products.next_page_number()}&search={search_query}"

    # Передаем результат в шаблон
    return render(request, 'main.html', {
        "data": top_products,
        "previous_page_url": previous_page_url,
        "next_page_url": next_page_url,
        "page_number": page_number,
        "search_query": search_query,
        "departments": departments,  # Список категорий для фильтра
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

    # Получаем количество продаж и общую сумму продаж для текущего товара
    sales_info = (
        ShopOrderproduct.objects
        .filter(product_id=id)
        .aggregate(total_sales=Sum('add_to_cart_order'), total_revenue=Sum(F('add_to_cart_order') * F('product__price')))
    )

    # Сбор данных о продажах по дням недели
    # Сбор данных о продажах по дням недели только для данного товара
    sales_data = (
    ShopOrderproduct.objects
    .filter(product_id=id)  # Фильтр по конкретному товару
    .values('order__order_dow')  # Группировка по дням недели
    .annotate(total_sales=Sum('add_to_cart_order'))  # Суммируем количество проданных товаров по дням
    .order_by('order__order_dow')  # Сортировка по дням недели
    )

# Преобразование данных для графика
    days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']  # Дни недели для отображения на графике
    sales_counts = [0] * 7  # Инициализация списка для хранения продаж по каждому дню недели

# Заполняем продажи по дням недели на основе собранных данных
    for entry in sales_data:
        sales_counts[entry['order__order_dow']] = entry['total_sales']  # Записываем продажи по индексу дня недели


    return render(request, 'product1.html', {
        "product": current_product,
        "data": results,
        "sales_counts": sales_counts,  # Передаем данные о продажах в контекст
        "days_of_week": days_of_week,
        "total_sales": sales_info['total_sales'],
        "total_revenue": sales_info['total_revenue'],
    })

def calculate_purchase_recommendations(request):
    # Задайте желаемую прибыль в процентах (например, 0.2 для 20%)
    desired_profit_percentage = float(request.GET.get('desired_profit_percentage', 0.2))

    # Изменяем запрос к базе данных, чтобы включить имя продукта
    sales_data = (
        ShopOrderproduct.objects
        .values('product__product_name')  # Получаем имя продукта
        .annotate(
            total_quantity=Sum('add_to_cart_order'),
            avg_price=Avg('product__price'),
            avg_price_z=Avg('product__price_z'),
            margin=F('avg_price') - F('avg_price_z'),
        )
        [:1000]  # Ограничиваем вывод первыми 1000 строками
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
                'product_name': item['product__product_name'],  # Используем имя продукта
                'total_quantity': item['total_quantity'],
                'margin': item['margin'],
                'popularity': popularity,
                'purchase_recommendation': purchase_recommendation,
            })

    # Сортировка рекомендаций
    sort_by = request.GET.get('sort_by', 'purchase_recommendation')
    recommendations.sort(key=lambda x: x[sort_by], reverse=True)

    # Расчет бюджета закупки с учетом желаемой прибыли
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
    }

    return render(request, 'recommendations.html', context)
