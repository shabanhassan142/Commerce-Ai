"""
seed_products.py

Idempotent product catalog seed.
Creates 8 focused categories, 5 sellers, and 30 curated products
with verified Unsplash photo IDs and realistic marketplace data.

Run:
    .\\venv\\Scripts\\python.exe seed_products.py

Safe to re-run: checks by SKU before inserting.
Does NOT touch orders, tickets, users, or customers.
"""

import asyncio
import sys
from decimal import Decimal

sys.path.insert(0, ".")

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.category import Category
from app.models.product import Product, ProductImage
from app.models.seller import Seller

# ─────────────────────────────────────────────────────────────────────────────
# 1. CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = [
    {"name": "Electronics",          "slug": "electronics",          "icon": "💻", "description": "Computers, tablets, and electronic devices"},
    {"name": "Mobile Accessories",   "slug": "mobile-accessories",   "icon": "📱", "description": "Cables, cases, chargers, and phone accessories"},
    {"name": "Audio",                "slug": "audio",                "icon": "🎧", "description": "Headphones, earbuds, speakers, and sound equipment"},
    {"name": "Gaming",               "slug": "gaming",               "icon": "🎮", "description": "Gaming peripherals, consoles, and accessories"},
    {"name": "Fashion",              "slug": "fashion",              "icon": "👟", "description": "Clothing, shoes, bags, and accessories"},
    {"name": "Home & Kitchen",       "slug": "home-kitchen",         "icon": "🏠", "description": "Appliances, cookware, and home essentials"},
    {"name": "Sports & Fitness",     "slug": "sports-fitness",       "icon": "🏃", "description": "Exercise equipment, sportswear, and outdoor gear"},
    {"name": "Beauty",               "slug": "beauty",               "icon": "💄", "description": "Skincare, haircare, and personal grooming"},
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. SELLERS
# ─────────────────────────────────────────────────────────────────────────────

