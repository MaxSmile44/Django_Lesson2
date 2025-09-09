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
