from decimal import Decimal
from io import BytesIO
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from apps.inventory.services import ensure_inventory
from apps.orders.models import Coupon
from apps.products.models import Category, Product

# Real product photos (Unsplash). Seed falls back to generated art if download fails.
PHOTO_URLS = {
    "Wireless Earbuds": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=900&q=80",
    "Smart Watch": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80",
    "Cotton Tee": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=80",
    "Running Shoes": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
    "Desk Lamp": "https://images.unsplash.com/photo-1507473882602-f95c4a17c9c9?auto=format&fit=crop&w=900&q=80",
    "Ceramic Mug": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=80",
}

PALETTE = {
    "Wireless Earbuds": ((28, 61, 48), (201, 162, 39)),
    "Smart Watch": ((22, 77, 54), (232, 220, 196)),
    "Cotton Tee": ((90, 58, 42), (245, 236, 220)),
    "Running Shoes": ((155, 44, 44), (28, 25, 20)),
    "Desk Lamp": ((201, 162, 39), (28, 25, 20)),
    "Ceramic Mug": ((31, 107, 74), (246, 241, 231)),
}


def _font(size):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_product(name):
    w, h = 900, 720
    bg, accent = PALETTE.get(name, ((31, 107, 74), (201, 162, 39)))
    img = Image.new("RGB", (w, h), (246, 241, 231))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 18), fill=bg)
    d.rectangle((0, h - 110, w, h), fill=bg)
    cx, cy = w // 2, h // 2 - 30

    if "Mug" in name:
        d.rounded_rectangle((cx - 90, cy - 80, cx + 70, cy + 110), 24, fill=accent, outline=bg, width=6)
        d.arc((cx + 50, cy - 20, cx + 140, cy + 80), 270, 90, fill=bg, width=14)
    elif "Lamp" in name:
        d.ellipse((cx - 110, cy - 130, cx + 110, cy - 10), fill=accent)
        d.rectangle((cx - 10, cy - 10, cx + 10, cy + 120), fill=bg)
        d.rectangle((cx - 70, cy + 120, cx + 70, cy + 138), fill=bg)
    elif "Shoes" in name:
        d.ellipse((cx - 180, cy - 20, cx + 160, cy + 90), fill=accent)
        d.polygon([(cx - 160, cy + 20), (cx - 40, cy - 80), (cx + 40, cy - 40), (cx - 80, cy + 40)], fill=bg)
    elif "Tee" in name:
        d.polygon(
            [
                (cx - 140, cy - 40),
                (cx - 50, cy - 90),
                (cx + 50, cy - 90),
                (cx + 140, cy - 40),
                (cx + 100, cy - 10),
                (cx + 70, cy - 40),
                (cx + 70, cy + 120),
                (cx - 70, cy + 120),
                (cx - 70, cy - 40),
                (cx - 100, cy - 10),
            ],
            fill=accent,
        )
    elif "Watch" in name:
        d.rounded_rectangle((cx - 40, cy - 150, cx + 40, cy + 150), 18, fill=bg)
        d.ellipse((cx - 95, cy - 95, cx + 95, cy + 95), fill=accent, outline=bg, width=10)
        d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=bg)
    else:
        d.ellipse((cx - 120, cy - 50, cx - 20, cy + 50), fill=accent)
        d.ellipse((cx + 20, cy - 50, cx + 120, cy + 50), fill=accent)
        d.rounded_rectangle((cx - 18, cy - 12, cx + 18, cy + 12), 8, fill=bg)

    d.text((40, h - 78), name, fill=(255, 255, 255), font=_font(36))
    d.text((40, h - 38), "Merkato demo", fill=(232, 220, 196), font=_font(18))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _photo_bytes(name):
    url = PHOTO_URLS.get(name)
    if url:
        try:
            req = Request(url, headers={"User-Agent": "MerkatoCatalog/1.0"})
            with urlopen(req, timeout=20) as resp:
                data = resp.read()
            if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n":
                return data
        except OSError:
            pass
    return _draw_product(name)


def _attach_image(product, force=False):
    if product.image and not force:
        return False
    raw = _photo_bytes(product.name)
    filename = f"{slugify(product.name)}.jpg"
    if product.image:
        product.image.delete(save=False)
    product.image.save(filename, ContentFile(raw), save=True)
    return True


class Command(BaseCommand):
    help = "Seed demo categories, products, images, and WELCOME10 coupon"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing product images",
        )

    def handle(self, *args, **options):
        force = options["force_images"]
        cat_map = {}
        for name in ("Electronics", "Fashion", "Home"):
            cat, _ = Category.objects.get_or_create(
                slug=name.lower(), defaults={"name": name}
            )
            cat_map[name] = cat

        catalog = [
            ("Wireless Earbuds", "Electronics", "EB-001", "49.99", 40, True),
            ("Smart Watch", "Electronics", "SW-002", "129.00", 25, True),
            ("Cotton Tee", "Fashion", "CT-010", "19.50", 100, True),
            ("Running Shoes", "Fashion", "RS-011", "89.00", 30, False),
            ("Desk Lamp", "Home", "DL-020", "34.00", 50, False),
            ("Ceramic Mug", "Home", "CM-021", "12.00", 80, False),
        ]
        created = 0
        imaged = 0
        for name, cat_name, sku, price, stock, featured in catalog:
            prod, was = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat_map[cat_name],
                    "price": Decimal(price),
                    "description": f"Demo product: {name}",
                    "is_active": True,
                    "is_featured": featured,
                },
            )
            ensure_inventory(prod, quantity=stock if was else 0)
            if was:
                inv = prod.inventory
                if inv.quantity == 0:
                    inv.quantity = stock
                    inv.save(update_fields=["quantity"])
                created += 1
            if _attach_image(prod, force=force):
                imaged += 1

        Coupon.objects.get_or_create(
            code="WELCOME10",
            defaults={"percent_off": 10, "is_active": True, "max_uses": 1000},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog ready ({Product.objects.count()} products, "
                f"{created} new, {imaged} images)"
            )
        )
