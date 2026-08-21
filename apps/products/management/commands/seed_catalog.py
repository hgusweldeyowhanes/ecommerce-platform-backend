from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from apps.inventory.services import ensure_inventory
from apps.orders.models import Coupon
from apps.products.models import Category, Product, ProductVariant

CATEGORIES = ("Women's Wear", "Men's Wear", "Accessories", "Kids", "Wedding")

# sku, name, category, price, stock, featured, description
CATALOG = [
    (
        "TK-001",
        "Tigray Tilf Kemis",
        "Women's Wear",
        "189.00",
        24,
        True,
        "White Habesha kemis with classic Tigray tilf geometric borders in green, gold, red, and black. Hand-finished tibeb along the hem and sleeves.",
    ),
    (
        "HK-002",
        "Classic White Habesha Kemis",
        "Women's Wear",
        "149.00",
        30,
        True,
        "Breathable shemma cotton kemis with a clean silhouette and subtle embroidered trim. Everyday elegance for church, holidays, and family gatherings.",
    ),
    (
        "NS-003",
        "Handwoven Netela Shawl",
        "Accessories",
        "68.00",
        40,
        True,
        "Light double-layer netela with colorful tilf edges. Drape over a kemis for warmth and ceremony.",
    ),
    (
        "MS-004",
        "Men's Shemma Shirt",
        "Men's Wear",
        "79.00",
        28,
        True,
        "Traditional white cotton shirt with a soft collar and fine handwoven detail at the placket.",
    ),
    (
        "GT-005",
        "Golden Tibeb Dress",
        "Women's Wear",
        "220.00",
        16,
        True,
        "Statement kemis with rich gold tibeb embroidery across the bodice and hem. Made for celebrations.",
    ),
    (
        "BK-006",
        "Bridal Habesha Kemis",
        "Wedding",
        "320.00",
        10,
        True,
        "Full bridal set inspired by Tigray wedding dress: flowing white kemis, ornate tilf, and matching netela.",
    ),
    (
        "KK-007",
        "Kids Mini Kemis",
        "Kids",
        "59.00",
        35,
        False,
        "Soft cotton mini kemis for girls, with playful but traditional tilf borders sized for children.",
    ),
    (
        "SH-008",
        "Tilf Shash Headwrap",
        "Accessories",
        "34.00",
        50,
        False,
        "Embroidered shash headwrap with Tigray-style diamond motifs. Pairs with any white kemis.",
    ),
    (
        "CG-009",
        "Cotton Gabbi Wrap",
        "Accessories",
        "55.00",
        32,
        False,
        "Thick cotton gabbi for cool highland evenings. Neutral weave with a thin colored edge.",
    ),
    (
        "FK-010",
        "Festive Red-Trim Kemis",
        "Women's Wear",
        "175.00",
        20,
        True,
        "White kemis framed with bold red and gold tilf — festive without losing traditional form.",
    ),
    (
        "MC-011",
        "Men's Tilf Collar Shirt",
        "Men's Wear",
        "92.00",
        22,
        False,
        "Tailored men's shirt with a narrow green-and-gold tilf collar band. Smart for weddings and holidays.",
    ),
    (
        "WN-012",
        "Wedding Netela Pair",
        "Wedding",
        "110.00",
        18,
        False,
        "Matched bride and groom netela pair with coordinated tilf borders for ceremony photos.",
    ),
    (
        "EK-013",
        "Everyday Soft Kemis",
        "Women's Wear",
        "98.00",
        45,
        False,
        "Lightweight daily kemis with minimal trim. Comfortable for home, market days, and travel.",
    ),
    (
        "TB-014",
        "Handwoven Tilf Belt",
        "Accessories",
        "28.00",
        60,
        False,
        "Narrow handwoven belt with diamond tilf pattern. Cinched over a kemis or shemma shirt.",
    ),
    (
        "ZC-015",
        "Zuria Ceremony Set",
        "Wedding",
        "280.00",
        12,
        True,
        "Layered zuria-inspired ceremony set with embroidered panels and a matching wrap.",
    ),
    (
        "TP-016",
        "Tilf Stripe Pants",
        "Men's Wear",
        "64.00",
        26,
        False,
        "Straight cotton trousers with a discreet tilf stripe at the cuff. Pair with the shemma shirt.",
    ),
]

