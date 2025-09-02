import json
import phonenumbers

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework import status, serializers
from rest_framework.decorators import api_view
from rest_framework.serializers import ModelSerializer, ValidationError
from rest_framework.response import Response

from .models import Order, OrderProduct, Product


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


class OrderProductSerializer(ModelSerializer):
    product = serializers.IntegerField()

    class Meta:
        model = OrderProduct
        fields = ['product', 'quantity']


class OrderSerializer(ModelSerializer):
    products = OrderProductSerializer(many=True, allow_empty=False, write_only=True)
    phonenumber = serializers.CharField(source='phone')

    class Meta:
        model = Order
        fields = ['firstname', 'lastname', 'phonenumber', 'address', 'products']

    def validate_phonenumber(self, value):
        phone = phonenumbers.parse(value, 'RU')
        if not phonenumbers.is_valid_number(phone):
            raise ValidationError([f"Invalid phonenumber: {value}"])
        return value


@api_view(['GET', 'POST'])
def register_order(request):
    try:
        with transaction.atomic():
            if request.method == 'GET':
                serializer = OrderSerializer(Order.objects.all(), many=True)
                return Response(serializer.data)
            elif request.method == 'POST':
                serializer = OrderSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)

                order = Order.objects.create(
                    firstname=serializer.validated_data['firstname'],
                    lastname=serializer.validated_data['lastname'],
                    phone=serializer.validated_data['phone'],
                    address=serializer.validated_data['address']
                )
                products_ids = [product['product'] for product in serializer.validated_data['products']]
                products = Product.objects.filter(pk__in=products_ids)
                product_map = {product.pk: product for product in products}
                for product in serializer.validated_data['products']:
                    product_obj = product_map.get(product['product'])
                    OrderProduct.objects.create(order=order, product=product_obj, quantity=product['quantity'], price=product_obj.price)

                content = {'New order added': serializer.validated_data}
                return Response(content)

    except ObjectDoesNotExist as error:
        return Response(f'{error}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except TypeError as error:
        return Response(f'{error}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except KeyError as error:
        return Response(f'{error}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except ValueError as error:
        return Response(f'{error}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except AttributeError as error:
        return Response(f'{error}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
