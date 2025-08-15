import json

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order
from .models import OrderProduct
from .models import Product
import phonenumbers

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
    try:
        data = request.data
        if request.method == 'POST':

            if not isinstance(data, dict):
                return Response('Non-json format sent', status=status.HTTP_400_BAD_REQUEST)

            def find_empty_or_null_keys(data):
                empty_or_null_keys = []
                for key, value in data.items():
                    if not value or value is None:
                        empty_or_null_keys.append(key)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                empty_or_null_keys.extend(find_empty_or_null_keys(item))
                    elif isinstance(value, dict):
                        empty_or_null_keys.extend(find_empty_or_null_keys(value))
                return empty_or_null_keys

            empty_or_null_keys = find_empty_or_null_keys(data)

            if empty_or_null_keys:
                return Response(f'Empty or NoneType keys: {empty_or_null_keys}', status=status.HTTP_400_BAD_REQUEST)

            expected_types = {
                'products': list,
                'firstname': str,
                'lastname': str,
                'phonenumber': str,
                'address': str
            }
            missing_keys, wrong_types = [], []

            for key, expected_type in expected_types.items():
                if key in data:
                    if not isinstance(data[key], expected_type):
                        wrong_types.append(
                            f"Key '{key}' is expected to be of type {expected_type.__name__}, "
                            f"but it is of type {type(data[key]).__name__}"
                        )
                else:
                    missing_keys.append(key)

            if 'products' not in missing_keys:
                if isinstance(data['products'], list):
                    for item in data.get('products'):
                        if not isinstance(item, dict):
                            wrong_types.append(
                                f"In list of key 'products' is expected to be of type dict, "
                                f"but it is of type {type(item).__name__}"
                            )
                        else:
                            if not isinstance(item.get('product'), int):
                                wrong_types.append(
                                    f"Key 'product' is expected to be of type int, "
                                    f"but it is of type {type(item.get('product')).__name__}"
                                )
                            if not isinstance(item.get('quantity'), int):
                                wrong_types.append(
                                    f"Key 'quantity' is expected to be of type int, "
                                    f"but it is of type {type(item.get('quantity')).__name__}"
                                )

            if missing_keys and wrong_types:
                return Response(f'Missing keys: {missing_keys}, {wrong_types}', status=status.HTTP_400_BAD_REQUEST)
            elif missing_keys:
                return Response({'Missing keys': missing_keys}, status=status.HTTP_400_BAD_REQUEST)
            elif wrong_types:
                return Response(wrong_types, status=status.HTTP_400_BAD_REQUEST)

            phone = phonenumbers.parse(data['phonenumber'], 'RU')
            if not phonenumbers.is_valid_number(phone):
                return Response({'Invalid phonenumber': data['phonenumber']}, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(
                firstname=data['firstname'],
                lastname=data['lastname'],
                phone=data['phonenumber'],
                address=data['address']
            )
            for product in data['products']:
                product_name = Product.objects.get(pk=product['product'])
                OrderProduct.objects.create(order=order, product=product_name, quantity=product['quantity'])

            content = {'New order added': data}
            return Response(content, status=status.HTTP_200_OK)
        else:
            return Response({})
    except ObjectDoesNotExist as error:
        return Response(f'{error}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

