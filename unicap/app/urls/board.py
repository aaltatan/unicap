from django.urls import path

from ..views import board, dashboard

app_name = "board"

urlpatterns = [
    path(route="", view=dashboard.dashboard, name="dashboard"),
    path(route="board/", view=board.index, name="index"),
    path(route="board/move/", view=board.move, name="move"),
    path(route="board/preview/", view=board.preview, name="preview"),
    path(route="board/toggle/", view=board.toggle, name="toggle"),
    path(route="board/reset/", view=board.reset, name="reset"),
    path(route="board/optimize/", view=board.optimize, name="optimize"),
    path(route="board/recommend/", view=board.recommend, name="recommend"),
]
