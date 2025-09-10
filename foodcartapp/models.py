import requests

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum, F, ForeignKey
from phonenumber_field.modelfields import PhoneNumberField


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True
    )
    lat = models.FloatField(
        'Координаты: широта',
        blank=True,
        null=True
    )
    lon = models.FloatField(
        'Координаты: долгота',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name

    def fetch_coordinates(self, address):
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


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class OrderQuerySet(models.QuerySet):
    def order_price(self):
        orders = self.annotate(order_price=Sum(F('orderproduct__price') * F('orderproduct__quantity')))
        return orders


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='ресторан',
        related_name='menu_items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        verbose_name='продукт',
        related_name='menu_items',
        on_delete=models.CASCADE
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f'{self.restaurant.name} - {self.product.name}'


class Order(models.Model):
    Raw = 'Необработанный'
    Cooking = 'Готовится'
    Transport = 'В пути'
    Completed = 'Завершен'
    ORDER_STATUS_CHOICES = [
        (Raw, 'Необработанный'),
        (Cooking, 'Готовится'),
        (Transport, 'В пути'),
        (Completed, 'Завершен')
    ]
    Cash = 'Наличностью'
    Electronic = 'Электронно'
    PAYMENT_CHOICES = [
        (Cash, 'Наличностью'),
        (Electronic, 'Электронно')
    ]
    firstname = models.CharField(
        'имя клиента',
        max_length=25
    )
    lastname = models.CharField(
        'фамилия клиента',
        max_length=25
    )
    phone = PhoneNumberField(
        'телефон клиента',
        region='RU'
    )
    address = models.CharField(
        'адрес клиента',
        max_length=100
    )
    products = models.ManyToManyField(
        Product,
        related_name='products',
        through='OrderProduct'
    )
    status = models.CharField(
        'статус заказа',
        max_length=25,
        choices=ORDER_STATUS_CHOICES,
        default=Raw,
        db_index=True
    )
    comment = models.CharField(
        'комментарий к заказу',
        max_length=200,
        blank=True
    )
    order_date = models.DateTimeField(
        'дата и время регистрации заказа',
        auto_now_add=True,
        db_index=True
    )
    call_date = models.DateTimeField(
        'дата и время звонка',
        null=True,
        blank=True,
        db_index=True
    )
    delivery_date = models.DateTimeField(
        'дата и время доставки',
        null=True,
        blank=True,
        db_index=True
    )
    payment = models.CharField(
        'способ оплаты',
        max_length=25,
        choices=PAYMENT_CHOICES,
        default=Electronic,
        db_index=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='ресторан',
        related_name='orders',
        null=True,
        on_delete=models.SET_NULL
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.firstname} {self.lastname} {self.address}'


class OrderProduct(models.Model):
    order = ForeignKey(
        Order,
        verbose_name='заказ',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        verbose_name='товар',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveSmallIntegerField(
        'количество',
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'элемент заказа'
        verbose_name_plural = 'элементы заказа'

    def __str__(self):
        return f'{self.product.name} {self.order}'
