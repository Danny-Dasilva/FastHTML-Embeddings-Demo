from fasthtml.common import *
from pathlib import Path

app, rt = fast_app()

# Assume we have image files in the 'static/images' directory
image_dir = Path('static/images')
categories = ['Nature', 'Cities', 'Animals', 'Food', 'Technology']
users = ['John Doe', 'Jane Doe', 'Bob Smith', 'Sarah Lee']

def image_item(filename, category):
    print(f"/static/images/{category.lower()}/{filename}", "aaa")
    return Div(
        Img(src=f"/static/images/{category.lower()}/{filename}", alt=filename, cls="category-image"),
        cls="image-item",
        draggable="true",
        **{'@dragstart': f"drag(event, '{category.lower()}/{filename}')"}
    )

def category_section(category):
    print(image_dir/category.lower())
    images = list((image_dir / category.lower()).glob('*.webp'))[:10]
    print([img.name for img in images], )
    return Div(
        H2(category),
        Div(*[image_item(img.name, category) for img in images], cls="category-images"),
        cls="category-section"
    )

def user_card(name, username):
    return Div(
        Div(cls="user-avatar"),
        H3(name),
        P(username),
        P("Lorem ipsum dolor sit amet, consectetur adipiscing elit."),
        Div(cls="user-images", **{'@dragover': "allowDrop(event)", '@drop': "drop(event)"}),
        cls="user-card"
    )

@rt("/")
def get():
    return Titled(
        "Image Drag and Drop App",
        Div(*[category_section(cat) for cat in categories], cls="categories-container"),
        Div(*[user_card(name, f"@{name.lower().replace(' ', '')}") for name in users], cls="users-container"),
        Style("""
            .categories-container { display: flex; flex-wrap: wrap; gap: 20px; }
            .category-section { flex: 1; min-width: 200px; }
            .category-images { display: flex; flex-wrap: wrap; gap: 10px; }
            .image-item { width: 100px; height: 100px; cursor: move; }
            .category-image { width: 100%; height: 100%; object-fit: cover; }
            .users-container { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 40px; }
            .user-card { flex: 1; min-width: 200px; border: 1px solid #ccc; padding: 20px; }
            .user-avatar { width: 50px; height: 50px; background-color: #ccc; border-radius: 50%; }
            .user-images { min-height: 100px; border: 1px dashed #ccc; margin-top: 20px; padding: 10px; }
            .user-images img { width: 80px; height: 80px; object-fit: cover; margin: 5px; }
            .delete-btn { background-color: #ff4d4d; color: white; border: none; padding: 5px 10px; cursor: pointer; }
        """),
        Script("""
            function drag(ev, data) {
                ev.dataTransfer.setData("text", data);
            }

            function allowDrop(ev) {
                ev.preventDefault();
            }

            function drop(ev) {
                ev.preventDefault();
                var data = ev.dataTransfer.getData("text");
                var img = document.createElement("img");
                img.src = "/static/images/" + data;
                img.style.width = "80px";
                img.style.height = "80px";
                img.style.objectFit = "cover";
                img.style.margin = "5px";
                
                var deleteBtn = document.createElement("button");
                deleteBtn.innerText = "Delete";
                deleteBtn.className = "delete-btn";
                deleteBtn.onclick = function() {
                    img.remove();
                    deleteBtn.remove();
                };
                
                ev.target.appendChild(img);
                ev.target.appendChild(deleteBtn);
            }
        """)
    )

@rt('/static/images/{category}/{filename}')
def serve_image(category: str, filename: str):
    return FileResponse(image_dir / category / filename)

if __name__ == '__main__':
    serve()