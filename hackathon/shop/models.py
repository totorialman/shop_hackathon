from django.db import models

class ShopDepartment(models.Model):
    id = models.BigAutoField(primary_key=True)
    department = models.CharField(max_length=100)

    class Meta:
        db_table = 'shop_department'


class ShopOrder(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField()
    order_dow = models.IntegerField()
    order_hour_of_day = models.IntegerField()
    eval_set = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'shop_order'


class ShopOrderproduct(models.Model):
    id = models.BigAutoField(primary_key=True)
    add_to_cart_order = models.IntegerField()
    order = models.ForeignKey(ShopOrder, models.DO_NOTHING)
    product = models.ForeignKey('ShopProduct', models.DO_NOTHING)

    class Meta:
        db_table = 'shop_order_product'


class ShopProduct(models.Model):
    id = models.BigAutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    price = models.IntegerField()
    department = models.ForeignKey(ShopDepartment, models.DO_NOTHING)
    price_z = models.IntegerField()

    class Meta:
        db_table = 'shop_product'