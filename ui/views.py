import flet as ft
import os
from helper import IMachineService, MachineBusinessLogic
from helper.logic import XML_TAG_IST, XML_TAG_SOLL

# Layout Constants
DEFAULT_PADDING = 20
LARGE_PADDING = 50
HEADER_TEXT_SIZE = 24
INSTRUCTION_TEXT_SIZE = 20
ICON_SIZE_LARGE = 50
ICON_SIZE_MEDIUM = 20
EXPORT_FILE_SUFFIX = "_konfiguriert"

class UploadView(ft.View):
    """
    View for the first step: Uploading the ZIP file.
    Handles UI layout and user interaction for file selection.
    """

    def __init__(self, service: IMachineService, navigation_callback):
        super().__init__(route="/", padding=LARGE_PADDING)
        self.service = service
        self.nav = navigation_callback
        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self.on_file_result

        self.status_label = ft.Text()
        self.proceed_button = ft.ElevatedButton(
            text="Nächster Schritt: Sequenz-Editor",
            icon=ft.Icons.ARROW_FORWARD,
            disabled=True,
            on_click=lambda _: self.nav("/editor")
        )

        self.file_picker = ft.FilePicker(on_result=self.on_file_result)

        self.controls = [
            ft.AppBar(
                title=ft.Text("Schritt 1: ZIP hochladen"), 
                bgcolor=ft.Colors.BLUE_GREY_100
            ),
            ft.Container(
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=DEFAULT_PADDING,
                    controls=[
                        ft.Icon(name=ft.Icons.UPLOAD_FILE, size=ICON_SIZE_LARGE),
                        ft.Text("Bitte lade deine ZIP-Datei hoch.", size=INSTRUCTION_TEXT_SIZE),
                        ft.ElevatedButton(
                            text="ZIP-Datei auswählen",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda _: self.file_picker.pick_files(
                                allow_multiple=False, 
                                allowed_extensions=["zip"]
                            )
                        ),
                        self.status_label,
                        ft.Divider(),
                        self.proceed_button
                    ]
                ),
                alignment=ft.alignment.center
            )
        ]


    def on_file_result(self, event: ft.ControlEvent):
        """Processes the file selection event and updates UI status."""
        if event.files:
            selected_file = event.files[0]
            uploaded_file_name = self.service.logic_handle_upload(selected_file)

            self.status_label.value = f"Ausgewählte Datei: {uploaded_file_name}"
            self.proceed_button.disabled = False
            self.update()


