from geopy import distance

from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from operator import itemgetter

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem
from coordinates.models import Coordinate


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
    orders = Order.objects.prefetch_related('products').select_related('restaurant').order_price()
    items = RestaurantMenuItem.objects.select_related('restaurant', 'product').filter(availability=True)
    coordinates = Coordinate.objects.all()

    addresses_with_coords = {coordinate.address: [coordinate.lat, coordinate.lon] for coordinate in coordinates}

    order_menus = {order.id: [product.id for product in order.products.all()] for order in orders}

    restaurant_menus = {}
    restaurant_coordinates = {}
    for item in items:
        restaurant_name = item.restaurant.name
        coords = (item.restaurant.lat, item.restaurant.lon)
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

    avalible_restaurants_with_distance = {}
    for order in orders:
        if order.address in addresses_with_coords:
            coordinate = addresses_with_coords[order.address]
            avalible_restaurants_with_distance[order.id] = []
            for restrant_name in avalible_restaurants[order.id]:
                order_coords = (coordinate[0], coordinate[1])
                restaurant_distance = distance.distance(
                    order_coords,
                    restaurant_coordinates[restrant_name]
                ).km
                avalible_restaurants_with_distance[order.id].append(
                    (restrant_name, round(restaurant_distance, 2))
                )
            avalible_restaurants_with_distance[order.id] =(
                sorted(avalible_restaurants_with_distance[order.id], key=itemgetter(1))
            )
            order.restaurant_names_list = avalible_restaurants_with_distance[order.id]

    return render(request, template_name='order_items.html', context = {
        'order_items': orders
    })
