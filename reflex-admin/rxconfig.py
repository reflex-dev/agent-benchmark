import reflex_enterprise as rxe
from reflex.plugins import SitemapPlugin

config = rxe.Config(
    app_name="reflex_admin",
    frontend_port=3001,
    backend_port=8001,
    tailwind=None,
    show_built_with_reflex=False,
    plugins=[
        SitemapPlugin(),
        rxe.EventHandlerAPIPlugin(),
    ],
)
