import os
import psycopg2
from psycopg2.extras import execute_values
import torch
import time
from PIL import Image
import clip

# Database connection parameters
DB_PARAMS = {
    "dbname": "postgres",
    "user": "danny",
    "password": "password", 
    "host": "localhost"
}

# Initialize CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

def create_tables():
    """Create necessary tables in the database."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
                
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    embedding VECTOR(512)
                );
                
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    embedding VECTOR(512)
                );
                
                CREATE TABLE IF NOT EXISTS user_favorites (
                    user_id INTEGER REFERENCES users(id),
                    image_id INTEGER REFERENCES images(id),
                    PRIMARY KEY (user_id, image_id)
                );
                
                CREATE INDEX IF NOT EXISTS users_embedding_idx ON users USING diskann (embedding);
            """)
            # Set query parameters for accuracy vs. speed trade-off
            cur.execute("SET diskann.query_search_list_size = 100;")
            cur.execute("SET diskann.query_rescore = 50;")

def initialize_users():
    """Initialize the database with 4 users."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            users = [("user1",), ("user2",), ("user3",), ("user4",)]
            execute_values(cur, "INSERT INTO users (username) VALUES %s ON CONFLICT DO NOTHING", users)

def get_image_embedding(image_path):
    """Create an embedding for an image using CLIP."""
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image)
    return image_features.cpu().numpy().flatten()

def add_image_to_database(url, embedding):
    """Add an image and its embedding to the database."""
    print(url, "url")
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO images (url, embedding) VALUES (%s, %s) ON CONFLICT (url) DO UPDATE SET embedding = EXCLUDED.embedding",
                (url, embedding.tolist())
            )

def process_images_folder(folder_path):
    """Process all images in a folder and its subfolders."""
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                image_path = os.path.join(root, file)
                embedding = get_image_embedding(image_path)
                add_image_to_database(image_path, embedding)

def add_user_favorite(user_id, image_id):
    """Add a favorite image for a user."""
    print(user_id, image_id)
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_favorites (user_id, image_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, image_id)
            )
        update_user_embedding(user_id)

def update_user_embedding(user_id):
    """Update the embedding for a user based on their favorite images."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET embedding = (
                    SELECT AVG(i.embedding)
                    FROM user_favorites uf
                    JOIN images i ON uf.image_id = i.id
                    WHERE uf.user_id = %s
                )
                WHERE id = %s
            """, (user_id, user_id))

def get_similar_users(target_user_id, limit=3):
    """Get the most similar users based on embedding similarity."""
    start_time = time.time()
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            
            cur.execute("""
                WITH target_user AS (
                    SELECT embedding
                    FROM users
                    WHERE id = %s
                )
                SELECT u.id, u.username, 1 - (u.embedding <=> tu.embedding) AS similarity
                FROM users u, target_user tu
                WHERE u.id != %s
                  AND u.embedding IS NOT NULL
                  AND tu.embedding IS NOT NULL
                ORDER BY u.embedding <=> tu.embedding
                LIMIT %s
            """, (target_user_id, target_user_id, limit))
            
            results = cur.fetchall()
            if not results:
                print(f"No similar users found. User {target_user_id} might not exist or have an embedding.")
            
    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    
    return {"elapsed_time": elapsed_time, "results": results}

def delete_user_favorite(user_id, image_id):
    """Delete a user's favorite image and recalculate embedding."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM user_favorites
                WHERE user_id = %s AND image_id = %s
            """, (user_id, image_id))
            
            if cur.rowcount == 0:
                print(f"No favorite found for user {user_id} with image ID {image_id}")
                return
            
            print(f"Deleted favorite for user {user_id} with image ID {image_id}")
    
    update_user_embedding(user_id)

def get_user_favorites(user_id):
    """Get the URLs of favorite images for a user."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT i.id, i.url
                FROM user_favorites uf
                JOIN images i ON uf.image_id = i.id
                WHERE uf.user_id = %s
                ORDER BY i.id
            """, (user_id,))
            return [{"id": row[0], "url": row[1]} for row in cur.fetchall()]

def add_user_favorite_by_url(user_id, url):
    """Add a favorite image for a user by URL, assuming the image already exists in the database."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM images WHERE url = %s", (url,))
            result = cur.fetchone()
            
            if result is None:
                print(f"Error: Image with URL {url} not found in the database.")
                return None
            
            image_id = result[0]
            
            cur.execute(
                "INSERT INTO user_favorites (user_id, image_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, image_id)
            )
            
            if cur.rowcount == 0:
                print(f"Favorite already exists for user {user_id} with image URL {url}")
            else:
                print(f"Added favorite for user {user_id} with image URL {url}")
    
    update_user_embedding(user_id)

if __name__ == "__main__":
    create_tables()
    initialize_users()
    
    # Process images
    image_folder = "./static/images"
    process_images_folder(image_folder)
    
    # Add some favorites for demonstration
    add_user_favorite(1, 1)
    add_user_favorite(1, 2)
    add_user_favorite(2, 2)
    add_user_favorite(2, 3)
    add_user_favorite(3, 1)
    add_user_favorite(3, 3)
    add_user_favorite(4, 2)
    add_user_favorite(4, 4)
    
    # Get similar users
    target_user_id = 1
    similar_users = get_similar_users(target_user_id)
    print(f"Users most similar to user {target_user_id}:")
    for user_id, username, similarity in similar_users:
        print(f"User ID: {user_id}, Username: {username}, Similarity: {similarity:.4f}")