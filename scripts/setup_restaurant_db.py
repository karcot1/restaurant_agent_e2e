import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import pg8000
import time

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
EMBEDDING_MODEL='gemini-embedding-001'

# Verify required environment variables
required_vars = ['GOOGLE_CLOUD_PROJECT', 'REGION', 'DB_PASSWORD']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"Expected .env file location: {env_path}", file=sys.stderr)
    if not env_path.exists():
        print(f"✗ File not found at that location", file=sys.stderr)
    else:
        print(f"✓ File exists but is missing the variables above", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"Make sure your .env file contains:", file=sys.stderr)
    for var in missing_vars:
        print(f"  {var}=<value>", file=sys.stderr)
    sys.exit(1)

# Menu items data
MENU_ITEMS = [
    ("Truffle Mushroom Risotto", "Italian", "Main Course",
     "Arborio rice, truffle oil, porcini mushrooms, parmesan, white wine",
     "$28", "Vegetarian, Gluten-Free", True,
     "A creamy, luxurious risotto made with arborio rice slow-cooked in white wine and mushroom broth, finished with shaved black truffle and aged parmesan. The porcini mushrooms add a deep, earthy flavor that pairs beautifully with the delicate truffle oil drizzled on top."),
    ("Spicy Tuna Tartare", "Japanese", "Appetizer",
     "Ahi tuna, sriracha, sesame oil, avocado, crispy wonton",
     "$22", "Gluten-Free, Dairy-Free", True,
     "Fresh ahi tuna diced and tossed with sriracha aioli, toasted sesame oil, and lime juice, served atop creamy avocado slices with crispy wonton chips. A perfect balance of heat, richness, and crunch inspired by modern Japanese fusion cuisine."),
    ("Lamb Kofta Kebab", "Middle Eastern", "Main Course",
     "Ground lamb, cumin, coriander, yogurt sauce, flatbread",
     "$24", "Halal", True,
     "Hand-formed spiced lamb kebabs grilled over charcoal, seasoned with cumin, coriander, and sumac. Served with warm flatbread, tangy yogurt-cucumber sauce, and a fresh herb salad. A classic Middle Eastern street food elevated with premium ingredients."),
    ("Pad Thai", "Thai", "Main Course",
     "Rice noodles, shrimp, tamarind, peanuts, bean sprouts, lime",
     "$19", "Gluten-Free, Dairy-Free", True,
     "Stir-fried rice noodles with tiger shrimp, scrambled egg, and a sweet-sour tamarind sauce, topped with crushed peanuts, fresh bean sprouts, and a squeeze of lime. This classic Thai street food dish balances sweet, sour, salty, and umami in every bite."),
    ("Margherita Pizza", "Italian", "Main Course",
     "San Marzano tomatoes, fresh mozzarella, basil, olive oil",
     "$18", "Vegetarian", True,
     "A Neapolitan-style pizza with a thin, charred crust topped with crushed San Marzano tomatoes, creamy buffalo mozzarella, fresh basil leaves, and a drizzle of extra virgin olive oil. Simple, classic, and made with imported Italian ingredients."),
    ("Miso Glazed Black Cod", "Japanese", "Main Course",
     "Black cod, white miso, mirin, sake, pickled ginger",
     "$36", "Gluten-Free, Dairy-Free", True,
     "Buttery black cod marinated for 72 hours in a sweet white miso glaze with mirin and sake, then broiled until caramelized. Served with pickled ginger and steamed bok choy. A signature dish inspired by Nobu's iconic preparation."),
    ("Caesar Salad", "American", "Appetizer",
     "Romaine lettuce, parmesan, croutons, anchovy dressing",
     "$14", "Contains Gluten", True,
     "Crisp romaine hearts tossed with a house-made anchovy-garlic dressing, shaved parmesan, and golden sourdough croutons. A timeless salad that serves as the perfect light starter or side dish with grilled proteins."),
    ("Chicken Tikka Masala", "Indian", "Main Course",
     "Chicken thigh, tomato cream sauce, garam masala, basmati rice",
     "$21", "Gluten-Free", True,
     "Tender chunks of tandoori-marinated chicken simmered in a rich, creamy tomato sauce spiced with garam masala, cumin, and fenugreek. Served over fragrant basmati rice with warm garlic naan on the side."),
    ("Chocolate Lava Cake", "French", "Dessert",
     "Dark chocolate, butter, eggs, vanilla, powdered sugar",
     "$15", "Vegetarian", True,
     "A warm, individual-sized chocolate cake with a molten dark chocolate center that flows when you break through the delicate outer shell. Made with 70% Belgian dark chocolate and served with a scoop of vanilla bean ice cream."),
    ("Pho Bo", "Vietnamese", "Main Course",
     "Rice noodles, beef brisket, star anise, cinnamon, bean sprouts, Thai basil",
     "$17", "Gluten-Free, Dairy-Free", True,
     "A deeply aromatic beef broth simmered for 12 hours with star anise, cinnamon, and charred ginger, ladled over rice noodles and thinly sliced beef brisket. Served with fresh Thai basil, bean sprouts, jalapeño, and lime for the table to customize."),
    ("Lobster Bisque", "French", "Appetizer",
     "Lobster, heavy cream, cognac, tarragon, cayenne",
     "$19", "Gluten-Free", True,
     "A velvety smooth soup made from roasted lobster shells, finished with heavy cream, a splash of cognac, and fresh tarragon. Each bowl is garnished with tender lobster meat and a pinch of cayenne for subtle warmth."),
    ("Falafel Plate", "Middle Eastern", "Main Course",
     "Chickpeas, herbs, tahini, pickled vegetables, hummus",
     "$16", "Vegan, Gluten-Free", True,
     "Crispy-on-the-outside, fluffy-on-the-inside chickpea fritters seasoned with fresh parsley, cilantro, and cumin. Served with creamy tahini sauce, house-made hummus, pickled turnips, and warm pita bread."),
    ("Crème Brûlée", "French", "Dessert",
     "Heavy cream, vanilla bean, egg yolks, caramelized sugar",
     "$13", "Vegetarian, Gluten-Free", True,
     "A classic French custard made with Madagascar vanilla bean and farm-fresh egg yolks, topped with a perfectly torched layer of caramelized sugar that cracks with a satisfying snap. Rich, creamy, and elegantly simple."),
    ("Korean BBQ Short Ribs", "Korean", "Main Course",
     "Beef short ribs, soy sauce, sesame, garlic, pear marinade",
     "$32", "Dairy-Free", False,
     "Premium beef short ribs marinated overnight in a sweet and savory blend of soy sauce, Asian pear, garlic, and toasted sesame. Grilled tableside over charcoal and served with lettuce wraps, pickled daikon, and gochujang dipping sauce."),
    ("Tiramisu", "Italian", "Dessert",
     "Mascarpone, espresso, ladyfingers, cocoa, Marsala wine",
     "$14", "Vegetarian, Contains Gluten", True,
     "Layers of espresso-soaked ladyfingers and whipped mascarpone cream flavored with Marsala wine, dusted with premium Dutch cocoa powder. Made fresh daily and chilled for 24 hours to develop rich, complex flavors."),
]


