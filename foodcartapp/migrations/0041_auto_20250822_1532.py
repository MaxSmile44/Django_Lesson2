from django.db import migrations
from itertools import chain


def copy_price_to_orderproduct(apps, schema_editor):
    Product = apps.get_model('foodcartapp', 'Product')
    OrderProduct = apps.get_model('foodcartapp', 'OrderProduct')
    orderproducts = OrderProduct.objects.filter(price__isnull=True)
    orderproducts_iterator = orderproducts.iterator()
    products = Product.objects.all().iterator()
    try:
        first_orderproduct = next(orderproducts_iterator)
        first_product = next(products)
    except StopIteration:
        pass
    else:
        for product in chain([first_product], products):
            orderproducts.filter(product_id=product.id).update(price=product.price)


def clear_price_in_orderproduct(apps, schema_editor):
    OrderProduct = apps.get_model('foodcartapp', 'OrderProduct')
    orderproducts = OrderProduct.objects.filter(price__isnull=False)
    orderproducts_iterator = orderproducts.iterator()
    try:
        first_orderproduct = next(orderproducts_iterator)
    except StopIteration:
        pass
    else:
        orderproducts.update(price=None)


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0040_orderproduct_price'),
    ]

    operations = [
        migrations.RunPython(copy_price_to_orderproduct, clear_price_in_orderproduct),
    ]
