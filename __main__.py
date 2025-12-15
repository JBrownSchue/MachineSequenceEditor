import flet as ft
from ui import getUploadView, getEditorView, getResultView


def main(
    pageContext: ft.Page
):
    pageContext.title = "Machine Sequence Editor"
    pageContext.window.icon= "icon.ico"
    pageContext.theme_mode = ft.ThemeMode.LIGHT

    def handleRouteChange(
        _routeEvent
    ):
        pageContext.views.clear()

        temp = {
            "/": getUploadView,
            "/editor": getEditorView,
            "/result": getResultView,
        }

        if pageContext.route in temp:
            temptmep = temp[pageContext.route](pageContext)
            pageContext.views.append(temptmep)
        
        pageContext.update()

    def handleViewPop(
        _viewEvent
    ):
        pageContext.views.pop()
        
        if len(pageContext.views):
            topView = pageContext.views[-1]
            targetRoute = topView.route
            pageContext.go(targetRoute)

    pageContext.on_route_change = handleRouteChange
    pageContext.on_view_pop = handleViewPop
    
    pageContext.go("/")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
