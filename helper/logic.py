import os
import shutil
from .zipService import ZipService

# Configuration Constants
UPLOAD_DIRECTORY_NAME = "uploads"
MACHINE_TYPE_PREFIX = ";MACHINE_TYPE_"
REAL_MACHINE_ID_PREFIX = "REAL_MACHINE_TYPE:"

FOLDER_BARS = "Bars/"
FOLDER_PROFILES = "Profiles/"
XML_TAG_IST = "Is_Number"
XML_TAG_SOLL = "ReferenceValue"

# Machine Specific Limits
DEFAULT_MIN_MOUNT_COUNT = 0
DEFAULT_MAX_MOUNT_COUNT = 25
SMALL_SHELF_LIMIT = 9
AS100_MODEL_LIMIT = 10
MIN_COUNT_FOR_EQUIPPED_MODELS = 1

# Features
FEATURE_SHIFT_CUT = "ShiftCutDevice"
FEATURE_SHELF_SMALL = "createShelf"
FEATURE_SHELF_BIG = "createBigShelf"
FEATURE_ROBOT_MODE = "RobotMode"

# Konstanten für die Parsing-Logik
EXPECTED_KV_PARTS = 2
INDEX_KEY = 0
INDEX_VALUE = 1

# Mount Counts
MOUNT_REQUIRED = 1
MOUNT_NOT_REQUIRED = 0
MODELS_WITH_MOUNT = {"AF500", "AF510", "AS100"}

SEPARATOR_ASSIGNMENT = "="
SEPARATOR_PROPERTY = ":"

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
        self.active_folder = FOLDER_BARS
        self.is_bars_mode = True
        self.current_file_order = []
        self.extracted_xml_data = {}
        
        self.feature_state = {
            FEATURE_SHIFT_CUT: False,
            FEATURE_SHELF_SMALL: False,
            FEATURE_SHELF_BIG: False,
            FEATURE_ROBOT_MODE: False
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
            
            if line.startswith(MACHINE_TYPE_PREFIX) and SEPARATOR_ASSIGNMENT in line:
                parts = [p.strip() for p in line.split(SEPARATOR_ASSIGNMENT)]
                if len(parts) == EXPECTED_KV_PARTS:
                    key_part, value_part = parts
                    clean_key = key_part[len(MACHINE_TYPE_PREFIX):]
                    machine_definitions_map[value_part] = clean_key

            elif line.startswith(REAL_MACHINE_ID_PREFIX):
                parts = [p.strip() for p in line.split(SEPARATOR_PROPERTY)]
                if len(parts) >= EXPECTED_KV_PARTS:
                    found_real_id = parts[INDEX_VALUE]

        self._apply_machine_identity(found_real_id, machine_definitions_map)
        self._set_mount_count()

    def _apply_machine_identity(self, found_real_id, definitions_map):
        """Helper function to identify the machine"""
        if found_real_id and found_real_id in definitions_map:
            real_name = definitions_map[found_real_id]
            self.machine_model_name = real_name
            self.machine_display_string = real_name.replace("_", " ")
        elif found_real_id:
            self.machine_model_name = found_real_id
            self.machine_display_string = f"ID {found_real_id}"

    def _set_mount_count(self):
        """Calculates the mount count dependend on the machine"""
        if self.machine_model_name in MODELS_WITH_MOUNT:
            self.mount_count = MOUNT_REQUIRED
        else:
            self.mount_count = MOUNT_NOT_REQUIRED


    def logic_validate_mount_count(self, user_input_text: str) -> tuple[str, bool, str]:
        """
        Validates the mount count using named limits instead of magic numbers.
        Returns: (clamped_value, has_error, hint_message)
        """
        min_allowed = DEFAULT_MIN_MOUNT_COUNT
        max_allowed = DEFAULT_MAX_MOUNT_COUNT
        limit_description = ""

        # Adjust limits based on active features or machine model
        if self.feature_state.get(FEATURE_SHELF_SMALL):
            min_allowed, max_allowed = MIN_COUNT_FOR_EQUIPPED_MODELS, SMALL_SHELF_LIMIT
            limit_description = "(Small Shelf Limit)"
        elif self.feature_state.get(FEATURE_SHELF_BIG):
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
        states = self.feature_state
        if feature_name in [FEATURE_SHELF_SMALL, FEATURE_SHELF_BIG] and states[feature_name]:
            other = FEATURE_SHELF_BIG if feature_name == FEATURE_SHELF_SMALL else FEATURE_SHELF_SMALL
            states[other] = False
            states[FEATURE_ROBOT_MODE] = True
            states[FEATURE_SHIFT_CUT] = False
        else:
            if not states[FEATURE_SHELF_SMALL] and not states[FEATURE_SHELF_BIG]:
                states[FEATURE_ROBOT_MODE] = False

        if feature_name == FEATURE_SHIFT_CUT and states[FEATURE_SHIFT_CUT]:
            if states[FEATURE_SHELF_SMALL] or states[FEATURE_SHELF_BIG]:
                states[FEATURE_SHIFT_CUT] = False
            else:
                self.is_bars_mode = True
                self.logic_load_files_for_mode()
                self.logic_load_xml_data_for_files()

    def logic_is_mode_switch_allowed(self) -> bool:
        """CHECKS if you are allowed to switch between Bars and Profiles"""
        return not self.feature_state.get(FEATURE_SHIFT_CUT, False)

    def logic_load_files_for_mode(self) -> None:
        """Fetches file names from the ZIP for the selected mode."""
        self.active_folder = "Bars/" if self.is_bars_mode else "Profiles/"
        self.current_file_order = self.zip_service.getFileNamesInFolder(
            self.uploaded_file_path, self.active_folder
        )


    def logic_load_xml_data_for_files(self) -> None:
        """
        Loads IST- and SOLL-Values from the XML in Bars/ and Profiles/.
        """
        if not self.uploaded_file_path:
            return

        target_folders = [FOLDER_BARS, FOLDER_PROFILES]
        tags_to_find = [XML_TAG_IST, XML_TAG_SOLL]

        raw_results = self.zip_service.extractXmlDataFromFolders(
            self.uploaded_file_path, 
            target_folders, 
            tags_to_find
        )

        self.extracted_xml_data = raw_results


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
                if key == FEATURE_SHELF_SMALL: final_features.append({FEATURE_SHELF_SMALL: "smallShelf"})
                elif key == FEATURE_SHELF_BIG: final_features.append({FEATURE_SHELF_SMALL: "bigShelf"})
                else: final_features.append({key: active})
        return {
            "MachineModel": self.machine_model_name,
            "TestBars": self.is_bars_mode,
            "FileOrder": self.current_file_order,
            "MountCount": self.mount_count,
            "Features": final_features
        }