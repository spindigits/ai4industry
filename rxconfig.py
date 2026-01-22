import reflex as rx

config = rx.Config(
    app_name="greenpower_rag",
    db_url="sqlite:///reflex.db",
    env=rx.Env.DEV,
)
