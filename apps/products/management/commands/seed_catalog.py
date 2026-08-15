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

PHOTO_URLS = {
    "Wireless Earbuds": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=900&q=80",
    "Smart Watch": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80",
    "Bluetooth Speaker": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=900&q=80",
    "Studio Headphones": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
    "USB-C Power Bank": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?auto=format&fit=crop&w=900&q=80",
    "Cotton Tee": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=80",
    "Running Shoes": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
    "Denim Jacket": "https://images.unsplash.com/photo-1544022613-e87ca75a784a?auto=format&fit=crop&w=900&q=80",
    "Linen Shirt": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=900&q=80",
    "City Backpack": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=80",
    "Desk Lamp": "https://images.unsplash.com/photo-1507473882602-f95c4a17c9c9?auto=format&fit=crop&w=900&q=80",
    "Ceramic Mug": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=80",
    "Wool Throw": "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?auto=format&fit=crop&w=900&q=80",
    "Wall Clock": "https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?auto=format&fit=crop&w=900&q=80",
    "Ceramic Planter": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?auto=format&fit=crop&w=900&q=80",
    "Shea Body Cream": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?auto=format&fit=crop&w=900&q=80",
    "Yoga Mat": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?auto=format&fit=crop&w=900&q=80",
    "Insulated Bottle": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=80",
}

PALETTE = {
    "Wireless Earbuds": ((28, 61, 48), (201, 162, 39)),
    "Smart Watch": ((22, 77, 54), (232, 220, 196)),
    "Bluetooth Speaker": ((30, 30, 30), (201, 162, 39)),
    "Studio Headphones": ((20, 20, 20), (180, 40, 40)),
    "USB-C Power Bank": ((40, 44, 52), (200, 200, 200)),
    "Cotton Tee": ((90, 58, 42), (245, 236, 220)),
    "Running Shoes": ((155, 44, 44), (28, 25, 20)),
    "Denim Jacket": ((37, 64, 97), (232, 220, 196)),
    "Linen Shirt": ((196, 164, 132), (90, 58, 42)),
    "City Backpack": ((40, 32, 28), (201, 162, 39)),
    "Desk Lamp": ((201, 162, 39), (28, 25, 20)),
    "Ceramic Mug": ((31, 107, 74), (246, 241, 231)),
    "Wool Throw": ((140, 90, 70), (246, 241, 231)),
    "Wall Clock": ((28, 25, 20), (232, 220, 196)),
    "Ceramic Planter": ((31, 107, 74), (180, 200, 160)),
    "Shea Body Cream": ((232, 200, 180), (90, 58, 42)),
    "Yoga Mat": ((90, 40, 80), (246, 241, 231)),
    "Insulated Bottle": ((30, 80, 120), (232, 220, 196)),
}

CATEGORIES = ("Electronics", "Fashion", "Home", "Beauty", "Sports")

