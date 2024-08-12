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
        Div(cls="user-avatar"),
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
            .image-item { width: 100px; height: 100px; cursor: move; }
            .category-image { width: 100%; height: 100%; object-fit: cover; }
            .users-container { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 40px; }
            .user-card { flex: 1; min-width: 200px; border: 1px solid #333; padding: 20px; background-color: #2a2a2a; }
            .user-avatar { width: 50px; height: 50px; background-color: #444; border-radius: 50%; }
            .user-images { min-height: 100px; border: 1px dashed #444; margin-top: 20px; padding: 10px; display: flex; flex-wrap: wrap; gap: 10px; }
            .user-image-container { position: relative; }
            .user-image { width: 80px; height: 80px; object-fit: cover; }
            .delete-btn { position: absolute; top: 0; right: 0; background-color: #ff4d4d; color: white; border: none; padding: 2px 5px; cursor: pointer; font-size: 0.8em; }
            .sortable-drag { opacity: 0.5; }
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