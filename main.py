from fasthtml.common import *
from pathlib import Path

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

def user_image(image):
    return Div(
        Img(src=f"/static/images/{image.image_path}", alt=image.image_path, cls="user-image"),
        Button("Delete", cls="delete-btn", hx_delete=f"/delete_image/{image.id}",
               hx_target=f"#{image.user.replace(' ', '_')}_images", hx_swap="outerHTML"),
        cls="user-image-container",
        data_path=image.image_path
    )

def user_images_container(name):
    user_images_list = user_images(where=f"user == '{name}'")
    return Div(*[user_image(img) for img in user_images_list],
               id=f"{name.replace(' ', '_')}_images", cls="user-images sortable-list")

def user_card(name):
    username = f"@{name.lower().replace(' ', '')}"
    return Div(
        H3(name),
        P(username),
        user_images_container(name),
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
    user_images_list = user_images(where=f"user == '{user}'")
    if len(user_images_list) >= 4:
        return user_images_container(user)
    if not any(img.image_path == image_path for img in user_images_list):
        new_image = UserImage(user=user, image_path=image_path)
        user_images.insert(new_image)
    return user_images_container(user)

@rt('/delete_image/{id}')
def delete(id: int):
    image = user_images.get(id)
    if image:
        user = image.user
        user_images.delete(id)
        return user_images_container(user)
    return ""

@rt('/static/images/{category}/{filename}')
def serve_image(category: str, filename: str):
    return FileResponse(image_dir / category / filename)

if __name__ == '__main__':
    serve()