def get_connection():
    """Create a connection to Cloud SQL using the connector."""
    project = os.environ['GOOGLE_CLOUD_PROJECT']
    region = os.environ['REGION']
    password = os.environ['DB_PASSWORD']
    instance = os.environ['DB_INSTANCE']
    database = os.environ['DB_NAME']

    connector = Connector()
    conn = connector.connect(
        f"{project}:{region}:{instance}",
        "pg8000",
        user="postgres",
        password=password,
        db=database
    )
    return conn, connector


def create_schema(cursor):
    """Create extensions and menu_items table."""
    cursor.execute("CREATE EXTENSION IF NOT EXISTS google_ml_integration")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            cuisine_type VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            ingredients VARCHAR NOT NULL,
            price VARCHAR NOT NULL,
            dietary_tags VARCHAR NOT NULL,
            available BOOLEAN NOT NULL DEFAULT TRUE,
            description TEXT NOT NULL,
            description_embedding vector(3072)
        )
    """)


def seed_menu_items(cursor, conn):
    """Insert menu items."""
    cursor.execute("SELECT COUNT(*) FROM menu_items")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        print(f"      {existing_count} menu items already exist, skipping seed")
        return 0

    cursor.executemany("""
        INSERT INTO menu_items (name, cuisine_type, category, ingredients, price, dietary_tags, available, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, MENU_ITEMS)
    conn.commit()
    return len(MENU_ITEMS)


def generate_embeddings(cursor, conn):
    """Generate embeddings using Cloud SQL's embedding() function."""
    cursor.execute("SELECT COUNT(*) FROM menu_items WHERE description_embedding IS NULL")
    null_count = cursor.fetchone()[0]

    if null_count == 0:
        print("      All menu items already have embeddings")
        return 0

    cursor.execute(f"""
        UPDATE menu_items
        SET description_embedding = embedding('{EMBEDDING_MODEL}', description)::vector
        WHERE description_embedding IS NULL
    """)
    rows_updated = cursor.rowcount
    conn.commit()
    return rows_updated


def main():
    conn, connector = get_connection()
    cursor = conn.cursor()

    try:
        create_schema(cursor)
        conn.commit()

        seeded = seed_menu_items(cursor, conn)
        if seeded > 0:
            print(f"      ✓ Inserted {seeded} menu items")

        # Waiting for vertex role propagation
        time.sleep(60)
        embedded = generate_embeddings(cursor, conn)
        if embedded > 0:
            print(f"      ✓ Generated {embedded} embeddings")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        connector.close()


if __name__ == "__main__":
    main()