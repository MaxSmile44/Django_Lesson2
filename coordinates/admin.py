from django.contrib import admin

from .models import Coordinate


@admin.register(Coordinate)
class CoordinateAdmin(admin.ModelAdmin):
    fields = [
        'address',
        'lat',
        'lon',
        'coordinate_date'
    ]
    readonly_fields = ('coordinate_date',)