class EditorView(ft.View):
    """
    View for the second step: Configuring machine features and file sequence.
    Drives UI updates based on the shared business logic service.
    """
    def __init__(self, service: IMachineService, navigation_callback):
        super().__init__(route="/editor", scroll=ft.ScrollMode.AUTO)
        self.service = service
        self.nav = navigation_callback

        # Display Elements
        self.machine_name_label = ft.Text(
            size=HEADER_TEXT_SIZE, 
            weight=ft.FontWeight.BOLD, 
            color=ft.Colors.BLUE_GREY_900
        )

        # Configuration Elements
        self.mount_count_hint = ft.Text(size=12, color=ft.Colors.GREY)
        self.mount_count_field = ft.TextField(
            label="MountCount",
            width=250, 
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]"),
            border_color=ft.Colors.TEAL_600,
            on_change=self.on_mount_count_change
        )

        self.features_list = ft.Column(spacing=5)
        self.files_list = ft.Column(spacing=8)

        # Selection Mode
        self.mode_switch = ft.Switch(
            active_color=ft.Colors.BLUE_600, 
            on_change=self.on_mode_toggle
        )
        self.mode_description = ft.Text(weight=ft.FontWeight.BOLD, size=16)

        self.controls = [
            ft.AppBar(title=ft.Text("Sequenz-Editor"), bgcolor=ft.Colors.BLUE_GREY_100),
            ft.Container(
                padding=DEFAULT_PADDING,
                content=ft.Column([
                    ft.Text("Erkannte Maschinen-Konfiguration:", color=ft.Colors.GREY),
                    self.machine_name_label,
                    ft.Divider(),
                    ft.Container(
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        padding=10,
                        border_radius=8,
                        content=ft.Row([
                            ft.Row([self.mode_switch, self.mode_description]),
                            ft.Row([
                                ft.Icon(ft.Icons.NUMBERS, size=ICON_SIZE_MEDIUM),
                                ft.Column([self.mount_count_field, self.mount_count_hint], spacing=0)
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ),
                    ft.Text("Features konfigurieren:", weight=ft.FontWeight.BOLD),
                    self.features_list,
                    ft.Divider(),
                    ft.Text("Dateireihenfolge (Drag & Drop):", weight=ft.FontWeight.BOLD),
                    self.files_list,
                    ft.Container(height=30),
                    ft.ElevatedButton(
                        text="Sequenz bestätigen & Beenden",
                        icon=ft.Icons.CHECK_CIRCLE,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE),
                        on_click=lambda _: self.nav("/result")
                    )
                ])
            )
        ]


    def on_attach(self):
        """Initializes configuration data and refreshes view components."""
        if self.service.machine_model_name == "UNKNOWN":
            self.service.logic_parse_config()
            self.service.logic_load_files_for_mode()
            self.service.logic_load_xml_data_for_files()
        self.refresh_ui()


    def refresh_ui(self):
        """Synchronizes all UI components with the current service state."""
        self.machine_name_label.value = self.service.machine_display_string
        self.mount_count_field.value = str(self.service.mount_count)
        self.mode_switch.value = self.service.is_bars_mode
        self.mode_description.value = "Test Bars" if self.service.is_bars_mode else "Test Profiles"

        _, has_error, message = self.service.logic_validate_mount_count(self.mount_count_field.value)
        self.mount_count_hint.value = message
        self.mount_count_hint.color = ft.Colors.RED if has_error else ft.Colors.GREY

        can_switch_mode = self.service.logic_is_mode_switch_allowed()
        self.mode_switch.disabled = not can_switch_mode

        if not can_switch_mode:
            self.mode_description.value = "Test Bars (Erzwungen durch SiftCutDevice)"
            self.mode_description.color = ft.Colors.ORANGE_700
        else:
            self.mode_description.value = "Test Bars" if self.service.is_bars_mode else "Test Profiles"
            self.mode_description.color = ft.Colors.BLACK
        
        self.rebuild_features_ui()
        self.rebuild_files_ui()
        self.update()


    def rebuild_features_ui(self):
        """Reconstructs the feature toggle list based on logic state."""
        self.features_list.controls.clear()
        feature_order = ["createShelf", "createBigShelf", "RobotMode", "ShiftCutDevice"]
        
        labels = {
            "createShelf": "createShelf",
            "createBigShelf": "createBigShelf",
            "RobotMode": "RobotMode",
            "ShiftCutDevice": "ShiftCutDevice"
        }

        for key in feature_order:
            is_active = self.service.feature_state.get(key, False)
            
            any_shelf_active = (self.service.feature_state.get("createShelf") or 
                               self.service.feature_state.get("createBigShelf"))
            
            is_blocked = False
            block_reason = ""

            if key == "RobotMode" and not any_shelf_active:
                is_blocked = True
                block_reason = " (Erfordert ein Regal)"
            elif key == "ShiftCutDevice" and any_shelf_active:
                is_blocked = True
                block_reason = " (Nicht mit Regal möglich)"

            display_text = labels.get(key, key) + block_reason

            self.features_list.controls.append(
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE if is_active else ft.Icons.CANCEL,
                        icon_color=ft.Colors.GREEN if is_active else ft.Colors.RED_400,
                        disabled=is_blocked,
                        on_click=lambda _, feat=key: self.on_feature_click(feat)
                    ),
                    ft.Text(display_text, weight=ft.FontWeight.BOLD)
                ])
            )


    def rebuild_files_ui(self):
        """Reconstructs the draggable file list from current sequence."""
        self.files_list.controls.clear()

        for index, name in enumerate(self.service.current_file_order):
            display_name = os.path.splitext(name)[0]

            full_path = f"{self.service.active_folder}{name}"
            xml_info = self.service.extracted_xml_data.get(full_path, {})
            ist_val = xml_info.get(XML_TAG_IST, "-")
            soll_val = xml_info.get(XML_TAG_SOLL, "-")

            self.files_list.controls.append(
                ft.Draggable(
                    group="files",
                    data=str(index),
                    content_feedback=ft.Container(
                        content=ft.Text(
                            f"{display_name}",
                            size=14
                            ),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=5,
                        border=ft.border.all(1, ft.Colors.BLUE),
                        opacity=0.8,
                    ),
                    content=ft.DragTarget(
                        group="files",
                        data=str(index),
                        on_accept=self.on_file_dropped,
                        content=ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DRAG_HANDLE, color=ft.Colors.GREY_400),
                                ft.Text(f"{index + 1}. {display_name}", expand=True),
                                ft.Text(f"IST: {ist_val}", size=12, color=ft.Colors.GREY_400),
                                ft.Text(f"SOLL: {soll_val}", size=12, color=ft.Colors.BLACK),
                            ]),
                            padding=10, 
                            border=ft.border.all(1, ft.Colors.GREY_300), 
                            border_radius=5,
                            bgcolor=ft.Colors.WHITE
                        )
                    )
                )
            )


    def on_mount_count_change(self, event: ft.ControlEvent):
        """Validates input and updates range hint via business logic."""
        _, has_error, message = self.service.logic_validate_mount_count(event.control.value)
        self.mount_count_hint.value = message
        self.mount_count_hint.color = ft.Colors.RED if has_error else ft.Colors.GREY
        self.update()


    def on_feature_click(self, feature_name: str):
        """Toggles a machine feature and refreshes dependencies."""
        self.service.logic_toggle_feature(feature_name)
        self.refresh_ui()


    def on_mode_toggle(self, event: ft.ControlEvent):
        """Switches between Bar and Profile modes and reloads file lists."""
        self.service.is_bars_mode = event.control.value
        self.service.logic_load_files_for_mode()
        self.service.logic_load_xml_data_for_files()
        self.refresh_ui()


    def on_file_dropped(self, event: ft.DragTargetEvent):
        """Updates the internal file sequence based on drag-and-drop result."""
        source_control = self.page.get_control(event.src_id)
        source_index = int(source_control.data)
        target_index = int(event.control.data)
        
        self.service.logic_reorder_drag_drop(source_index, target_index)
        self.refresh_ui()