SIZED_PRODUCTS = {
    "Tigray Tilf Kemis",
    "Classic White Habesha Kemis",
    "Golden Tibeb Dress",
    "Bridal Habesha Kemis",
    "Festive Red-Trim Kemis",
    "Everyday Soft Kemis",
    "Kids Mini Kemis",
}


def _font(size):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_tilf_band(d, y, w, band_h=18):
    colors = [
        (0, 120, 60),
        (255, 204, 0),
        (180, 40, 40),
        (20, 20, 20),
        (196, 163, 90),
    ]
    x = 0
    i = 0
    while x < w:
        d.rectangle((x, y, min(x + 28, w), y + band_h), fill=colors[i % len(colors)])
        x += 28
        i += 1


def _draw_product(name):
    """Branded product tile: white kemis silhouette + Tigray tilf bands."""
    w, h = 900, 1100
    img = Image.new("RGB", (w, h), (247, 241, 230))
    d = ImageDraw.Draw(img)
    _draw_tilf_band(d, 0, w, 28)
    # soft stage
    d.ellipse((80, 160, w - 80, 980), fill=(255, 252, 247), outline=(196, 163, 90), width=3)
    # dress body
    dress = [(450, 220), (560, 300), (620, 520), (640, 880), (260, 880), (280, 520), (340, 300)]
    d.polygon(dress, fill=(255, 255, 255), outline=(61, 42, 26))
    # tilf hem
    _draw_tilf_band(d, 850, w, 30)
    d.rectangle((260, 850, 640, 900), fill=None)
    for i, color in enumerate([(0, 120, 60), (255, 204, 0), (180, 40, 40), (20, 20, 20), (196, 163, 90)]):
        d.rectangle((270 + i * 70, 855, 330 + i * 70, 895), fill=color)
    # sleeve accents
    d.rectangle((300, 340, 360, 380), fill=(180, 40, 40))
    d.rectangle((540, 340, 600, 380), fill=(0, 120, 60))
    d.rectangle((0, h - 140, w, h), fill=(61, 42, 26))
    d.text((40, h - 100), name[:36], fill=(255, 255, 255), font=_font(34))
    d.text((40, h - 52), "Tradiva · Wear Your Heritage", fill=(196, 163, 90), font=_font(18))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _photo_bytes(name):
    # Prefer on-brand traditional tiles so every sample looks like Tigray / Habesha dress.
    # External fashion stock often misses tilf/kemis detail.
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
    help = "Seed Tradiva catalog: Tigray / Habesha clothing, images, WELCOME10"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Replace existing product images",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Deactivate products not in the Tradiva clothing catalog",
        )

    def handle(self, *args, **options):
        force = options["force_images"]
        replace = options["replace"]
        cat_map = {}
        for name in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                slug=slugify(name), defaults={"name": name}
            )
            if cat.name != name:
                cat.name = name
                cat.save(update_fields=["name"])
            cat_map[name] = cat

        keep_skus = {row[0] for row in CATALOG}
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
                    "currency": "USD",
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
            if not prod.is_active:
                prod.is_active = True
                updates.append("is_active")
            if Decimal(str(prod.price)) != Decimal(price):
                prod.price = Decimal(price)
                updates.append("price")
            if updates:
                prod.save(update_fields=updates)

            ensure_inventory(prod, quantity=stock if was else 0)
            if was:
                inv = prod.inventory
                if inv.quantity == 0:
                    inv.quantity = stock
                    inv.save(update_fields=["quantity"])
                created += 1
            if _attach_image(prod, force=force or was):
                imaged += 1

            if name in SIZED_PRODUCTS:
                for size in ("S", "M", "L", "XL"):
                    ProductVariant.objects.get_or_create(
                        sku=f"{prod.sku}-{size}",
                        defaults={
                            "product": prod,
                            "name": size,
                            "price": None,
                            "stock": max(4, stock // 4),
                            "options": {"size": size},
                            "is_active": True,
                        },
                    )

        if replace:
            deactivated = (
                Product.objects.exclude(sku__in=keep_skus)
                .filter(is_active=True)
                .update(is_active=False)
            )
            self.stdout.write(f"Deactivated {deactivated} old catalog items.")

        Coupon.objects.get_or_create(
            code="WELCOME10",
            defaults={"percent_off": 10, "is_active": True, "max_uses": 1000},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Tradiva catalog ready ({Product.objects.filter(is_active=True).count()} active, "
                f"{created} new, {imaged} images)"
            )
        )
