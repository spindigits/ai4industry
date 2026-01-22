import reflex as rx
from .state import State

def login_page() -> rx.Component:
    """The login page."""
    return rx.center(
        rx.vstack(
            rx.heading("⚡ GreenPower RAG", size="8"),
            rx.text("Please login to continue", color="gray"),
            rx.input(
                placeholder="Username",
                value=State.username_input,
                on_change=State.set_username_input,
            ),
            rx.input(
                placeholder="Password",
                type_="password",
                value=State.password_input,
                on_change=State.set_password_input,
            ),
            rx.cond(
                State.auth_error != "",
                rx.text(State.auth_error, color="red"),
            ),
            rx.button(
                "Login",
                on_click=State.login,
                width="100%",
            ),
            rx.text("Default: admin / admin123", font_size="0.8em", color="gray"),
            spacing="4",
            padding="2em",
            border_radius="10px",
            box_shadow="lg",
            bg="white",
            width="400px",
        ),
        height="100vh",
        bg="#f5f5f5",
    )

def chat_message(message: dict) -> rx.Component:
    """A single chat message."""
    return rx.box(
        rx.box(
            rx.text(message["content"]),
            bg=rx.cond(message["role"] == "user", "#E3F2FD", "#F5F5F5"),
            color="black",
            padding="1em",
            border_radius="8px",
            align_self=rx.cond(message["role"] == "user", "flex-end", "flex-start"),
        ),
        display="flex",
        justify_content=rx.cond(message["role"] == "user", "flex-end", "flex-start"),
        margin_bottom="1em",
        width="100%",
    )

def dashboard_page() -> rx.Component:
    """The main dashboard page."""
    return rx.flex(
        # --- Sidebar ---
        rx.vstack(
            rx.heading("GreenPower", size="6", color="white"),
            rx.text(f"Welcome, {State.user['display_name']}", color="lightgray", font_size="0.9em"),
            rx.divider(border_color="gray"),
            
            # Logout
            rx.button("Logout", on_click=State.logout, variant="outline", color_scheme="red", width="100%"),
            
            rx.divider(border_color="gray"),
            
            # Document Ingestion
            rx.heading("Ingestion", size="3", color="white"),
            rx.upload(
                rx.text("Drag & create files", color="white"),
                id="files",
                border="1px dotted white",
                padding="1em",
            ),
            rx.button(
                "Upload", 
                on_click=lambda: State.handle_upload(rx.upload_files(upload_id="files")),
                loading=State.is_uploading,
            ),
            rx.cond(
                State.upload_result,
                rx.text(State.upload_result.to_string(), color="lightgreen", font_size="0.8em"),
            ),
            
            rx.divider(border_color="gray"),
            
            # Web Scraping
            rx.heading("Web Scraping", size="3", color="white"),
            rx.text_area(
                placeholder="https://example.com...",
                value=State.scrape_urls,
                on_change=State.set_scrape_urls,
                height="100px",
                bg="white",
                color="black"
            ),
            rx.hstack(
                rx.checkbox("Follow Links", checked=State.scrape_follow_links, on_change=State.set_scrape_follow_links),
                rx.text("Max:", color="white"),
                rx.input(value=State.scrape_max_pages.to_string(), on_change=State.set_scrape_max_pages, width="50px", bg="white", color="black"),
                spacing="2",
            ),
            rx.button(
                "Scrape", 
                on_click=State.handle_scrape,
                loading=State.is_scraping
            ),
             rx.cond(
                State.scrape_result,
                rx.text(State.scrape_result.to_string(), color="lightgreen", font_size="0.8em"),
            ),
            
            bg="#2c3e50",
            width="300px",
            height="100vh",
            padding="2em",
            spacing="4",
        ),
        
        # --- Main Chat Area ---
        rx.vstack(
            rx.heading("Hybrid RAG Chat", size="7"),
            rx.divider(),
            
            # Chat History
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(State.chat_history, chat_message),
                    width="100%",
                ),
                height="70vh",
                width="100%",
                padding="2em",
                border="1px solid #e0e0e0",
                border_radius="10px",
            ),
            
            # Input Area
            rx.hstack(
                rx.input(
                    placeholder="Ask a question...",
                    value=State.question,
                    on_change=State.set_question,
                    width="100%",
                ),
                rx.button(
                    "Send", 
                    on_click=State.handle_submit,
                    loading=State.is_processing,
                ),
                width="100%",
                padding_top="1em",
            ),
            
            width="100%",
            height="100vh",
            padding="2em",
            spacing="4",
        ),
    )

def index() -> rx.Component:
    """The main entry point handles routing between login and dashboard."""
    return rx.cond(
        State.is_authenticated,
        dashboard_page(),
        login_page(),
    )

# Create the app
app = rx.App()
app.add_page(index)
