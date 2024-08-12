from fasthtml.common import *
from pathlib import Path
from embeddings import get_user_favorites, delete_user_favorite, add_user_favorite_by_url, get_similar_users
app, rt = fast_app()

# Database setup
db = database('data/images.db')
user_images = db.t.user_images
if user_images not in db.t:
    user_images.create(id=int, user=str, image_path=str, pk='id')
UserImage = user_images.dataclass()

# Image directory and categories
image_dir = Path('static/images')
categories = ['catsinsink', 'corgi', 'otters', 'waterporn', 'earthporn']
users = ['John Doe', 'Jane Doe', 'Bob Smith', 'Sarah Lee']
users_dict = {
    'John Doe': 1,
    'Jane Doe': 2,
    'Bob Smith': 3,
    'Sarah Lee': 4
}
reversed_users_dict = {
    1: 'John Doe',
    2: 'Jane Doe',
    3: 'Bob Smith',
    4: 'Sarah Lee'
}
def image_item(filename, category):
    return Div(
        Img(src=f"/static/images/{category.lower()}/{filename}", alt=filename, cls="category-image"),
        Button("...", cls="quick-add-btn", hx_post="/add_image", 
               hx_vals=f"{{user: '', image_path: '{category.lower()}/{filename}'}}"),
        cls="image-item",
        data_path=f"{category.lower()}/{filename}"
    )

def category_section(category):
    images = list((image_dir / category.lower()).glob('*.jpg'))[:10]
    return Div(
        H2(category),
        Div(*[image_item(img.name, category) for img in images], cls="category-images", id=f"{category.lower()}-images"),
        cls="category-section"
    )

def user_image(image, user):
    return Div(
        Img(src=f"{image['url']}", alt=f"{image['url']}", cls="user-image"),
        Button("Delete", cls="delete-btn", hx_delete=f"/delete_image/{user}/{image['id']}",
               hx_target=f"#{user.replace(' ', '_')}_images", hx_swap="outerHTML"),
        cls="user-image-container",
        data_path=f"{image['url']}",
    )

def user_similarity_section(name):
    user_id = users_dict[name]
    similar_users = get_similar_users(user_id)
    similar_users_html = [
        P(f"{reversed_users_dict[user_id]}: {similarity:.3f}") 
        for user_id, user_name, similarity in similar_users 
        if similarity is not None
    ]
    return Div(
        H4("Similar Users:"),
        *similar_users_html,
        cls="user-similarity",
        id=f"{name.replace(' ', '_')}_similarity"
    )

def user_images_container(name):
    user_id = users_dict[name]
    favorites = get_user_favorites(user_id)
    return Div(*[user_image(img, name) for img in favorites],
               id=f"{name.replace(' ', '_')}_images", cls="user-images sortable-list")

def user_card(name):
    username = f"@{name.lower().replace(' ', '')}"
    return Div(
        H3(name),
        P(username),
        user_images_container(name),
        user_similarity_section(name),
        cls="user-card"
    )

