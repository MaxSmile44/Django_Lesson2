import json

from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order
from .models import OrderProduct
from .models import Product


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@api_view(['GET', 'POST'])
def register_order(request):
    data = request.data
    if request.method == 'POST':
        order = Order.objects.create(
            firstname=data['firstname'],
            lastname=data['lastname'],
            phone=data['phonenumber'],
            address=data['address']
        )
        for product in data['products']:
            product_name = Product.objects.get(pk=product['product'])
            OrderProduct.objects.create(order=order, product=product_name, quantity=product['quantity'])
    elif request.method == 'GET':
        orders = Order.objects.prefetch_related('orderproduct_set__product')
        all_orders = []
        for order in orders:
            products = []
            for product in order.orderproduct_set.all():
                products.append({
                    'product': product.product.name,
                    'quantity': product.quantity,
                })
            all_orders.append({
                'firstname': order.firstname,
                'lastname': order.lastname,
                'phone': str(order.phone),
                'address': order.address,
                'products': products,
            })
        return Response(all_orders)
    return Response({})
