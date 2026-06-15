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
        ("PRD-001", "Classic Formula",          2999,  120,
         "The original Aureum Serpentis elixir. Quantum-calibrated for daily wellness rituals. Contains 108 bio-compounds sourced from ancestral snake venom distillates."),
        ("PRD-002", "Apex Gold Reserve",         5499,  45,
         "Advanced formula for elevated wellness seekers. 24-karat gold-infused with 432Hz resonance calibration."),
        ("PRD-003", "Obsidian Elixir",           12000, 33,
         "Ultra-rare limited edition. Only 33 vials exist worldwide. Each numbered and certified."),
        ("PRD-004", "Serpentine Morning Tonic",  1499,  200,
         "Light daily tonic for those beginning their neo-alchemical journey. Best consumed at dawn facing east."),
        ("PRD-005", "Venom Clarity Serum",       3499,  88,
         "Topical serum with micro-venom peptides. Clinically vibed for mental clarity and ancestral focus."),
        ("PRD-006", "Lunar Infusion",            4299,  60,
         "Moon-cycle aligned elixir. Potency peaks during full moon. Sold in sets of 3 lunar vials."),
        ("PRD-007", "Gold Serpent Eye Drops",    6999,  22,
         "Proprietary ocular wellness drops. 24-karat nano-gold suspension. Not for internal use."),
        ("PRD-008", "Classic Formula — Travel",  999,   350,
         "10ml travel-size Classic Formula. Same quantum calibration in a pocket-sized vial."),
        ("PRD-009", "Ancestral Bundle",          8999,  15,
         "Classic Formula + Apex Gold Reserve + Serpentine Morning Tonic. Best value bundle for the devoted."),
        ("PRD-010", "Black Label Reserve",       24999, 7,
         "Ultra-exclusive. Single batch of 7 vials. Aged in obsidian vessels for 108 days. By invitation only."),
    ]
    c.executemany("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?)", products)

    conn.commit()
    conn.close()
    print(f"Database seeded — {len(orders)} orders, {len(products)} products.")
    print(f"Location: {os.path.abspath('ecombot.db')}")

if __name__ == "__main__":
    init()