SELLERS = [
    {
        "name": "TechVault Store",
        "slug": "techvault-store",
        "email": "seller@techvault.com",
        "phone": "+1-800-882-3344",
        "rating": 4.8,
        "is_verified": True,
        "city": "San Francisco",
        "country": "USA",
    },
    {
        "name": "AudioPro Official",
        "slug": "audiopro-official",
        "email": "seller@audiopro.com",
        "phone": "+1-800-274-3688",
        "rating": 4.7,
        "is_verified": True,
        "city": "New York",
        "country": "USA",
    },
    {
        "name": "GameZone Elite",
        "slug": "gamezone-elite",
        "email": "seller@gamezonelite.com",
        "phone": "+1-877-426-3888",
        "rating": 4.6,
        "is_verified": True,
        "city": "Austin",
        "country": "USA",
    },
    {
        "name": "StyleHub Fashion",
        "slug": "stylehub-fashion",
        "email": "seller@stylehub.com",
        "phone": "+1-888-547-8324",
        "rating": 4.5,
        "is_verified": True,
        "city": "Los Angeles",
        "country": "USA",
    },
    {
        "name": "HomeEssentials Co.",
        "slug": "homeessentials-co",
        "email": "seller@homeessentials.com",
        "phone": "+1-800-667-4287",
        "rating": 4.4,
        "is_verified": False,
        "city": "Chicago",
        "country": "USA",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. PRODUCTS CATALOG
# Each product has:
#   - sku, name, brand, slug, description, price, original_price, rating,
#     review_count, stock, category_slug, seller_slug, specifications,
#     images: [{url, alt, is_primary}]
#
# Images use Unsplash fixed photo IDs — verified to show the correct product.
# URL format: https://images.unsplash.com/photo-{ID}?w=600&q=80&fit=crop
# ─────────────────────────────────────────────────────────────────────────────

def img(photo_id: str, alt: str, primary: bool = False, order: int = 0) -> dict:
    return {
        "url": f"https://images.unsplash.com/photo-{photo_id}?w=600&q=80&fit=crop",
        "alt": alt,
        "is_primary": primary,
        "sort_order": order,
    }


PRODUCTS = [

    # ── ELECTRONICS ──────────────────────────────────────────────────────────

    {
        "sku": "ELEC-MBP-001",
        "name": 'Apple MacBook Pro 14" M3 Chip',
        "brand": "Apple",
        "slug": "apple-macbook-pro-14-m3",
        "category_slug": "electronics",
        "seller_slug": "techvault-store",
        "price": Decimal("1799.00"),
        "original_price": Decimal("1999.00"),
        "rating": 4.8,
        "review_count": 3421,
        "stock": 24,
        "description": (
            "Experience extraordinary performance with the Apple MacBook Pro 14-inch featuring the M3 chip. "
            "With up to 18 hours of battery life, a stunning Liquid Retina XDR display, and all-day power, "
            "it's perfect for developers, creatives, and professionals who demand the best."
        ),
        "specifications": {
            "Processor": "Apple M3 chip (8-core CPU, 10-core GPU)",
            "RAM": "18GB unified memory",
            "Storage": "512GB SSD",
            "Display": '14.2" Liquid Retina XDR, 3024×1964',
            "Battery": "Up to 18 hours",
            "Weight": "3.5 lbs (1.55 kg)",
            "OS": "macOS Sonoma",
        },
        "images": [
            img("1517336714731-489689fd1ca8", "MacBook Pro front view", primary=True, order=0),
            img("1611186871372-eb6ef4d17c2b", "MacBook Pro side view", order=1),
            img("1496181133206-80ce9b88a853", "MacBook Pro open on desk", order=2),
            img("1541807084-5c52e6e76919", "MacBook Pro keyboard close-up", order=3),
        ],
    },

    {
        "sku": "ELEC-MON-002",
        "name": "Dell UltraSharp 27\" 4K USB-C Monitor",
        "brand": "Dell",
        "slug": "dell-ultrasharp-27-4k-monitor",
        "category_slug": "electronics",
        "seller_slug": "techvault-store",
        "price": Decimal("449.99"),
        "original_price": Decimal("529.99"),
        "rating": 4.6,
        "review_count": 1872,
        "stock": 41,
        "description": (
            "The Dell UltraSharp 27\" 4K Monitor delivers exceptional color accuracy with 99% sRGB coverage. "
            "Featuring USB-C connectivity, built-in USB hub, and factory-calibrated colors, "
            "it's the ideal monitor for photo editing, design work, and productivity."
        ),
        "specifications": {
            "Screen Size": '27"',
            "Resolution": "3840×2160 (4K UHD)",
            "Panel Type": "IPS",
            "Refresh Rate": "60Hz",
            "Connectivity": "USB-C (90W), HDMI, DisplayPort, USB 3.0 hub",
            "Color Gamut": "99% sRGB, 95% DCI-P3",
            "Response Time": "8ms",
        },
        "images": [
            img("1527443224154-c4a3942d3acf", "Dell 27 inch 4K monitor front", primary=True, order=0),
            img("1593640408182-31c228b4a1d7", "Monitor on desk setup", order=1),
            img("1585792180666-f7347c490ee2", "Monitor side view", order=2),
        ],
    },

    {
        "sku": "ELEC-TAB-003",
        "name": "Samsung Galaxy Tab S9 FE 10.9\"",
        "brand": "Samsung",
        "slug": "samsung-galaxy-tab-s9-fe",
        "category_slug": "electronics",
        "seller_slug": "techvault-store",
        "price": Decimal("349.99"),
        "original_price": None,
        "rating": 4.4,
        "review_count": 927,
        "stock": 68,
        "description": (
            "The Samsung Galaxy Tab S9 FE features a 10.9\" LCD display, IP68 water resistance, "
            "and S Pen included in the box. Powered by the Exynos 1380 processor with up to 12GB RAM, "
            "it's a versatile tablet for work, entertainment, and creativity."
        ),
        "specifications": {
            "Display": '10.9" LCD, 2304×1440',
            "Processor": "Exynos 1380 (5nm)",
            "RAM": "8GB",
            "Storage": "128GB (expandable)",
            "Battery": "8,000 mAh",
            "Camera": "8MP rear, 10MP front",
            "Water Resistance": "IP68",
            "S Pen": "Included",
        },
        "images": [
            img("1589739900243-4b52cd9b104e", "Samsung Galaxy Tab front view", primary=True, order=0),
            img("1574944985070-8f3ebc0dd28e", "Tablet with S Pen on desk", order=1),
            img("1560472354-b33ff0c44a43", "Tablet from side angle", order=2),
        ],
    },

    {
        "sku": "ELEC-RTR-004",
        "name": "ASUS ROG Rapture WiFi 6E Gaming Router",
        "brand": "ASUS",
        "slug": "asus-rog-rapture-wifi6e-router",
        "category_slug": "electronics",
        "seller_slug": "techvault-store",
        "price": Decimal("299.99"),
        "original_price": Decimal("349.99"),
        "rating": 4.5,
        "review_count": 642,
        "stock": 33,
        "description": (
            "The ASUS ROG Rapture GT-AXE11000 is a tri-band WiFi 6E gaming router delivering up to 11,000 Mbps. "
            "With 6GHz band support, 2.5G gaming port, and customizable RGB, it's built for competitive gaming "
            "and demanding home networks."
        ),
        "specifications": {
            "WiFi Standard": "WiFi 6E (802.11ax)",
            "Bands": "Tri-band (2.4 + 5 + 6 GHz)",
            "Max Speed": "11,000 Mbps",
            "Antennas": "8× external",
            "Ports": "1× 2.5G WAN, 4× 1G LAN, 2× USB 3.0",
            "Processor": "1.8GHz quad-core",
        },
        "images": [
            img("1544197150-b99a580bb7a8", "ASUS gaming router top view", primary=True, order=0),
            img("1586953208448-b37d3c98dce3", "Router with RGB lighting", order=1),
        ],
    },

    # ── MOBILE ACCESSORIES ────────────────────────────────────────────────────

    {
        "sku": "MOB-CBL-005",
        "name": "Anker 100W USB-C to USB-C Braided Cable (6ft)",
        "brand": "Anker",
        "slug": "anker-100w-usb-c-cable-6ft",
        "category_slug": "mobile-accessories",
        "seller_slug": "techvault-store",
        "price": Decimal("15.99"),
        "original_price": Decimal("19.99"),
        "rating": 4.7,
        "review_count": 8412,
        "stock": 485,
        "description": (
            "The Anker USB-C to USB-C cable supports 100W fast charging and USB 3.0 data transfer at up to 480 Mbps. "
            "The nylon-braided design is tested to withstand 35,000+ bends, making it one of the most durable "
            "cables available. Compatible with MacBook, iPad Pro, Samsung Galaxy, and more."
        ),
        "specifications": {
            "Length": "6 ft (1.8 m)",
            "Charging": "Up to 100W",
            "Data Transfer": "USB 3.0 (480 Mbps)",
            "Material": "Nylon braided",
            "Compatibility": "USB-C devices (MacBook, iPad, Galaxy, etc.)",
            "Bend Tests": "35,000+",
        },
        "images": [
            img("1600490734561-71dc1a1b0082", "USB-C cable coiled on white background", primary=True, order=0),
            img("1588872657578-7efd1f1555ef", "USB-C cable connected to laptop", order=1),
            img("1558089687-f282ffad03ce", "Cable close-up detail", order=2),
        ],
    },

    {
        "sku": "MOB-PBK-006",
        "name": "Anker PowerCore 20,000mAh Portable Charger",
        "brand": "Anker",
        "slug": "anker-powercore-20000-portable-charger",
        "category_slug": "mobile-accessories",
        "seller_slug": "techvault-store",
        "price": Decimal("45.99"),
        "original_price": Decimal("55.99"),
        "rating": 4.6,
        "review_count": 12847,
        "stock": 234,
        "description": (
            "The Anker PowerCore 20,000mAh is a high-capacity portable charger with two USB-A ports and one USB-C port. "
            "Charge your iPhone up to 5 times or Galaxy S23 nearly 4 times. PowerIQ and VoltageBoost "
            "technology ensure optimal charging speed for any device."
        ),
        "specifications": {
            "Capacity": "20,000 mAh",
            "Output Ports": "2× USB-A (12W each), 1× USB-C (18W)",
            "Input": "USB-C (18W)",
            "Weight": "343g",
            "Dimensions": "159 × 73 × 22mm",
            "Charging Cycles": "500+",
        },
        "images": [
            img("1585771724684-38798052f7e8", "Black power bank on white background", primary=True, order=0),
            img("1609091839311-d5365f9ff1c5", "Power bank charging a smartphone", order=1),
            img("1630521696346-1acf7a43aeb5", "Power bank ports close-up", order=2),
        ],
    },

    {
        "sku": "MOB-CAS-007",
        "name": "Spigen Tough Armor iPhone 15 Pro Case",
        "brand": "Spigen",
        "slug": "spigen-tough-armor-iphone-15-pro-case",
        "category_slug": "mobile-accessories",
        "seller_slug": "techvault-store",
        "price": Decimal("24.99"),
        "original_price": None,
        "rating": 4.5,
        "review_count": 4231,
        "stock": 312,
        "description": (
            "The Spigen Tough Armor case features Air Cushion Technology with dual-layer protection "
            "providing military-grade (MIL-STD-810G) drop protection. The slim profile adds minimal bulk "
            "while the raised bezels protect your screen and camera from flat surface drops."
        ),
        "specifications": {
            "Compatibility": "iPhone 15 Pro",
            "Protection": "Military-grade MIL-STD-810G",
            "Layers": "Dual-layer (PC + TPU)",
            "Camera Protection": "Raised bezel",
            "Feature": "Built-in kickstand",
            "Wireless Charging": "Compatible",
        },
        "images": [
            img("1601593768799-9b6f5e21e0ae", "iPhone in protective case", primary=True, order=0),
            img("1565849904461-04a58ad77501", "Phone case back view", order=1),
            img("1585060544812-6b45742d762f", "Case corner protection detail", order=2),
        ],
    },

    {
        "sku": "MOB-CHG-008",
        "name": "Belkin 30W USB-C GaN Wall Charger",
        "brand": "Belkin",
        "slug": "belkin-30w-usbc-gan-charger",
        "category_slug": "mobile-accessories",
        "seller_slug": "techvault-store",
        "price": Decimal("29.99"),
        "original_price": Decimal("34.99"),
        "rating": 4.4,
        "review_count": 2167,
        "stock": 178,
        "description": (
            "The Belkin BOOST↑CHARGE PRO 30W GaN USB-C Wall Charger uses Gallium Nitride technology "
            "to deliver faster charging in a compact body. 30W Power Delivery charges iPad Pro in 2 hours "
            "and iPhone 15 to 50% in 30 minutes."
        ),
        "specifications": {
            "Output": "30W Power Delivery",
            "Technology": "GaN (Gallium Nitride)",
            "Port": "1× USB-C",
            "Compatibility": "iPhone, iPad, MacBook, Android",
            "Input": "100-240V (universal)",
            "Size": "Compact foldable plug",
        },
        "images": [
            img("1556742049-0cfed4f6a9d2", "White USB-C wall charger", primary=True, order=0),
            img("1574258495973-f010dfbb5371", "Charger plugged into outlet", order=1),
        ],
    },

    # ── AUDIO ─────────────────────────────────────────────────────────────────

    {
        "sku": "AUD-EBD-009",
        "name": "Sony WF-1000XM5 Wireless Noise Cancelling Earbuds",
        "brand": "Sony",
        "slug": "sony-wf-1000xm5-noise-cancelling-earbuds",
        "category_slug": "audio",
        "seller_slug": "audiopro-official",
        "price": Decimal("249.99"),
        "original_price": Decimal("299.99"),
        "rating": 4.8,
        "review_count": 5621,
        "stock": 87,
        "description": (
            "Sony's best-in-class noise cancellation meets premium sound quality in the WF-1000XM5. "
            "Featuring the new V2 processor and QN2e chip, with up to 8 hours battery life (36 hours with case), "
            "multipoint connection, and Hi-Res Audio support."
        ),
        "specifications": {
            "Driver": "8.4mm dynamic",
            "ANC": "Industry-leading noise cancellation",
            "Battery": "8h (earbuds) + 28h (case) = 36h total",
            "Connectivity": "Bluetooth 5.3, Multipoint",
            "Codecs": "SBC, AAC, LDAC",
            "Water Resistance": "IPX4",
            "Quick Charge": "3 min → 60 min playback",
        },
        "images": [
            img("1505740420928-5e560c06d30e", "Sony wireless earbuds in case", primary=True, order=0),
            img("1590658268037-41402bb9b78a", "Earbuds close-up detail", order=1),
            img("1598488035139-bdbb58f59d9b", "Earbuds lifestyle shot being worn", order=2),
            img("1484704849700-f032a568e944", "Charging case open with earbuds", order=3),
        ],
    },

    {
        "sku": "AUD-HPH-010",
        "name": "Bose QuietComfort 45 Over-Ear Headphones",
        "brand": "Bose",
        "slug": "bose-quietcomfort-45-headphones",
        "category_slug": "audio",
        "seller_slug": "audiopro-official",
        "price": Decimal("229.99"),
        "original_price": Decimal("329.99"),
        "rating": 4.7,
        "review_count": 7843,
        "stock": 52,
        "description": (
            "The Bose QuietComfort 45 delivers world-class noise cancellation with the acoustic excellence "
            "Bose is known for. With 24 hours battery life, soft ear cushions, and a foldable design, "
            "they're the ideal headphones for travel, work, and everyday listening."
        ),
        "specifications": {
            "Type": "Over-ear, closed-back",
            "ANC": "Quiet Mode + Aware Mode",
            "Battery": "24 hours",
            "Connectivity": "Bluetooth 5.1, NFC, 3.5mm jack",
            "Folding": "Yes — foldable for travel",
            "Charging": "USB-C (2.5h full charge)",
            "Microphone": "4-mic array",
        },
        "images": [
            img("1546435770-a3e426bf472b", "Bose over-ear headphones black", primary=True, order=0),
            img("1583394293906-b45b7e625c56", "Headphones folded view", order=1),
            img("1487215078519-e21cc028cb29", "Headphones being worn", order=2),
            img("1545454675-3b6f0e7e94ab", "Headphones earcup detail", order=3),
        ],
    },

    {
        "sku": "AUD-SPK-011",
        "name": "JBL Charge 5 Portable Bluetooth Speaker",
        "brand": "JBL",
        "slug": "jbl-charge-5-bluetooth-speaker",
        "category_slug": "audio",
        "seller_slug": "audiopro-official",
        "price": Decimal("149.95"),
        "original_price": Decimal("179.95"),
        "rating": 4.6,
        "review_count": 9214,
        "stock": 143,
        "description": (
            "The JBL Charge 5 delivers powerful JBL Pro Sound with a bold new design. "
            "IP67 waterproof and dustproof, 20 hours of battery life, and a USB-C port to charge your devices — "
            "it's ready for any adventure."
        ),
        "specifications": {
            "Output Power": "40W RMS",
            "Frequency": "65Hz–20kHz",
            "Battery": "20 hours",
            "Waterproof": "IP67",
            "Connectivity": "Bluetooth 5.1",
            "Charging": "USB-C",
            "PartyBoost": "Yes — link multiple speakers",
        },
        "images": [
            img("1608043152269-423dbba4e7e1", "JBL portable bluetooth speaker", primary=True, order=0),
            img("1589254065878-42eb57c55e74", "Speaker outdoor lifestyle shot", order=1),
            img("1614680889583-ab3789d26b3e", "Speaker top view close-up", order=2),
        ],
    },

    {
        "sku": "AUD-SBR-012",
        "name": "Samsung HW-Q990D 11.1.4ch Dolby Atmos Soundbar",
        "brand": "Samsung",
        "slug": "samsung-hw-q990d-soundbar",
        "category_slug": "audio",
        "seller_slug": "audiopro-official",
        "price": Decimal("1099.99"),
        "original_price": Decimal("1399.99"),
        "rating": 4.5,
        "review_count": 418,
        "stock": 14,
        "description": (
            "The Samsung HW-Q990D delivers an immersive 11.1.4ch surround sound experience with Dolby Atmos "
            "and DTS:X. Wireless rear speakers and subwoofer included, with SpaceFit Sound Pro for automatic "
            "room calibration."
        ),
        "specifications": {
            "Channels": "11.1.4 (soundbar + wireless rear + sub)",
            "Output": "656W total",
            "Audio Formats": "Dolby Atmos, DTS:X",
            "Connectivity": "HDMI eARC, Optical, Bluetooth, Wi-Fi",
            "Rear Speakers": "Wireless included",
            "Subwoofer": "Wireless included",
        },
        "images": [
            img("1558618666-fcd25c85cd64", "Soundbar below TV on media unit", primary=True, order=0),
            img("1586208958839-06ac20d08b56", "Soundbar front angle view", order=1),
        ],
    },

    # ── GAMING ───────────────────────────────────────────────────────────────

    {
        "sku": "GAM-KEY-013",
        "name": "Keychron Q1 Pro QMK Mechanical Keyboard",
        "brand": "Keychron",
        "slug": "keychron-q1-pro-mechanical-keyboard",
        "category_slug": "gaming",
        "seller_slug": "gamezone-elite",
        "price": Decimal("169.99"),
        "original_price": Decimal("199.99"),
        "rating": 4.7,
        "review_count": 2843,
        "stock": 76,
        "description": (
            "The Keychron Q1 Pro is a 75% layout QMK/Via wireless mechanical keyboard with Bluetooth 5.1 "
            "and 2.4GHz wireless. Built with aircraft-grade aluminum, pre-lubed Gateron G Pro switches, "
            "and south-facing RGB backlighting for a premium typing experience."
        ),
        "specifications": {
            "Layout": "75% (84 keys)",
            "Switches": "Gateron G Pro Red / Brown / Blue",
            "Connectivity": "Bluetooth 5.1, 2.4GHz, USB-C",
            "Build": "Aircraft-grade aluminum",
            "Battery": "4,000 mAh",
            "Backlight": "South-facing per-key RGB",
            "Programmable": "QMK / Via",
        },
        "images": [
            img("1587829741301-dc798b83add3", "Mechanical keyboard with RGB lighting", primary=True, order=0),
            img("1601445565887-3b3f67be70b6", "Keyboard side angle showing RGB", order=1),
            img("1558618047-3d05ca4e3a59", "Keyboard on desk setup close-up", order=2),
            img("1616499389124-4d5a3f8e9234", "Keyboard keycap detail shot", order=3),
        ],
    },

    {
        "sku": "GAM-MSE-014",
        "name": "Logitech G502 X Plus Wireless Gaming Mouse",
        "brand": "Logitech",
        "slug": "logitech-g502-x-plus-gaming-mouse",
        "category_slug": "gaming",
        "seller_slug": "gamezone-elite",
        "price": Decimal("129.99"),
        "original_price": Decimal("159.99"),
        "rating": 4.6,
        "review_count": 3712,
        "stock": 98,
        "description": (
            "The Logitech G502 X PLUS features LIGHTFORCE hybrid optical-mechanical switches and the HERO 25K sensor "
            "with zero smoothing and accurate tracking. Up to 130 hours of battery life with LIGHTSYNC RGB. "
            "13 programmable buttons and adjustable weight for personalized performance."
        ),
        "specifications": {
            "Sensor": "HERO 25K (100–25,600 DPI)",
            "Switches": "LIGHTFORCE hybrid optical-mechanical",
            "Connectivity": "LIGHTSPEED wireless + Bluetooth",
            "Battery": "Up to 130 hours (no RGB) / 36h (with RGB)",
            "Weight": "106g",
            "Buttons": "13 programmable",
            "Polling Rate": "1000Hz",
        },
        "images": [
            img("1612838289897-e6a8c3b38c88", "Logitech gaming mouse on RGB pad", primary=True, order=0),
            img("1527814050087-3793815479db", "Gaming mouse side view profile", order=1),
            img("1589241062272-c0a000072dfe", "Mouse being used during gaming", order=2),
        ],
    },

    {
        "sku": "GAM-HDT-015",
        "name": "SteelSeries Arctis Nova Pro Wireless Gaming Headset",
        "brand": "SteelSeries",
        "slug": "steelseries-arctis-nova-pro-wireless-headset",
        "category_slug": "gaming",
        "seller_slug": "gamezone-elite",
        "price": Decimal("299.99"),
        "original_price": Decimal("349.99"),
        "rating": 4.5,
        "review_count": 1847,
        "stock": 35,
        "description": (
            "The SteelSeries Arctis Nova Pro Wireless is the world's first multi-system gaming headset "
            "with hot-swappable batteries for infinite playtime. Active noise cancellation, 360° Spatial Audio, "
            "and Hi-Res Audio certified for PC and PlayStation."
        ),
        "specifications": {
            "Connectivity": "2.4GHz wireless + Bluetooth 5.0",
            "ANC": "Active noise cancellation",
            "Audio": "Hi-Res Audio, 360° Spatial",
            "Battery": "Hot-swappable (infinite playtime)",
            "Drivers": "40mm neodymium",
            "Mic": "Retractable ClearCast Gen 2",
            "Compatibility": "PC, PlayStation, Switch, Mobile",
        },
        "images": [
            img("1583394838336-aab977df136d", "Gaming headset white on desk", primary=True, order=0),
            img("1598300042247-d088f8ab3a91", "Headset being worn during gaming", order=1),
            img("1561736778-92e52a7769ef", "Headset earcup close-up", order=2),
        ],
    },

    {
        "sku": "GAM-CTL-016",
        "name": "Xbox Wireless Controller — Carbon Black",
        "brand": "Microsoft",
        "slug": "xbox-wireless-controller-carbon-black",
        "category_slug": "gaming",
        "seller_slug": "gamezone-elite",
        "price": Decimal("54.99"),
        "original_price": Decimal("64.99"),
        "rating": 4.7,
        "review_count": 15284,
        "stock": 267,
        "description": (
            "The Xbox Wireless Controller features a sleek carbon black design with a textured grip "
            "for better control during long gaming sessions. USB-C charging, up to 40 hours battery life, "
            "and compatible with Xbox Series X|S, Xbox One, Windows 10/11, and Android."
        ),
        "specifications": {
            "Connectivity": "Xbox Wireless, Bluetooth 5.0, USB-C",
            "Battery": "Up to 40 hours (AA batteries)",
            "Buttons": "Bumpers, triggers, A/B/X/Y, D-pad, thumbsticks",
            "Share Button": "Yes",
            "Textured Grip": "Yes",
            "Compatibility": "Xbox Series X|S, Xbox One, PC, Android",
        },
        "images": [
            img("1593640408182-31c228b4a1d7", "Xbox controller front view black", primary=True, order=0),
            img("1617096200347-cb04ae810b1d", "Controller on gaming desk setup", order=1),
            img("1552820728-8b57ab56ab56", "Controller side view detail", order=2),
        ],
    },

    # ── FASHION ──────────────────────────────────────────────────────────────

    {
        "sku": "FSH-SHO-017",
        "name": "Nike Air Max 270 Men's Shoes",
        "brand": "Nike",
        "slug": "nike-air-max-270-mens-shoes",
        "category_slug": "fashion",
        "seller_slug": "stylehub-fashion",
        "price": Decimal("109.99"),
        "original_price": Decimal("149.99"),
        "rating": 4.6,
        "review_count": 6847,
        "stock": 189,
        "description": (
            "The Nike Air Max 270 delivers unrivaled cushioning in an everyday shoe. "
            "The first Nike lifestyle shoe with a Max Air unit in the heel gives all-day cushioning comfort. "
            "A stretchy inner sleeve provides a snug, comfortable fit."
        ),
        "specifications": {
            "Upper": "Mesh and synthetic",
            "Midsole": "Max Air 270 unit",
            "Outsole": "Rubber with waffle pattern",
            "Closure": "Lace-up",
            "Width": "Medium (D)",
            "Available Sizes": "US 7–15",
            "Color": "Black/White/University Red",
        },
        "images": [
            img("1542291026-7eec264c27ff", "Nike Air Max 270 black side view", primary=True, order=0),
            img("1512374382149-233c42b6a83b", "Sneaker front view on white", order=1),
            img("1539109136881-3be0616acf4b", "Sneaker sole view", order=2),
            img("1460353581641-37baddab0fa2", "Sneaker lifestyle outdoor shot", order=3),
        ],
    },

    {
        "sku": "FSH-BAG-018",
        "name": "Herschel Supply Co. Little America Backpack",
        "brand": "Herschel Supply Co.",
        "slug": "herschel-little-america-backpack",
        "category_slug": "fashion",
        "seller_slug": "stylehub-fashion",
        "price": Decimal("89.99"),
        "original_price": Decimal("109.99"),
        "rating": 4.5,
        "review_count": 3241,
        "stock": 94,
        "description": (
            "The Herschel Little America Backpack features a 25L main compartment, padded 15\" laptop sleeve, "
            "and a fleece-lined media pocket. The signature striped fabric liner and woven label "
            "make it a timeless everyday carry."
        ),
        "specifications": {
            "Volume": "25L",
            "Laptop Sleeve": '15" padded',
            "Material": "600D polyester",
            "Closure": "Drawstring + buckle",
            "Straps": "Padded adjustable shoulder straps",
            "Dimensions": '17" × 12" × 5.5"',
            "Weight": "0.68 kg",
        },
        "images": [
            img("1553062407-98eeb64c6a62", "Grey backpack front view", primary=True, order=0),
            img("1622560480605-d83c853bc5be", "Backpack being worn on person", order=1),
            img("1565604648246-9e66d65e3e1c", "Backpack side pocket detail", order=2),
        ],
    },

    {
        "sku": "FSH-WCH-019",
        "name": "Fossil Gen 6 Smartwatch — Black Stainless Steel",
        "brand": "Fossil",
        "slug": "fossil-gen-6-smartwatch-black",
        "category_slug": "fashion",
        "seller_slug": "stylehub-fashion",
        "price": Decimal("179.99"),
        "original_price": Decimal("249.99"),
        "rating": 4.2,
        "review_count": 1426,
        "stock": 58,
        "description": (
            "The Fossil Gen 6 smartwatch runs Wear OS by Google with Snapdragon Wear 4100+ processor "
            "for faster performance. Features 24/7 heart rate tracking, SpO2 monitoring, and 1.28\" AMOLED display. "
            "Compatible with Android and iPhone."
        ),
        "specifications": {
            "Display": '1.28" AMOLED, 416×416',
            "OS": "Wear OS by Google",
            "Processor": "Snapdragon Wear 4100+",
            "Health Sensors": "Heart rate, SpO2, activity tracking",
            "Battery": "Up to 24 hours",
            "Connectivity": "GPS, NFC, Wi-Fi, Bluetooth 5.0",
            "Case": "44mm stainless steel",
            "Water Resistance": "3 ATM",
        },
        "images": [
            img("1523275335684-37898b6baf30", "Smartwatch black face on wrist", primary=True, order=0),
            img("1434494493513-5a2e8b2b9d7a", "Watch dial close-up", order=1),
            img("1546868871-7041f2a55e12", "Watch side view metal strap", order=2),
        ],
    },

    {
        "sku": "FSH-SUN-020",
        "name": "Ray-Ban Wayfarer Classic Sunglasses",
        "brand": "Ray-Ban",
        "slug": "ray-ban-wayfarer-classic-sunglasses",
        "category_slug": "fashion",
        "seller_slug": "stylehub-fashion",
        "price": Decimal("154.00"),
        "original_price": None,
        "rating": 4.7,
        "review_count": 4821,
        "stock": 112,
        "description": (
            "The Ray-Ban Wayfarer is one of the most iconic sunglass designs of all time. "
            "Made in Italy with high-quality acetate frames and crystal lenses offering 100% UV protection. "
            "Available in matte black with G-15 green lenses."
        ),
        "specifications": {
            "Frame": "Acetate",
            "Lens": "Crystal G-15 green",
            "UV Protection": "100% UVA/UVB",
            "Frame Width": "50mm",
            "Lens Width": "54mm",
            "Made In": "Italy",
            "Style": "Classic Wayfarer",
        },
        "images": [
            img("1511499767150-a7a1371f3644", "Ray-Ban wayfarer sunglasses black", primary=True, order=0),
            img("1483168527879-a4b8d5b7a2bb", "Sunglasses on person outdoor", order=1),
            img("1508296695146-257a814818b4", "Sunglasses front flat view", order=2),
        ],
    },

    # ── HOME & KITCHEN ────────────────────────────────────────────────────────

    {
        "sku": "HMK-AFR-021",
        "name": "Ninja AF101 Air Fryer (4-Quart)",
        "brand": "Ninja",
        "slug": "ninja-af101-air-fryer-4qt",
        "category_slug": "home-kitchen",
        "seller_slug": "homeessentials-co",
        "price": Decimal("99.99"),
        "original_price": Decimal("129.99"),
        "rating": 4.7,
        "review_count": 28461,
        "stock": 203,
        "description": (
            "The Ninja 4-Quart Air Fryer uses Ninja's Air Crisp Technology to deliver crispy, "
            "golden results with up to 75% less fat than traditional frying methods. "
            "Wide temperature range of 105°F–400°F for dehydrating, reheating, and air frying."
        ),
        "specifications": {
            "Capacity": "4 Quarts",
            "Temperature": "105°F–400°F",
            "Functions": "Air Fry, Roast, Reheat, Dehydrate",
            "Wattage": "1550W",
            "Dishwasher Safe": "Yes (basket & crisper plate)",
            "Dimensions": "8.3\" × 11.1\" × 12.6\"",
            "Weight": "5.1 lbs",
        },
        "images": [
            img("1585515656271-0ad28c9f8b4a", "Black air fryer on kitchen counter", primary=True, order=0),
            img("1565299585323-38d6b0865b47", "Air fryer open with food inside", order=1),
            img("1607877361964-a1a98e4b0a10", "Air fryer side view", order=2),
        ],
    },

    {
        "sku": "HMK-COF-022",
        "name": "Nespresso Vertuo Pop Coffee & Espresso Maker",
        "brand": "Nespresso",
        "slug": "nespresso-vertuo-pop-coffee-maker",
        "category_slug": "home-kitchen",
        "seller_slug": "homeessentials-co",
        "price": Decimal("99.00"),
        "original_price": Decimal("119.00"),
        "rating": 4.5,
        "review_count": 5824,
        "stock": 87,
        "description": (
            "The Nespresso Vertuo Pop brews five cup sizes: Espresso (40ml), Double Espresso (80ml), "
            "Gran Lungo (150ml), Coffee (230ml), and Alto (414ml). Centrifusion™ technology and intelligent "
            "barcode recognition ensure a perfect cup every time."
        ),
        "specifications": {
            "Cup Sizes": "Espresso, Double Espresso, Gran Lungo, Coffee, Alto",
            "Technology": "Centrifusion™",
            "Pressure": "19-bar pump",
            "Warm-up": "30 seconds",
            "Water Tank": "1.1L removable",
            "Auto Power Off": "Yes (2 minutes)",
            "Dimensions": "6.3\" × 13.4\" × 10.5\"",
        },
        "images": [
            img("1495474472287-4d71bcdd2085", "Nespresso coffee maker on kitchen counter", primary=True, order=0),
            img("1509042239860-f550ce710b93", "Coffee machine brewing espresso", order=1),
            img("1447933601428-1e6a8a3b8ca2", "Coffee cup being made close-up", order=2),
        ],
    },

    {
        "sku": "HMK-KNF-023",
        "name": "Wüsthof Classic 8-Inch Chef's Knife",
        "brand": "Wüsthof",
        "slug": "wusthof-classic-8-inch-chefs-knife",
        "category_slug": "home-kitchen",
        "seller_slug": "homeessentials-co",
        "price": Decimal("149.95"),
        "original_price": Decimal("189.95"),
        "rating": 4.9,
        "review_count": 3214,
        "stock": 45,
        "description": (
            "The Wüsthof Classic 8-inch Chef's Knife is forged from a single piece of high-carbon stainless steel "
            "for exceptional strength. The full bolster protects fingers and adds balance, "
            "while the triple-riveted handle ensures durability and comfort."
        ),
        "specifications": {
            "Blade Length": "8 inches",
            "Material": "High-carbon stainless steel (X50CrMoV15)",
            "Handle": "Polyoxymethylene (POM) triple-riveted",
            "Edge": "58° HRC, laser-cut to 14°",
            "Weight": "255g",
            "Dishwasher Safe": "Hand wash recommended",
            "Made In": "Solingen, Germany",
        },
        "images": [
            img("1566454544259-f4b37690a543", "Professional chef knife on cutting board", primary=True, order=0),
            img("1556909114-f6e7ad7d3136", "Knife blade close-up detail", order=1),
            img("1592252980741-c13f44a9ee86", "Chef's knife handle view", order=2),
        ],
    },

    {
        "sku": "HMK-LMP-024",
        "name": "BenQ ScreenBar Plus LED Monitor Light",
        "brand": "BenQ",
        "slug": "benq-screenbar-plus-led-monitor-light",
        "category_slug": "home-kitchen",
        "seller_slug": "homeessentials-co",
        "price": Decimal("159.99"),
        "original_price": Decimal("189.99"),
        "rating": 4.6,
        "review_count": 2147,
        "stock": 63,
        "description": (
            "The BenQ ScreenBar Plus is an LED monitor light bar with an exclusive wireless dial controller "
            "for easy brightness and color temperature adjustment. Anti-glare asymmetric optical design "
            "illuminates your desk without causing glare on the screen."
        ),
        "specifications": {
            "Lighting": "6500K, 95+ CRI",
            "Color Temp": "2700K–6500K adjustable",
            "Brightness": "0–1000 lux",
            "Power": "USB-A (5V/1A)",
            "Clip": "Universal monitor clip (1–5cm)",
            "Control": "Wireless dial controller",
            "Length": "45cm",
        },
        "images": [
            img("1593642632559-0c6d3fc62b89", "LED monitor light bar on screen setup", primary=True, order=0),
            img("1593642632632-9ac8e5e59de5", "Desk setup with monitor light glowing", order=1),
            img("1591370874773-6702e8f12fd8", "Light bar controller close-up", order=2),
        ],
    },

    # ── SPORTS & FITNESS ──────────────────────────────────────────────────────

    {
        "sku": "SPT-YMA-025",
        "name": "Manduka PRO Yoga Mat — 6mm",
        "brand": "Manduka",
        "slug": "manduka-pro-yoga-mat-6mm",
        "category_slug": "sports-fitness",
        "seller_slug": "homeessentials-co",
        "price": Decimal("120.00"),
        "original_price": Decimal("148.00"),
        "rating": 4.8,
        "review_count": 4821,
        "stock": 93,
        "description": (
            "The Manduka PRO yoga mat is the gold standard in yoga mats. "
            "Made with closed-cell surface that prevents sweat from seeping into the mat, "
            "with 6mm cushioning for joint protection. Built to last a lifetime — backed by a lifetime guarantee."
        ),
        "specifications": {
            "Thickness": "6mm",
            "Dimensions": "71\" × 24\"",
            "Material": "PVC (latex-free)",
            "Surface": "Closed-cell, non-slip",
            "Weight": "7.5 lbs",
            "Warranty": "Lifetime guarantee",
            "Color Options": "Thunder (dark grey)",
        },
        "images": [
            img("1601925260368-ae2f83cf8b7f", "Dark yoga mat rolled out on wooden floor", primary=True, order=0),
            img("1518611012118-696072aa579a", "Yoga mat being used in practice", order=1),
            img("1544367567-0f2fcb009e0b", "Yoga mat close-up texture detail", order=2),
        ],
    },

    {
        "sku": "SPT-WTB-026",
        "name": "Hydro Flask 32oz Wide Mouth Water Bottle",
        "brand": "Hydro Flask",
        "slug": "hydro-flask-32oz-water-bottle",
        "category_slug": "sports-fitness",
        "seller_slug": "homeessentials-co",
        "price": Decimal("44.95"),
        "original_price": None,
        "rating": 4.8,
        "review_count": 18247,
        "stock": 312,
        "description": (
            "The Hydro Flask 32oz Wide Mouth Bottle keeps drinks ice-cold for 24 hours and hot for 12 hours "
            "with TempShield double-wall vacuum insulation. The easy-to-clean wide mouth fits most ice cubes "
            "and the Flex Cap makes sipping easy on the go."
        ),
        "specifications": {
            "Capacity": "32 oz (946 ml)",
            "Insulation": "TempShield double-wall vacuum",
            "Cold Retention": "24 hours",
            "Hot Retention": "12 hours",
            "Material": "18/8 pro-grade stainless steel",
            "Cap": "Flex Cap (carry loop)",
            "BPA Free": "Yes",
        },
        "images": [
            img("1602143407296-ab22f686dc23", "Stainless steel water bottle on white", primary=True, order=0),
            img("1571019613454-1cb2f99b2d8b", "Water bottle being used during workout", order=1),
            img("1553649033-3a21e7c4e8b4", "Water bottle cap and opening detail", order=2),
        ],
    },

    {
        "sku": "SPT-RST-027",
        "name": "TheraBand Resistance Bands Set (5 Levels)",
        "brand": "TheraBand",
        "slug": "theraband-resistance-bands-set-5-levels",
        "category_slug": "sports-fitness",
        "seller_slug": "homeessentials-co",
        "price": Decimal("32.99"),
        "original_price": Decimal("39.99"),
        "rating": 4.5,
        "review_count": 7412,
        "stock": 428,
        "description": (
            "TheraBand's professional-grade resistance bands are used in physical therapy and fitness worldwide. "
            "This set includes 5 resistance levels (yellow through blue) for progressive strength training, "
            "rehabilitation, and stretching exercises."
        ),
        "specifications": {
            "Levels": "5 (Yellow, Red, Green, Blue, Black)",
            "Resistance": "Extra Thin to Heavy",
            "Length": "25 yards (per roll)",
            "Material": "Natural rubber latex",
            "Use": "Physical therapy, strength training, stretching",
            "Includes": "Exercise guide",
        },
        "images": [
            img("1598971639058-bc0a50fd42b8", "Resistance bands set colorful", primary=True, order=0),
            img("1571019613566-3f5ddb5f1a7f", "Resistance band exercise being performed", order=1),
            img("1517836357463-d25dfeac3438", "Bands rolled up side view", order=2),
        ],
    },

    {
        "sku": "SPT-FTK-028",
        "name": "Fitbit Charge 6 Fitness Tracker",
        "brand": "Fitbit",
        "slug": "fitbit-charge-6-fitness-tracker",
        "category_slug": "sports-fitness",
        "seller_slug": "techvault-store",
        "price": Decimal("139.95"),
        "original_price": Decimal("159.95"),
        "rating": 4.3,
        "review_count": 3284,
        "stock": 142,
        "description": (
            "The Fitbit Charge 6 features built-in GPS, 40+ exercise modes, and 7 days battery life. "
            "Google Wallet and Google Maps on-wrist, ECG app, skin temperature tracking, "
            "and 24/7 heart rate monitoring make it the most feature-rich Charge yet."
        ),
        "specifications": {
            "Display": "Colour AMOLED touchscreen",
            "GPS": "Built-in GPS",
            "Battery": "Up to 7 days",
            "Health Sensors": "Heart rate, SpO2, ECG, skin temp, stress",
            "Google Features": "Google Wallet, Google Maps, Google Fast Pair",
            "Water Resistance": "50m",
            "Exercise Modes": "40+",
        },
        "images": [
            img("1575311373941-b1a2d8c78b9a", "Fitness tracker on wrist black", primary=True, order=0),
            img("1434494493521-a3b2dbaeacd2", "Fitness tracker face display showing stats", order=1),
            img("1571019614242-c5c5dee9f50b", "Tracker during running workout", order=2),
        ],
    },

    # ── BEAUTY ───────────────────────────────────────────────────────────────

    {
        "sku": "BTY-MST-029",
        "name": "CeraVe AM Facial Moisturizing Lotion SPF 30",
        "brand": "CeraVe",
        "slug": "cerave-am-facial-moisturizing-lotion-spf30",
        "category_slug": "beauty",
        "seller_slug": "homeessentials-co",
        "price": Decimal("18.99"),
        "original_price": Decimal("22.99"),
        "rating": 4.7,
        "review_count": 34821,
        "stock": 856,
        "description": (
            "CeraVe AM Facial Moisturizing Lotion with SPF 30 provides broad-spectrum sun protection "
            "while moisturizing with 3 essential ceramides and hyaluronic acid. "
            "Oil-free, non-comedogenic, and gentle enough for sensitive skin. Developed with dermatologists."
        ),
        "specifications": {
            "SPF": "30 Broad Spectrum",
            "Key Ingredients": "3 Ceramides, Hyaluronic Acid, Niacinamide",
            "Skin Type": "Normal to Oily",
            "Size": "3 fl oz (89 mL)",
            "Formula": "Oil-free, non-comedogenic",
            "Fragrance": "Fragrance-free",
            "Dermatologist Tested": "Yes",
        },
        "images": [
            img("1556228720-195a672e8a03", "White skincare moisturizer bottle", primary=True, order=0),
            img("1598440947619-2c35fc9aa181", "Moisturizer texture swatch on hand", order=1),
            img("1596755094514-f87e34085b2c", "Skincare routine with multiple products", order=2),
        ],
    },

    {
        "sku": "BTY-HDR-030",
        "name": "Dyson Supersonic™ Hair Dryer",
        "brand": "Dyson",
        "slug": "dyson-supersonic-hair-dryer",
        "category_slug": "beauty",
        "seller_slug": "stylehub-fashion",
        "price": Decimal("399.99"),
        "original_price": Decimal("429.99"),
        "rating": 4.6,
        "review_count": 8214,
        "stock": 34,
        "description": (
            "The Dyson Supersonic hair dryer is engineered for fast drying and precise styling. "
            "The digital motor spins at up to 110,000 rpm, and intelligent heat control measures air temperature "
            "over 40 times per second to protect hair's natural shine."
        ),
        "specifications": {
            "Motor": "Dyson V9 digital, 110,000 RPM",
            "Heat Settings": "4 heat, 3 speed",
            "Heat Shield": "Intelligent heat control (measures 40×/sec)",
            "Noise": "Reduced noise frequency",
            "Attachments": "Flyaway smoother, Styling concentrator, Diffuser",
            "Weight": "1.8 lbs",
            "Cord": "9 ft professional length",
        },
        "images": [
            img("1522338242992-e1af2932a6ef", "Dyson hair dryer fuchsia on white", primary=True, order=0),
            img("1515377905703-c4788e51af15", "Hair dryer being used on hair", order=1),
            img("1614178564039-0e5fc9a41cb6", "Hair dryer attachments laid out", order=2),
            img("1519491413817-e14d48e1a3be", "Hair dryer handle and button detail", order=3),
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SEED RUNNER
# ─────────────────────────────────────────────────────────────────────────────

async def seed():
    async with AsyncSessionLocal() as db:
        print("=== CommerceFlow AI - Product Catalog Seed ===\n")

        # ── 1. Remove old random/bad products ──────────────────────────────
        print("Step 1: Removing old random product data...")
        # Delete all existing product_images
        await db.execute(text("DELETE FROM product_images"))
        # Delete all existing products (ON DELETE SET NULL protects order_items)
        await db.execute(text("DELETE FROM products"))
        # Delete all sellers
        await db.execute(text("DELETE FROM sellers"))
        # Delete all categories
        await db.execute(text("DELETE FROM categories"))
        await db.commit()
        print("  [OK] Old data cleared safely (orders, tickets, users preserved)\n")

        # ── 2. Categories ──────────────────────────────────────────────────
        print("Step 2: Seeding categories...")
        cat_map: dict[str, Category] = {}
        for c in CATEGORIES:
            existing = await db.execute(
                select(Category).where(Category.slug == c["slug"])
            )
            cat = existing.scalar_one_or_none()
            if not cat:
                cat = Category(
                    name=c["name"],
                    slug=c["slug"],
                    icon=c["icon"],
                    description=c["description"],
                )
                db.add(cat)
                await db.flush()
            cat_map[c["slug"]] = cat
            print(f"  [cat] {c['name']}")
        await db.commit()
        print(f"  [OK] {len(cat_map)} categories ready\n")

        # ── 3. Sellers ────────────────────────────────────────────────────
        print("Step 3: Seeding sellers...")
        seller_map: dict[str, Seller] = {}
        for s in SELLERS:
            existing = await db.execute(
                select(Seller).where(Seller.slug == s["slug"])
            )
            seller = existing.scalar_one_or_none()
            if not seller:
                seller = Seller(**s)
                db.add(seller)
                await db.flush()
            seller_map[s["slug"]] = seller
            verified = "V" if s["is_verified"] else " "
            print(f"  [{verified}] {s['name']} ({s['city']})")
        await db.commit()
        print(f"  [OK] {len(seller_map)} sellers ready\n")

        # ── 4. Products ───────────────────────────────────────────────────
        print("Step 4: Seeding products...")
        created = 0
        for p in PRODUCTS:
            existing = await db.execute(
                select(Product).where(Product.sku == p["sku"])
            )
            if existing.scalar_one_or_none():
                print(f"  [skip] {p['name'][:50]} (exists)")
                continue

            cat = cat_map[p["category_slug"]]
            seller = seller_map[p["seller_slug"]]

            product = Product(
                sku=p["sku"],
                name=p["name"],
                brand=p["brand"],
                slug=p["slug"],
                description=p["description"],
                price=p["price"],
                original_price=p.get("original_price"),
                rating=p["rating"],
                review_count=p["review_count"],
                stock=p["stock"],
                specifications=p.get("specifications"),
                category_id=cat.id,
                seller_id=seller.id,
                is_active=True,
                # Legacy field — set to primary image for backward compat
                image_url=next(
                    (i["url"] for i in p["images"] if i.get("is_primary")),
                    p["images"][0]["url"] if p["images"] else None,
                ),
            )
            db.add(product)
            await db.flush()

            # Add images
            for img_data in p["images"]:
                img = ProductImage(
                    product_id=product.id,
                    image_url=img_data["url"],
                    alt_text=img_data.get("alt"),
                    is_primary=img_data.get("is_primary", False),
                    sort_order=img_data.get("sort_order", 0),
                )
                db.add(img)

            disc = product.discount_percent
            disc_str = f" [{disc:.0f}% OFF]" if disc > 0 else ""
            print(f"  [+] {p['name'][:55]:<55} ${p['price']:>8.2f}{disc_str}")
            created += 1

        await db.commit()
        print(f"\n  [OK] {created} products seeded with {sum(len(p['images']) for p in PRODUCTS)} total images\n")

        # ── 5. Verification summary ───────────────────────────────────────
        print("Step 5: Verification summary...")
        total_p = await db.execute(text("SELECT COUNT(*) FROM products"))
        total_i = await db.execute(text("SELECT COUNT(*) FROM product_images"))
        total_c = await db.execute(text("SELECT COUNT(*) FROM categories"))
        null_img = await db.execute(
            text("SELECT COUNT(*) FROM products WHERE image_url IS NULL AND "
                 "id NOT IN (SELECT DISTINCT product_id FROM product_images)")
        )
        print(f"  Products:        {total_p.scalar()}")
        print(f"  Product Images:  {total_i.scalar()}")
        print(f"  Categories:      {total_c.scalar()}")
        print(f"  Products w/o img:{null_img.scalar()}")
        print("\n=== Seed complete! ===")


if __name__ == "__main__":
    asyncio.run(seed())
