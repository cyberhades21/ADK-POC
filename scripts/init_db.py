"""Run once to create and seed the SQLite database: python -m scripts.init_db"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.services.db import get_conn

def init():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id      TEXT PRIMARY KEY,
            status        TEXT NOT NULL,
            eta           TEXT,
            carrier       TEXT,
            customer_name TEXT,
            can_cancel    INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS products (
            product_id  TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            price       INTEGER NOT NULL,
            stock       INTEGER DEFAULT 0,
            description TEXT
        );
    """)

    orders = [
        ("ORD-001", "Shipped",           "18 Jun 2026", "BlueDart",   "Aarav Shah",       0),
        ("ORD-002", "Processing",        "20 Jun 2026", "DTDC",       "Priya Menon",      1),
        ("ORD-003", "Delivered",         "10 Jun 2026", "FedEx",      "Rohan Verma",      0),
        ("ORD-004", "Out for Delivery",  "Today",       "Delhivery",  "Sara Khan",        0),
        ("ORD-005", "Cancelled",         "N/A",         "N/A",        "Dev Patel",        0),
        ("ORD-006", "Processing",        "22 Jun 2026", "BlueDart",   "Ananya Iyer",      1),
        ("ORD-007", "Shipped",           "19 Jun 2026", "Ecom Express","Vikram Nair",     0),
        ("ORD-008", "Delivered",         "8 Jun 2026",  "DTDC",       "Meera Pillai",     0),
        ("ORD-009", "Shipped",           "21 Jun 2026", "FedEx",      "Arjun Mehta",      0),
        ("ORD-010", "Processing",        "23 Jun 2026", "Delhivery",  "Kavya Reddy",      1),
        ("ORD-011", "Out for Delivery",  "Today",       "BlueDart",   "Rahul Gupta",      0),
        ("ORD-012", "Delivered",         "12 Jun 2026", "Ecom Express","Sneha Joshi",     0),
        ("ORD-013", "Shipped",           "20 Jun 2026", "DTDC",       "Aditya Kumar",     0),
        ("ORD-014", "Cancelled",         "N/A",         "N/A",        "Pooja Sharma",     0),
        ("ORD-015", "Processing",        "24 Jun 2026", "FedEx",      "Kiran Rao",        1),
        ("ORD-016", "Shipped",           "18 Jun 2026", "BlueDart",   "Divya Krishnan",   0),
        ("ORD-017", "Delivered",         "9 Jun 2026",  "Delhivery",  "Suresh Babu",      0),
        ("ORD-018", "Out for Delivery",  "Today",       "DTDC",       "Lakshmi Nair",     0),
        ("ORD-019", "Processing",        "25 Jun 2026", "Ecom Express","Nikhil Bhatt",    1),
        ("ORD-020", "Shipped",           "22 Jun 2026", "FedEx",      "Riya Desai",       0),
        ("ORD-021", "Delivered",         "11 Jun 2026", "BlueDart",   "Sameer Patil",     0),
        ("ORD-022", "Processing",        "26 Jun 2026", "DTDC",       "Neha Jain",        1),
        ("ORD-023", "Shipped",           "23 Jun 2026", "Delhivery",  "Manish Tiwari",    0),
        ("ORD-024", "Cancelled",         "N/A",         "N/A",        "Deepa Menon",      0),
        ("ORD-025", "Out for Delivery",  "Today",       "Ecom Express","Rajesh Kumar",    0),
    ]
    c.executemany("INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?)", orders)

    products = [
        ("PRD-001", "Samsung Galaxy A55",          32999, 15,
         "6.6-inch AMOLED display, 50MP triple camera, 5000mAh battery, 8GB RAM. 1 year manufacturer warranty."),
        ("PRD-002", "Redmi Note 13",               17999, 28,
         "6.67-inch AMOLED display, 108MP camera, 5000mAh battery, 6GB RAM. 1 year manufacturer warranty."),
        ("PRD-003", "Samsung 43-inch 4K Smart TV", 42999, 7,
         "4K UHD resolution, Smart TV with built-in streaming apps, 3 HDMI ports. 2 year manufacturer warranty."),
        ("PRD-004", "DStv HD Decoder",             3499,  40,
         "Full HD satellite decoder, compatible with all DStv packages, single view. 1 year warranty."),
        ("PRD-005", "USB-C Charging Cable 2m",     499,   120,
         "Braided 2-metre USB-C to USB-C cable, supports 65W fast charging. Universal compatibility."),
        ("PRD-006", "OnePlus Nord CE 4",           24999, 20,
         "6.7-inch AMOLED display, 50MP camera, 5500mAh battery, 8GB RAM, 100W fast charging. 1 year warranty."),
        ("PRD-007", "Sony 55-inch 4K OLED TV",    129999, 3,
         "OLED 4K display, Dolby Vision and Atmos, Google TV built-in. 2 year warranty."),
        ("PRD-008", "Realme Buds T310",            1999,  55,
         "True wireless earbuds, ANC, 40-hour total battery life, IPX5 water resistant."),
        ("PRD-009", "Logitech MX Keys Mini",       7999,  18,
         "Compact wireless keyboard, backlit keys, Bluetooth multi-device, USB-C charging."),
        ("PRD-010", "Samsung 1TB Portable SSD",    8499,  25,
         "USB 3.2 Gen 2 portable SSD, 1050MB/s read speed, shock resistant, 3 year warranty."),
    ]
    c.executemany("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?)", products)

    conn.commit()
    conn.close()
    print(f"Database seeded — {len(orders)} orders, {len(products)} products.")
    print(f"Location: {os.path.abspath('ecombot.db')}")

if __name__ == "__main__":
    init()