# sku, name, category, price, stock, featured, description
CATALOG = [
    ("EB-001", "Wireless Earbuds", "Electronics", "49.99", 40, True,
     "Compact earbuds with a clear everyday mix and a charging case that lasts through a commute."),
    ("SW-002", "Smart Watch", "Electronics", "129.00", 25, True,
     "Track steps, heart rate, and calls from your wrist. Water-resistant for rain and workouts."),
    ("SP-003", "Bluetooth Speaker", "Electronics", "59.00", 35, True,
     "Room-filling sound in a portable can. Pair in seconds for kitchen, balcony, or road trips."),
    ("HP-004", "Studio Headphones", "Electronics", "89.00", 28, False,
     "Over-ear cushions and a wired/wireless mix for focus work, films, and late-night listening."),
    ("PB-005", "USB-C Power Bank", "Electronics", "32.00", 60, False,
     "10,000 mAh backup battery with USB-C in and out. Keep a phone and earbuds alive on the go."),
    ("CT-010", "Cotton Tee", "Fashion", "19.50", 100, True,
     "Mid-weight cotton, relaxed cut. Washes well and layers under a jacket without bulk."),
    ("RS-011", "Running Shoes", "Fashion", "89.00", 30, True,
     "Cushioned daily trainers for pavement runs and all-day wear around the city."),
    ("DJ-012", "Denim Jacket", "Fashion", "74.00", 22, False,
     "Classic indigo jacket with a straight fit. Works over tees in Addis evenings."),
    ("LS-013", "Linen Shirt", "Fashion", "45.00", 40, False,
     "Breathable linen for warm days. Light, unstructured, and easy to dress up or down."),
    ("BP-014", "City Backpack", "Fashion", "54.00", 36, False,
     "Padded laptop sleeve and a bottle pocket. Built for office days and weekend errands."),
    ("DL-020", "Desk Lamp", "Home", "34.00", 50, False,
     "Warm directional light for reading and late work. Compact base for a crowded desk."),
    ("CM-021", "Ceramic Mug", "Home", "12.00", 80, False,
     "A sturdy everyday mug with a comfortable handle. Dishwasher safe."),
    ("WT-022", "Wool Throw", "Home", "48.00", 24, True,
     "Soft throw for sofas and cool nights. Neutral weave that sits well in most rooms."),
    ("WC-023", "Wall Clock", "Home", "27.00", 40, False,
     "Quiet sweep movement and a clear face. A simple piece for kitchen or hallway."),
    ("PL-024", "Ceramic Planter", "Home", "18.00", 55, False,
     "Drainage hole and a saucer included. Sized for herbs or a small indoor plant."),
    ("BC-030", "Shea Body Cream", "Beauty", "16.00", 70, False,
     "Rich shea cream for dry skin. Light scent, made for highland mornings."),
    ("YM-040", "Yoga Mat", "Sports", "29.00", 45, False,
     "Non-slip 6mm mat that rolls tight. Use at home or carry to a class."),
    ("IB-041", "Insulated Bottle", "Sports", "22.00", 80, False,
     "Keeps water cold through a hot afternoon. Leak-resistant lid for bags and desks."),
]


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
    d.rounded_rectangle((cx - 140, cy - 110, cx + 140, cy + 110), 28, fill=accent, outline=bg, width=8)
    d.text((40, h - 78), name, fill=(255, 255, 255), font=_font(36))
    d.text((40, h - 38), "Adera", fill=(232, 220, 196), font=_font(18))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _photo_bytes(name):
    url = PHOTO_URLS.get(name)
    if url:
        try:
            req = Request(url, headers={"User-Agent": "AderaCatalog/1.0"})
            with urlopen(req, timeout=20) as resp:
                data = resp.read()
            if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n":
                return data
        except OSError:
            pass
    return _draw_product(name)


def _attach_image(product, force=False):
    from pathlib import Path

    on_disk = False
    if product.image:
        try:
            on_disk = Path(product.image.path).is_file()
        except (ValueError, OSError):
            on_disk = False
    if on_disk and not force:
        return False
    raw = _photo_bytes(product.name)
    filename = f"{slugify(product.name)}.jpg"
    if product.image:
        product.image.delete(save=False)
    product.image.save(filename, ContentFile(raw), save=True)
    return True


class Command(BaseCommand):
    help = "Seed Adera catalog: categories, products, images, WELCOME10 coupon"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing product images",
        )

    def handle(self, *args, **options):
        force = options["force_images"]
        cat_map = {}
        for name in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                slug=name.lower(), defaults={"name": name}
            )
            cat_map[name] = cat

        created = 0
        imaged = 0
        for sku, name, cat_name, price, stock, featured, description in CATALOG:
            prod, was = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat_map[cat_name],
                    "price": Decimal(price),
                    "description": description,
                    "is_active": True,
                    "is_featured": featured,
                },
            )
            updates = []
            if prod.name != name:
                prod.name = name
                updates.append("name")
            if prod.description != description:
                prod.description = description
                updates.append("description")
            if prod.category_id != cat_map[cat_name].id:
                prod.category = cat_map[cat_name]
                updates.append("category")
            if prod.is_featured != featured:
                prod.is_featured = featured
                updates.append("is_featured")
            if updates:
                prod.save(update_fields=updates)

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
                f"Adera catalog ready ({Product.objects.count()} products, "
                f"{created} new, {imaged} images)"
            )
        )
