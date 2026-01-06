import flet as ft
from ui import MachineApp


def main(page: ft.Page):
    MachineApp(page)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
