import os
import shutil
from .zipService import ZipService

# Configuration Constants
UPLOAD_DIRECTORY_NAME = "uploads"
MACHINE_TYPE_PREFIX = ";MACHINE_TYPE_"
REAL_MACHINE_ID_PREFIX = "REAL_MACHINE_TYPE:"

# Machine Specific Limits
DEFAULT_MIN_MOUNT_COUNT = 0
DEFAULT_MAX_MOUNT_COUNT = 25
SMALL_SHELF_LIMIT = 9
AS100_MODEL_LIMIT = 10
MIN_COUNT_FOR_EQUIPPED_MODELS = 1

class MachineBusinessLogic:
    """
    Concrete implementation of the machine sequence business logic.
    Handles data processing, file management, and configuration validation.
    """
    
    def __init__(self):
        self.zip_service = ZipService()
        self.uploaded_file_path = ""
        self.machine_model_name = "UNKNOWN"
        self.machine_display_string = "Unknown Machine"
        self.mount_count = DEFAULT_MIN_MOUNT_COUNT
        self.active_folder = "Bars/"
        self.is_bars_mode = True
        self.current_file_order = []
        
        self.feature_state = {
            "ShiftCutDevice": False,
            "createShelf": False,
            "createBigShelf": False,
            "RobotMode": False
        }
        os.makedirs(UPLOAD_DIRECTORY_NAME, exist_ok=True)


    def logic_handle_upload(self, file_info) -> str:
        """Copies the uploaded file from the picker to the local directory."""
        file_name = file_info.name
        destination_path = os.path.join(UPLOAD_DIRECTORY_NAME, file_name)
        shutil.copy2(file_info.path, destination_path)
        self.uploaded_file_path = destination_path
        return file_name


    def logic_parse_config(self) -> None:
        """Reads the configuration file and identifies the machine model."""
        raw_content = self.zip_service.readSingleFile(
            self.uploaded_file_path,
            "Configuration/MainKonfiguration.txt"
        )
        if not raw_content:
            return

        machine_definitions_map = {}
        found_real_id = None

        for line in raw_content.splitlines():
            line = line.strip()
            if line.startswith(MACHINE_TYPE_PREFIX) and "=" in line:
                parts = line.split("=")
                if len(parts) == 2:
                    machine_definitions_map[parts[1].strip()] = parts[0].strip()[
                        len(MACHINE_TYPE_PREFIX):]
            elif line.startswith(REAL_MACHINE_ID_PREFIX):
                parts = line.split(":")
                if len(parts) > 1:
                    found_real_id = parts[1].strip()

        if found_real_id and found_real_id in machine_definitions_map:
            real_name = machine_definitions_map[found_real_id]
            self.machine_model_name = real_name
            self.machine_display_string = real_name.replace("_", " ")
        elif found_real_id:
            self.machine_model_name = found_real_id
            self.machine_display_string = f"ID {found_real_id}"

        if self.machine_model_name in ["AF500", "AF510", "AS100"]:
            self.mount_count = 1
        else:
            self.mount_count = 0


    def logic_validate_mount_count(self, user_input_text: str) -> tuple[str, bool, str]:
        """
        Validates the mount count using named limits instead of magic numbers.
        Returns: (clamped_value, has_error, hint_message)
        """
        min_allowed = DEFAULT_MIN_MOUNT_COUNT
        max_allowed = DEFAULT_MAX_MOUNT_COUNT
        limit_description = ""

        # Adjust limits based on active features or machine model
        if self.feature_state.get("createShelf"):
            min_allowed, max_allowed = MIN_COUNT_FOR_EQUIPPED_MODELS, SMALL_SHELF_LIMIT
            limit_description = "(Small Shelf Limit)"
        elif self.feature_state.get("createBigShelf"):
            min_allowed, max_allowed = MIN_COUNT_FOR_EQUIPPED_MODELS, DEFAULT_MAX_MOUNT_COUNT
            limit_description = "(Big Shelf Limit)"
        elif self.machine_model_name == "AS100":
            min_allowed, max_allowed = MIN_COUNT_FOR_EQUIPPED_MODELS, AS100_MODEL_LIMIT
            limit_description = "(AS100 Limit)"

        try:
            numeric_value = int(user_input_text) if user_input_text else DEFAULT_MIN_MOUNT_COUNT
        except ValueError:
            numeric_value = DEFAULT_MIN_MOUNT_COUNT

        # Clamp the value between the allowed range
        clamped_value = max(min_allowed, min(numeric_value, max_allowed))
        self.mount_count = clamped_value
        
        has_error = (numeric_value < min_allowed or numeric_value > max_allowed)
        hint_message = f"Range: {min_allowed} - {max_allowed} {limit_description}"
        
        return str(clamped_value), has_error, hint_message


    def logic_toggle_feature(self, feature_name: str) -> None:
        """Toggles features and maintains logical consistency between options."""
        self.feature_state[feature_name] = not self.feature_state.get(feature_name, False)
        s = self.feature_state
        if feature_name in ["createShelf", "createBigShelf"] and s[feature_name]:
            other = "createBigShelf" if feature_name == "createShelf" else "createShelf"
            s[other] = False
            s["RobotMode"] = True
            s["ShiftCutDevice"] = False

        if feature_name == "ShiftCutDevice" and s["ShiftCutDevice"]:
            if s["createShelf"] or s["createBigShelf"]:
                s["ShiftCutDevice"] = False


    def logic_load_files_for_mode(self) -> None:
        """Fetches file names from the ZIP for the selected mode."""
        self.active_folder = "Bars/" if self.is_bars_mode else "Profiles/"
        self.current_file_order = self.zip_service.getFileNamesInFolder(
            self.uploaded_file_path, self.active_folder
        )


    def logic_reorder_drag_drop(self, source_index: int, destination_index: int) -> None:
        """Moves a file from its original position to a new position in the list."""
        if source_index != destination_index:
            moved_item = self.current_file_order.pop(source_index)
            self.current_file_order.insert(destination_index, moved_item)


    def logic_prepare_final_data(self) -> dict:
        """Formats all configuration data for final processing."""
        final_features = []
        for key, active in self.feature_state.items():
            if active:
                if key == "createShelf": final_features.append({"createShelf": "smallShelf"})
                elif key == "createBigShelf": final_features.append({"createShelf": "bigShelf"})
                else: final_features.append({key: active})
        return {
            "MachineModel": self.machine_model_name,
            "TestBars": self.is_bars_mode,
            "FileOrder": self.current_file_order,
            "MountCount": self.mount_count,
            "Features": final_features
        }