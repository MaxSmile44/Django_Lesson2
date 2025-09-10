import phonenumbers
import requests

from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, ValidationError
from .models import Order, OrderProduct, Product
from coordinates.models import Coordinate


class OrderProductSerializer(ModelSerializer):
    product = serializers.IntegerField()

    class Meta:
        model = OrderProduct
        fields = ['product', 'quantity']

    def validate_product(self, value):
        if not Product.objects.filter(id=value).exists():
            raise ValidationError(f'Продукт с id={value} не существует')
        return value


class OrderSerializer(ModelSerializer):
    products = OrderProductSerializer(many=True, allow_empty=False, write_only=True)

    class Meta:
        model = Order
        fields = ['firstname', 'lastname', 'phonenumber', 'address', 'products']

    def validate_phonenumber(self, value):
        phone = phonenumbers.parse(value, 'RU')
        if not phonenumbers.is_valid_number(phone):
            raise ValidationError([f"Invalid phonenumber: {value}"])
        return value

    def create(self, validated_data):
        order = Order.objects.create(
            firstname=validated_data['firstname'],
            lastname=validated_data['lastname'],
            phonenumber=validated_data['phonenumber'],
            address=validated_data['address']
        )

        coordinates = Coordinate.objects.all()
        order_addresses = [coordinate.address for coordinate in coordinates]

        if validated_data['address'] not in order_addresses:
            def fetch_coordinates(address):
                apikey = settings.YANDEX_APIKEY
                try:
                    base_url = "https://geocode-maps.yandex.ru/1.x"
                    response = requests.get(base_url, params={
                        "geocode": address,
                        "apikey": apikey,
                        "format": "json",
                    })
                    response.raise_for_status()
                    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

                    if not found_places:
                        return None

                    most_relevant = found_places[0]
                    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
                    return lon, lat
                except requests.exceptions.HTTPError as error:
                    print(f'HTTPError: {error}')
                    return None

            lon, lat = fetch_coordinates(validated_data['address'])
            coordinates.create(
                address=validated_data['address'],
                lon=lon,
                lat=lat
            )

        products_ids = [product['product'] for product in validated_data['products']]
        products = Product.objects.filter(pk__in=products_ids)
        product_map = {product.pk: product for product in products}
        for product in validated_data['products']:
            product_obj = product_map.get(product['product'])
            OrderProduct.objects.create(
                order=order,
                product=product_obj,
                quantity=product['quantity'],
                price=product_obj.price
            )
        return order