class ResultView(ft.View):
    """
    Final view for summary and Export.
    """

    def __init__(self, service: IMachineService, navigation_callback):
        super().__init__(route="/result", scroll=ft.ScrollMode.AUTO)
        self.service = service
        self.nav = navigation_callback

        self.features_summary = ft.Column(spacing=2)
        self.files_summary = ft.Column(spacing=2)

        self.export_progress = ft.ProgressBar(width=400, visible=False)
        self.save_button = ft.ElevatedButton(
            text="Konfigurierte ZIP-Datei speichern", 
            icon=ft.Icons.DOWNLOAD,
            on_click=self.on_save_click
        )
        self.save_dialog = ft.FilePicker()
        self.save_dialog.on_result = self.on_export_finished

        self.controls = [
            ft.AppBar(title=ft.Text("Vorgang abgeschlossen"), bgcolor=ft.Colors.GREEN_100),
            ft.Container(
                padding=DEFAULT_PADDING,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.TASK_ALT, color=ft.Colors.GREEN, size=ICON_SIZE_LARGE),
                        ft.Text("Sequenz erfolgreich definiert", weight="bold", size=INSTRUCTION_TEXT_SIZE),
                        ft.Divider(),

                        ft.Text("Konfigurierte Features:", weight="bold"),
                        ft.Container(content=self.features_summary, padding=10, bgcolor=ft.Colors.BLUE_50, border_radius=5),
                        
                        ft.Text("Finale Dateireihenfolge:", weight="bold"),
                        ft.Container(content=self.files_summary, padding=10, bgcolor=ft.Colors.GREY_100, border_radius=5),

                        ft.Divider(),
                        ft.Text("Du kannst die fertige Datei nun herunterladen."),
                        self.export_progress,
                        self.save_button,
                        ft.OutlinedButton("Neu starten", on_click=lambda _: self.nav("/"))
                    ]
                )
            )
        ]


    def refresh_summary(self):
        """Populates the summary previews with the actual data from the service."""
        self.features_summary.controls.clear()
        self.files_summary.controls.clear()

        final_data = self.service.logic_prepare_final_data()
        self.features_summary.controls.append(ft.Text(f"Maschine: {self.service.machine_model_name}"))
        self.features_summary.controls.append(ft.Text(f"MountCount: {self.service.mount_count}"))
        
        for feature in final_data["Features"]:
            for key, val in feature.items():
                self.features_summary.controls.append(ft.Text(f"- {key}: {val}", size=12))

        for index, name in enumerate(self.service.current_file_order):
            self.files_summary.controls.append(ft.Text(f"{index + 1}. {name}", size=12))


    def on_attach(self):
        """Prepares the save dialog overlay."""
        if self.save_dialog not in self.page.overlay:
            self.page.overlay.append(self.save_dialog)

        self.refresh_summary()
        self.page.update()


    def on_save_click(self, _):
        """Triggers the system save dialog for the result ZIP."""
        full_input_name = os.path.basename(self.service.uploaded_file_path)
        name_part, extension = os.path.splitext(full_input_name)
        default_output_name = f"{name_part}{EXPORT_FILE_SUFFIX}{extension}"

        self.save_dialog.save_file(
            file_name=default_output_name, 
            allowed_extensions=["zip"]
        )


    def on_export_finished(self, event: ft.FilePickerUploadEvent):
        """Handles the completion of the file export process."""
        if event.path:
            self.export_progress.visible = True
            self.update()
            
            final_data = self.service.logic_prepare_final_data()
            self.service.zip_service.createZipWithAddedConfig(
                originalZipPath=self.service.uploaded_file_path,
                targetZipPath=event.path,
                configurationData=final_data
            )
            
            self.export_progress.visible = False
            self.update()


