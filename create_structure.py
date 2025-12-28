import os

# Base directories
folders = {
    "templates": [
        "base.html",
        "components/navbar.html",
        "components/footer.html",
        "components/breadcrumbs.html",
        "components/alert.html",
        "core/home.html",
        "core/about.html",
        "core/contact.html",
        "core/instructors.html",
        "accounts/login.html",
        "accounts/signup.html",
        "accounts/dashboard.html",
        "accounts/profile.html",
        "accounts/email/email_confirmation_message.html",
        "classes/class_list.html",
        "classes/class_detail.html",
        "classes/schedule.html",
        "classes/booking_success.html",
        "store/product_list.html",
        "store/product_detail.html",
        "store/cart.html",
        "store/checkout.html",
        "store/order_confirmation.html",
        "blog/post_list.html",
        "blog/post_detail.html",
        "gallery/gallery.html"
    ],
    "static/css": ["custom.css"],
    "static/js": ["main.js", "cart.js", "booking.js"],
    "static/images": ["logo.png", "placeholder.jpg"],
    "media/products": [],
    "media/gallery": [],
    "media/instructors": [],
    "media/blog": []
}

def create_structure(base_path="."):
    for folder, files in folders.items():
        folder_path = os.path.join(base_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        for f in files:
            file_path = os.path.join(folder_path, f)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            if not os.path.exists(file_path):
                with open(file_path, "w") as fp:
                    fp.write("")  # create empty file
    print("Project structure created successfully!")

if __name__ == "__main__":
    create_structure()