@rt("/")
def get():
    return Titled(
        "Image Drag and Drop App",
        Script(src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"),
        Div(*[category_section(cat) for cat in categories], cls="categories-container"),
        Div(*[user_card(name) for name in users], cls="users-container"),
        Style("""
            body { background-color: #1a1a1a; color: #ffffff; }
            .categories-container { display: flex; flex-wrap: wrap; gap: 20px; }
            .category-section { flex: 1; min-width: 200px; }
            .category-images { display: flex; flex-wrap: wrap; gap: 10px; }
            .image-item { width: 100px; height: 100px; cursor: pointer; position: relative; }
            .category-image { width: 100%; height: 100%; object-fit: cover; }
            .users-container { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 40px; }
            .user-card { flex: 1; min-width: 200px; border: 1px solid #333; padding: 20px; background-color: #2a2a2a; }
            .user-images { min-height: 100px; border: 1px dashed #444; margin-top: 20px; padding: 10px; display: flex; flex-wrap: wrap; gap: 10px; }
            .user-image-container { position: relative; cursor: pointer; }
            .user-image { width: 80px; height: 80px; object-fit: cover; }
            .delete-btn { position: absolute; top: 0; right: 0; background-color: #ff4d4d; color: white; border: none; padding: 2px 5px; cursor: pointer; font-size: 0.8em; }
            .quick-add-btn { position: absolute; bottom: 0; right: 0; background-color: #4CAF50; color: white; border: none; padding: 2px 5px; cursor: pointer; font-size: 0.8em; }
            .sortable-drag { opacity: 0.5; }
            .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000; }
            .modal-content { background: #2a2a2a; padding: 20px; border-radius: 5px; max-width: 90%; max-height: 90%; overflow: auto; }
            .modal-image { max-width: 100%; max-height: 80vh; object-fit: contain; }
            .user-select-btn { margin: 5px; padding: 5px 10px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        """),
        Script("""
            document.addEventListener('DOMContentLoaded', function() {
                const categoryLists = document.querySelectorAll('.category-images');
                const userLists = document.querySelectorAll('.sortable-list');

                categoryLists.forEach(list => {
                    new Sortable(list, {
                        group: {
                            name: 'shared',
                            pull: 'clone',
                            put: false
                        },
                        sort: false,
                        animation: 150
                    });
                });

                userLists.forEach(list => {
                    new Sortable(list, {
                        group: {
                            name: 'shared',
                            pull: false
                        },
                        animation: 150,
                        onAdd: function(evt) {
                            const imagePath = evt.item.dataset.path;
                            const userName = evt.to.id.replace('_images', '').replace('_', ' ');
                            htmx.ajax('POST', '/add_image', {
                                target: evt.to,
                                swap: 'outerHTML',
                                values: { user: userName, image_path: imagePath }
                            });
                            evt.item.remove();  // Remove the cloned item
                        }
                    });
                });

                // Image view functionality
                function showImageModal(src, alt) {
                    const modal = document.createElement('div');
                    modal.className = 'modal';
                    modal.innerHTML = `
                        <div class="modal-content">
                            <img src="${src}" alt="${alt}" class="modal-image">
                        </div>
                    `;
                    
                    document.body.appendChild(modal);

                    // Close modal when clicking outside the image
                    modal.addEventListener('click', function(event) {
                        if (event.target === modal) {
                            modal.remove();
                        }
                    });
                }

                document.body.addEventListener('click', function(e) {
                    const img = e.target.closest('img');
                    if (img && (img.classList.contains('category-image') || img.classList.contains('user-image'))) {
                        showImageModal(img.src, img.alt);
                    }

                    if (e.target.classList.contains('quick-add-btn')) {
                        const imageItem = e.target.closest('.image-item');
                        const imagePath = imageItem.dataset.path;
                        const userCards = document.querySelectorAll('.user-card');
                        
                        // Create a modal for user selection
                        const modal = document.createElement('div');
                        modal.className = 'modal';
                        modal.innerHTML = `
                            <div class="modal-content">
                                <h3>Select a user to add the image to:</h3>
                                ${Array.from(userCards).map(card => `
                                    <button class="user-select-btn" data-user="${card.querySelector('h3').textContent}">${card.querySelector('h3').textContent}</button>
                                `).join('')}
                            </div>
                        `;
                        
                        document.body.appendChild(modal);

                        // Close modal when clicking outside
                        modal.addEventListener('click', function(event) {
                            if (event.target === modal) {
                                modal.remove();
                            }
                        });
                        // Add event listeners to user selection buttons
                        modal.querySelectorAll('.user-select-btn').forEach(btn => {
                            btn.addEventListener('click', function() {
                                const userName = this.dataset.user;
                                const userImagesContainer = document.getElementById(`${userName.replace(' ', '_')}_images`);
                                
                                htmx.ajax('POST', '/add_image', {
                                    target: userImagesContainer,
                                    swap: 'outerHTML',
                                    values: { user: userName, image_path: imagePath }
                                });

                                modal.remove();
                            });
                        });
                    }
                });
            });
        """)
    )

@rt('/add_image')
def post(user: str, image_path: str):
    user_id = users_dict[user]
    favorites = get_user_favorites(user_id)
    if len(favorites) >= 4:
        return user_images_container(user), user_similarity_section(user)
    if not any(img['url'] == image_path for img in favorites):
        add_user_favorite_by_url(user_id=user_id, url=f"./static/images/{image_path}")
    return user_images_container(user)

@rt('/update_similarity/{user}')
def update_similarity(user: str):
    return user_similarity_section(user)

@rt('/delete_image/{user}/{image_id}')
def delete(user: str, image_id: int):
    user_id = users_dict[user]
    delete_user_favorite(user_id=user_id, image_id=image_id)
    return user_images_container(user)


@rt('/static/images/{category}/{filename}')
def serve_image(category: str, filename: str):
    return FileResponse(image_dir / category / filename)

if __name__ == '__main__':
    serve()