class MachineApp:
    """
    Main Application Controller and Router.
    Orchestrates view transitions and maintains the shared logic service.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self.service = MachineBusinessLogic()

        self.page.title = "Test Configuration Wizard"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        self.page.on_route_change = self.on_handle_route
        self.page.on_view_pop = self.on_handle_pop

        # Central Route Mapping
        self.view_factories = {
            "/": lambda: UploadView(self.service, self.page.go),
            "/editor": lambda: EditorView(self.service, self.page.go),
            "/result": lambda: ResultView(self.service, self.page.go),
        }

        if self.page.route == "/":
            self.on_handle_route(None)
        else:
            self.page.go("/")


    def on_handle_route(self, _):
        """Handles navigation safely by building the view before clearing the stack."""
        try:
            builder = self.view_factories.get(self.page.route, self.view_factories["/"])
            new_view = builder()

            self.page.views.clear()
            self.page.overlay.clear()

            if hasattr(new_view, "file_picker"):
                self.page.overlay.append(new_view.file_picker)
            if hasattr(new_view, "save_dialog"):
                self.page.overlay.append(new_view.save_dialog)

            self.page.views.append(new_view)
            self.page.update()

            if hasattr(new_view, "on_attach"):
                new_view.on_attach()

        except Exception:
            import traceback
            error_stack = traceback.format_exc()
            self.page.views.clear()
            self.page.views.append(
                ft.View(
                    controls=[
                        ft.AppBar(title=ft.Text("Kritischer Fehler"), bgcolor=ft.Colors.RED_100),
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Die App konnte die Seite nicht laden:", weight="bold"),
                                ft.Text(error_stack, color=ft.Colors.RED, size=12, selectable=True),
                                ft.ElevatedButton("Zurück zum Start", on_click=lambda _: self.page.go("/"))
                            ], scroll=ft.ScrollMode.AUTO),
                            padding=20
                        )
                    ]
                )
            )
            self.page.update()


    def on_handle_pop(self, _):
        """Handles back-button navigation in the view stack."""
        if len(self.page.views) > 1:
            self.page.views.pop()
            top_view = self.page.views[-1]
            self.page.go(top_view.route)