from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "price", "is_active", "is_featured", "category")
    list_filter = ("is_active", "is_featured", "category")
    search_fields = ("name", "sku")
    prepopulated_fields = {"slug": ("name",)}
