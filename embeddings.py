import os
import psycopg2
from psycopg2.extras import execute_values
import torch
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
                CREATE EXTENSION IF NOT EXISTS vector;
                
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    embedding vector(512)
                );
                
                CREATE TABLE IF NOT EXISTS user_favorites (
                    user_id INTEGER REFERENCES users(id),
                    image_id INTEGER REFERENCES images(id),
                    PRIMARY KEY (user_id, image_id)
                );
                
                CREATE TABLE IF NOT EXISTS user_favorite_embeddings (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id),
                    embedding vector(512)
                );
            """)

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

def update_user_favorite_embedding(user_id):
    """Update the embedding for a user's favorite images."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH user_fav_embeddings AS (
                    SELECT AVG(i.embedding) AS avg_embedding
                    FROM user_favorites uf
                    JOIN images i ON uf.image_id = i.id
                    WHERE uf.user_id = %s
                )
                INSERT INTO user_favorite_embeddings (user_id, embedding)
                SELECT %s, avg_embedding
                FROM user_fav_embeddings
                ON CONFLICT (user_id) DO UPDATE SET embedding = EXCLUDED.embedding
            """, (user_id, user_id))

def get_similar_users(target_user_id, limit=3):
    """Get the most similar users based on favorite embeddings using efficient nearest neighbor search."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.username, 1 - (uf1.embedding <=> uf2.embedding) AS similarity
                FROM user_favorite_embeddings uf1
                CROSS JOIN LATERAL (
                    SELECT uf2.user_id, uf2.embedding
                    FROM user_favorite_embeddings uf2
                    WHERE uf2.user_id != uf1.user_id
                    ORDER BY uf1.embedding <=> uf2.embedding
                    LIMIT %s
                ) uf2
                JOIN users u ON uf2.user_id = u.id
                WHERE uf1.user_id = %s
                ORDER BY similarity DESC
            """, (limit, target_user_id))
            return cur.fetchall()
        
def delete_user_favorite(user_id, image_id):
    """Delete a user's favorite image and recalculate embeddings."""
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            # Delete the favorite
            cur.execute("""
                DELETE FROM user_favorites
                WHERE user_id = %s AND image_id = %s
            """, (user_id, image_id))
            
            # Check if any rows were affected
            if cur.rowcount == 0:
                print(f"No favorite found for user {user_id} with image ID {image_id}")
                return
            
            print(f"Deleted favorite for user {user_id} with image ID {image_id}")
            
            
            
            if cur.rowcount == 0:
                print(f"No embedding updated for user {user_id}")
            else:
                print(f"Updated embedding for user {user_id}")
    update_user_favorite_embedding(user_id)
                
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
            # First, get the image_id for the given URL
            cur.execute("SELECT id FROM images WHERE url = %s", (url,))
            result = cur.fetchone()
            
            if result is None:
                print(f"Error: Image with URL {url} not found in the database.")
                return None
            
            image_id = result[0]
            
            # Now add the favorite
            cur.execute(
                "INSERT INTO user_favorites (user_id, image_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, image_id)
            )
            
            if cur.rowcount == 0:
                print(f"Favorite already exists for user {user_id} with image URL {url}")
            else:
                print(f"Added favorite for user {user_id} with image URL {url}")
            
    update_user_favorite_embedding(user_id)



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
    
    # Update user favorite embeddings
    for user_id in range(1, 5):
        update_user_favorite_embedding(user_id)
    
    # Get similar users
    target_user_id = 1
    similar_users = get_similar_users(target_user_id)
    print(f"Users most similar to user {target_user_id}:")
    for user_id, username, similarity in similar_users:
        print(f"User ID: {user_id}, Username: {username}, Similarity: {similarity:.4f}")


