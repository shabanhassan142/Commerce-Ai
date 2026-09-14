"""
app/database/seed.py

Faker-powered seed script that populates the database with
realistic e-commerce marketplace data.

Usage:
    cd backend
    venv\\Scripts\\python.exe -m app.database.seed
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.password import hash_password
from app.config.settings import get_settings
from app.database.base import Base
from app.models import (
    Address,
    AgentLog,
    Category,
    Conversation,
    Customer,
    MessageRole,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Product,
    Return,
    ReturnReason,
    ReturnStatus,
    Seller,
    SupportTicket,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

settings = get_settings()

# ── Realistic product data ────────────────────────────────────────────────────

CATEGORIES = [
    {"name": "Electronics", "slug": "electronics", "icon": "💻", "description": "Phones, laptops, tablets, and accessories"},
    {"name": "Fashion", "slug": "fashion", "icon": "👗", "description": "Clothing, shoes, and accessories for all"},
    {"name": "Beauty & Health", "slug": "beauty-health", "icon": "💄", "description": "Skincare, makeup, and wellness products"},
    {"name": "Home & Living", "slug": "home-living", "icon": "🏠", "description": "Furniture, decor, and home essentials"},
    {"name": "Sports & Outdoors", "slug": "sports-outdoors", "icon": "⚽", "description": "Sports equipment and outdoor gear"},
    {"name": "Books & Stationery", "slug": "books-stationery", "icon": "📚", "description": "Books, notebooks, and office supplies"},
    {"name": "Toys & Games", "slug": "toys-games", "icon": "🎮", "description": "Toys, board games, and video games"},
    {"name": "Groceries", "slug": "groceries", "icon": "🛒", "description": "Food, beverages, and household essentials"},
    {"name": "Automotive", "slug": "automotive", "icon": "🚗", "description": "Car accessories and maintenance products"},
    {"name": "Baby & Kids", "slug": "baby-kids", "icon": "👶", "description": "Baby care, kids clothing, and toys"},
    {"name": "Pet Supplies", "slug": "pet-supplies", "icon": "🐾", "description": "Food, accessories, and care for pets"},
    {"name": "Jewelry & Watches", "slug": "jewelry-watches", "icon": "💎", "description": "Rings, necklaces, watches, and luxury items"},
]

PRODUCT_TEMPLATES = {
    "electronics": [
        ("Wireless Bluetooth Earbuds Pro", (1500, 8000)),
        ("USB-C Fast Charging Cable 2m", (300, 1200)),
        ("Laptop Cooling Pad with Fan", (2000, 5000)),
        ("Mechanical Gaming Keyboard RGB", (3000, 12000)),
        ("Portable Power Bank 20000mAh", (1500, 4000)),
        ("Smartphone Screen Protector Pack", (200, 800)),
        ("Wireless Mouse Ergonomic", (800, 3000)),
        ("Webcam HD 1080p with Mic", (2000, 6000)),
        ("Smart Watch Fitness Tracker", (3000, 15000)),
        ("Noise Cancelling Headphones", (5000, 20000)),
    ],
    "fashion": [
        ("Cotton Crew Neck T-Shirt", (500, 2000)),
        ("Slim Fit Denim Jeans", (1500, 4000)),
        ("Running Shoes Lightweight", (2000, 8000)),
        ("Leather Belt Classic", (600, 2500)),
        ("Sunglasses UV Protection", (500, 3000)),
        ("Winter Hoodie Fleece Lined", (1500, 4500)),
        ("Formal Dress Shirt", (1200, 3500)),
        ("Canvas Backpack 30L", (1000, 3500)),
        ("Sports Socks Pack of 6", (400, 1200)),
        ("Woolen Scarf Premium", (800, 2500)),
    ],
    "beauty-health": [
        ("Vitamin C Serum 30ml", (800, 2500)),
        ("Moisturizing Face Cream SPF 50", (600, 2000)),
        ("Hair Growth Oil Natural", (400, 1500)),
        ("Electric Toothbrush Sonic", (2000, 6000)),
        ("Protein Powder Whey 1kg", (3000, 8000)),
        ("Lip Balm Set of 4", (300, 900)),
        ("Facial Cleanser Foam", (500, 1500)),
        ("Perfume Eau de Toilette 100ml", (2000, 8000)),
        ("Nail Polish Set Gel", (600, 1800)),
        ("Hand Sanitizer Pack 500ml", (200, 600)),
    ],
    "home-living": [
        ("LED Desk Lamp Adjustable", (1000, 3500)),
        ("Bedsheet Set Cotton King", (1500, 5000)),
        ("Wall Clock Minimalist", (800, 2500)),
        ("Kitchen Knife Set 5pc", (2000, 6000)),
        ("Throw Pillow Cover 2pc", (400, 1200)),
        ("Storage Box Organizer Set", (600, 2000)),
        ("Non-stick Frying Pan 28cm", (800, 3000)),
        ("Bath Towel Set Premium", (1000, 3500)),
        ("Air Freshener Automatic", (500, 1500)),
        ("Plant Pot Ceramic Set", (700, 2500)),
    ],
}

SELLER_NAMES = [
    "TechZone Store", "Fashion Forward", "GlowUp Beauty", "HomeNest",
    "SportMax", "BookWorm Central", "GameWorld", "FreshMart",
    "AutoParts Hub", "BabyBliss", "PetParadise", "LuxeJewels",
    "Digital Dreams", "StyleCraft", "WellnessFirst", "CozyHome Plus",
    "ActiveLife Pro", "PageTurner Books", "PlayZone", "GreenGrocer",
    "MotoGear", "KiddieLand", "PawFriends", "GemStone Gallery",
    "MegaTech", "TrendSetters", "PureBeauty", "NestDecor",
    "FitGear Shop", "SmartGadgets",
]

PAKISTAN_CITIES = [
    "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad",
    "Peshawar", "Quetta", "Multan", "Sialkot", "Gujranwala",
]

TICKET_SUBJECTS = [
    "Order not received", "Wrong item delivered", "Damaged product",
    "Payment deducted but order failed", "Need to change delivery address",
    "How to initiate a return?", "Coupon code not working",
    "Product quality issue", "Delivery delayed beyond estimate",
    "Refund not processed yet", "Account login issue",
    "Cannot track my order", "Want to cancel order",
    "Missing items in package", "Warranty claim request",
]

AGENT_NAMES = ["supervisor", "order", "refund", "billing", "product", "knowledge", "support"]


async def seed_database():
    """Main seeding function."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(text("SELECT COUNT(*) FROM customers"))
        count = result.scalar()
        if count and count > 0:
            print(f"⚠️  Database already has {count} customers. Skipping seed.")
            print("   To re-seed, truncate tables first.")
            await engine.dispose()
            return

        print("Seeding CommerceFlow AI database...")
        print("=" * 60)

        # ── 1. Admin + Support Users ──────────────────────────────────
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@commerceflow.ai",
            full_name="Admin User",
            hashed_password=hash_password("Admin123!"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        support_user = User(
            id=uuid.uuid4(),
            email="support@commerceflow.ai",
            full_name="Support Agent",
            hashed_password=hash_password("Support123!"),
            role=UserRole.SUPPORT,
            is_active=True,
            is_verified=True,
        )
        session.add_all([admin_user, support_user])
        print("[+] Created admin and support users")

        # ── 2. Customer Users ─────────────────────────────────────────
        users: list[User] = []
        customers: list[Customer] = []
        for i in range(100):
            user = User(
                id=uuid.uuid4(),
                email=f"customer{i+1}@example.com",
                full_name=fake.name(),
                hashed_password=hash_password("Customer123!"),
                role=UserRole.CUSTOMER,
                is_active=True,
                is_verified=random.choice([True, True, True, False]),
            )
            users.append(user)
            session.add(user)

        await session.flush()  # Get user IDs

        for user in users:
            customer = Customer(
                id=uuid.uuid4(),
                user_id=user.id,
                phone=f"+92{random.randint(3000000000, 3999999999)}",
                loyalty_points=random.randint(0, 5000),
            )
            customers.append(customer)
            session.add(customer)

        await session.flush()
        print(f"[+] Created {len(users)} customer users + profiles")

        # ── 3. Addresses ──────────────────────────────────────────────
        all_addresses: list[Address] = []
        for customer in customers:
            num_addresses = random.randint(1, 3)
            for j in range(num_addresses):
                city = random.choice(PAKISTAN_CITIES)
                addr = Address(
                    id=uuid.uuid4(),
                    customer_id=customer.id,
                    label=["home", "office", "other"][j % 3],
                    street=fake.street_address(),
                    city=city,
                    state=city,  # simplified
                    postal_code=str(random.randint(10000, 99999)),
                    country="Pakistan",
                    is_default=(j == 0),
                )
                all_addresses.append(addr)
                session.add(addr)

        await session.flush()
        print(f"[+] Created {len(all_addresses)} addresses")

        # ── 4. Categories ─────────────────────────────────────────────
        categories: list[Category] = []
        for cat_data in CATEGORIES:
            cat = Category(id=uuid.uuid4(), **cat_data)
            categories.append(cat)
            session.add(cat)

        await session.flush()
        print(f"[+] Created {len(categories)} categories")

        # ── 5. Sellers ────────────────────────────────────────────────
        sellers: list[Seller] = []
        for name in SELLER_NAMES:
            slug = name.lower().replace(" ", "-").replace("'", "")
            seller = Seller(
                id=uuid.uuid4(),
                name=name,
                slug=slug,
                email=f"{slug}@marketplace.pk",
                phone=f"+92{random.randint(3000000000, 3999999999)}",
                rating=round(random.uniform(3.2, 5.0), 1),
                is_verified=random.choice([True, True, False]),
                city=random.choice(PAKISTAN_CITIES),
                country="Pakistan",
            )
            sellers.append(seller)
            session.add(seller)

        await session.flush()
        print(f"[+] Created {len(sellers)} sellers")

        # ── 6. Products ───────────────────────────────────────────────
        products: list[Product] = []
        sku_counter = 1000
        category_slug_map = {c.slug: c for c in categories}

        for cat_slug, templates in PRODUCT_TEMPLATES.items():
            cat = category_slug_map.get(cat_slug)
            if not cat:
                continue
            for template_name, price_range in templates:
                for variant in range(random.randint(2, 4)):
                    sku_counter += 1
                    price = Decimal(str(random.randint(*price_range)))
                    variant_name = f"{template_name} - {fake.color_name()}"
                    slug = f"{variant_name.lower().replace(' ', '-').replace('---', '-')[:250]}-{sku_counter}"

                    product = Product(
                        id=uuid.uuid4(),
                        name=variant_name,
                        slug=slug,
                        description=fake.paragraph(nb_sentences=4),
                        price=price,
                        discount_percent=random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30]),
                        sku=f"SKU-{sku_counter:05d}",
                        stock=random.randint(0, 500),
                        rating=round(random.uniform(2.5, 5.0), 1),
                        review_count=random.randint(0, 800),
                        image_url=f"https://picsum.photos/seed/{sku_counter}/400/400",
                        is_active=random.choice([True, True, True, True, False]),
                        category_id=cat.id,
                        seller_id=random.choice(sellers).id,
                    )
                    products.append(product)
                    session.add(product)

        await session.flush()
        print(f"[+] Created {len(products)} products")

        # ── 7. Orders & OrderItems ────────────────────────────────────
        orders: list[Order] = []
        order_counter = 0
        now = datetime.now(timezone.utc)

        for i in range(500):
            order_counter += 1
            customer = random.choice(customers)
            customer_addresses = [a for a in all_addresses if a.customer_id == customer.id]
            order_date = now - timedelta(days=random.randint(1, 180))
            status = random.choice(list(OrderStatus))

            order = Order(
                id=uuid.uuid4(),
                order_number=f"CF-{order_date.strftime('%Y%m%d')}-{order_counter:03d}",
                customer_id=customer.id,
                status=status,
                total_amount=Decimal("0"),
                shipping_address_id=customer_addresses[0].id if customer_addresses else None,
                tracking_number=f"PK{random.randint(100000000, 999999999)}" if status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED] else None,
                estimated_delivery=order_date + timedelta(days=random.randint(3, 10)) if status != OrderStatus.CANCELLED else None,
                delivered_at=order_date + timedelta(days=random.randint(3, 8)) if status == OrderStatus.DELIVERED else None,
            )

            # Add 1-5 items
            num_items = random.randint(1, 5)
            total = Decimal("0")
            for _ in range(num_items):
                product = random.choice(products)
                qty = random.randint(1, 3)
                unit_price = product.price
                item_total = unit_price * qty
                total += item_total

                item = OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=item_total,
                )
                session.add(item)

            order.total_amount = total
            orders.append(order)
            session.add(order)

        await session.flush()
        print(f"[+] Created {len(orders)} orders with items")

        # ── 8. Payments ───────────────────────────────────────────────
        for order in orders:
            method = random.choice(list(PaymentMethod))
            if order.status in [OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]:
                pay_status = PaymentStatus.COMPLETED
            elif order.status == OrderStatus.CANCELLED:
                pay_status = random.choice([PaymentStatus.FAILED, PaymentStatus.REFUNDED])
            else:
                pay_status = random.choice([PaymentStatus.PENDING, PaymentStatus.COMPLETED])

            payment = Payment(
                id=uuid.uuid4(),
                order_id=order.id,
                method=method,
                status=pay_status,
                amount=order.total_amount,
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}" if pay_status == PaymentStatus.COMPLETED else None,
                paid_at=order.created_at + timedelta(minutes=random.randint(1, 30)) if pay_status == PaymentStatus.COMPLETED else None,
            )
            session.add(payment)

        await session.flush()
        print(f"[+] Created {len(orders)} payments")

        # ── 9. Returns (~10% of delivered orders) ─────────────────────
        delivered_orders = [o for o in orders if o.status == OrderStatus.DELIVERED]
        return_orders = random.sample(delivered_orders, min(50, len(delivered_orders)))
        for order in return_orders:
            ret = Return(
                id=uuid.uuid4(),
                order_id=order.id,
                reason=random.choice(list(ReturnReason)),
                status=random.choice(list(ReturnStatus)),
                refund_amount=order.total_amount * Decimal(str(random.uniform(0.5, 1.0))),
                description=fake.sentence(nb_words=12),
            )
            if ret.status in [ReturnStatus.REFUNDED, ReturnStatus.COMPLETED]:
                ret.resolved_at = order.created_at + timedelta(days=random.randint(3, 14))
            session.add(ret)

        await session.flush()
        print(f"[+] Created {len(return_orders)} return requests")

        # ── 10. Support Tickets ───────────────────────────────────────
        tickets_created = 0
        for _ in range(80):
            customer = random.choice(customers)
            customer_orders = [o for o in orders if o.customer_id == customer.id]
            ticket_date = now - timedelta(days=random.randint(1, 90))
            tickets_created += 1

            ticket = SupportTicket(
                id=uuid.uuid4(),
                ticket_number=f"TK-{ticket_date.strftime('%Y%m%d')}-{tickets_created:03d}",
                customer_id=customer.id,
                order_id=customer_orders[0].id if customer_orders and random.random() > 0.3 else None,
                subject=random.choice(TICKET_SUBJECTS),
                description=fake.paragraph(nb_sentences=3),
                priority=random.choice(list(TicketPriority)),
                status=random.choice(list(TicketStatus)),
                assigned_to=support_user.id if random.random() > 0.4 else None,
            )
            if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                ticket.resolved_at = ticket_date + timedelta(days=random.randint(1, 5))
            session.add(ticket)

        await session.flush()
        print(f"[+] Created {tickets_created} support tickets")

        # ── 11. Conversations & Agent Logs ────────────────────────────
        conversations_created = 0
        logs_created = 0
        for _ in range(60):
            customer = random.choice(customers)
            conversations_created += 1

            conv = Conversation(
                id=uuid.uuid4(),
                customer_id=customer.id,
                title=random.choice([
                    "Order inquiry", "Track my package",
                    "Return request", "Product question",
                    "Billing issue", "General support",
                    "Warranty help", "Account help",
                ]),
                is_active=random.choice([True, True, False]),
            )
            session.add(conv)
            await session.flush()

            # 3-8 messages per conversation
            num_messages = random.randint(3, 8)
            msg_time = now - timedelta(days=random.randint(1, 60))
            for m in range(num_messages):
                role = MessageRole.USER if m % 2 == 0 else MessageRole.ASSISTANT
                agent = random.choice(AGENT_NAMES) if role == MessageRole.ASSISTANT else "user"

                log = AgentLog(
                    id=uuid.uuid4(),
                    conversation_id=conv.id,
                    agent_name=agent,
                    role=role,
                    content=fake.paragraph(nb_sentences=2) if role == MessageRole.USER else fake.paragraph(nb_sentences=3),
                    intent=random.choice([
                        "order_status", "track_order", "return_request",
                        "product_inquiry", "billing_question", "general_support",
                        None, None,
                    ]) if role == MessageRole.USER else None,
                    confidence=round(random.uniform(0.7, 0.99), 2) if role == MessageRole.ASSISTANT else None,
                    tokens_used=random.randint(50, 500) if role == MessageRole.ASSISTANT else None,
                    response_time_ms=random.randint(200, 3000) if role == MessageRole.ASSISTANT else None,
                )
                msg_time += timedelta(seconds=random.randint(5, 120))
                session.add(log)
                logs_created += 1

            conv.last_message_at = msg_time

        await session.flush()
        print(f"[+] Created {conversations_created} conversations with {logs_created} agent logs")

        # ── Commit everything ─────────────────────────────────────────
        await session.commit()

        print()
        print("=" * 60)
        print("Database seeded successfully!")
        print("=" * 60)
        print(f"   Users:          {len(users) + 2}")
        print(f"   Customers:      {len(customers)}")
        print(f"   Addresses:      {len(all_addresses)}")
        print(f"   Categories:     {len(categories)}")
        print(f"   Sellers:        {len(sellers)}")
        print(f"   Products:       {len(products)}")
        print(f"   Orders:         {len(orders)}")
        print(f"   Payments:       {len(orders)}")
        print(f"   Returns:        {len(return_orders)}")
        print(f"   Tickets:        {tickets_created}")
        print(f"   Conversations:  {conversations_created}")
        print(f"   Agent Logs:     {logs_created}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())

