import requests

from geopy import distance

import os

from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from dotenv import load_dotenv
from operator import itemgetter, attrgetter, methodcaller

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    try:
        load_dotenv()
        apikey = os.environ['YANDEX_APIKEY']
    except KeyError as error:
        print(f'KeyError: {error}')
    except TypeError as error:
        print(f'TypeError: {error}')

    orders = Order.objects.prefetch_related('products').select_related('restaurant').order_price()
    items = RestaurantMenuItem.objects.select_related('restaurant', 'product').filter(availability=True)

    def fetch_coordinates(apikey, address):
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

    order_menus = {order.id: [product.id for product in order.products.all()] for order in orders}

    try:
        restaurant_menus = {}
        restaurant_coordinates = {}
        for item in items:
            restaurant_name = item.restaurant.name
            coords = fetch_coordinates(apikey, item.restaurant.address)
            coords = (coords[1], coords[0])
            restaurant_coordinates[restaurant_name] = coords
            product_id = item.product.id
            if restaurant_name not in restaurant_menus:
                restaurant_menus[restaurant_name] = []
            restaurant_menus[restaurant_name].append(product_id)

        avalible_restaurants = {}
        for order_key, order_value in order_menus.items():
            avalible_restaurants[order_key] = []
            for restaurant_key, restaurant_value in restaurant_menus.items():
                if all([item in restaurant_value for item in order_value]):
                    avalible_restaurants[order_key].append(restaurant_key)

        avalible_restaurants_with_coords = {}
        for order in orders:
            avalible_restaurants_with_coords[order.id] = []
            for restrant_name in avalible_restaurants[order_key]:
                order_coords = fetch_coordinates(apikey, order.address)
                order_coords = (order_coords[1], order_coords[0])
                restaurant_distance = distance.distance(
                    order_coords,
                    restaurant_coordinates[restrant_name]
                ).km
                avalible_restaurants_with_coords[order.id].append(
                    # f'{restrant_name} - {restaurant_distance:.2f} км'
                    (restrant_name, round(restaurant_distance, 2))
                )
            avalible_restaurants_with_coords[order.id] =(
                sorted(avalible_restaurants_with_coords[order.id], key=itemgetter(1))
            )
            order.restaurant_names_list = avalible_restaurants_with_coords[order.id]
    except requests.exceptions.HTTPError as error:
        print(f'HTTPError: {error}')

    return render(request, template_name='order_items.html', context = {
        'order_items': orders
    })
