import os
import requests

from dotenv import load_dotenv

from django.db import models


class Coordinate(models.Model):
    address = models.CharField(
        'адрес',
        max_length=100,
        unique=True
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
    coordinate_date = models.DateTimeField(
        'дата и время записи координат',
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'координаты'
        verbose_name_plural = 'координаты'

    def __str__(self):
        return self.address

    def fetch_coordinates(self, address):
        try:
            load_dotenv()
            apikey = os.environ['YANDEX_APIKEY']
        except KeyError as error:
            print(f'KeyError: {error}')
        except TypeError as error:
            print(f'TypeError: {error}')

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

    def save(self, *args, **kwargs):
        if self.fetch_coordinates(self.address) and not self.address:
            lon, lat = self.fetch_coordinates(self.address)
            self.lon = lon
            self.lat = lat
            super().save(*args, **kwargs)
