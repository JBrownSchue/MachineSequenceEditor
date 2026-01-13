from typing import Protocol, List, Dict, Any

class IMachineService(Protocol):
    """
    Interface for the Machine Sequence Business Logic.
    Defines the contract that any implementation must fulfill to work with the UI.
    """
    
    # Attributes
    machine_model_name: str
    machine_display_string: str
    mount_count: int
    feature_state: Dict[str, bool]
    current_file_order: List[str]
    is_bars_mode: bool
    uploaded_file_path: str
    extracted_xml_data: Dict[str, Dict[str, str]]


    def logic_handle_upload(self, file_info: Any) -> str:
        """
        Processes the uploaded file and stores it locally.
        
        Args:
            file_obj: The file object from the Flet FilePicker.
            
        Returns:
            str: The name of the successfully uploaded file.
        """
        ...


    def logic_parse_config(self) -> None:
        """
        Reads the configuration file from the uploaded ZIP and determines the machine type.
        """
        ...


    def logic_validate_mount_count(self, user_input_text: str) -> tuple[str, bool, str]:
        """
        Validates the mount count input based on machine constraints and active features.
        
        Returns:
            tuple: (clamped_value_string, is_error_boolean, hint_text_string)
        """
        ...


    def logic_toggle_feature(self, feature_name: str) -> None:
        """
        Toggles a specific machine feature and handles logic dependencies (e.g., shelf mutual exclusivity).
        """
        ...

    def logic_is_mode_switch_allowed(self) -> None:
        """CHECKS if you are allowed to switch between Bars and Profiles"""
        ...

    def logic_load_files_for_mode(self) -> None:
        """
        Loads the list of files (Bars or Profiles) from the ZIP based on current mode.
        """
        ...

    def logic_load_xml_data_for_files(self) -> None:
        """
        Loads the IST and SOLL Number from Bars and Profiles from the ZIP.
        """
        ...


    def logic_move_file(self, from_index: int, to_index: int) -> None:
        """
        Moves a file within the current file order sequence.
        """
        ...


    def logic_reorder_drag_drop(self, source_index: int, destination_index: int) -> None:
        """
        Updates the file sequence after a drag-and-drop operation in the UI.
        """
        ...


    def logic_prepare_final_data(self) -> Dict[str, Any]:
        """
        Compiles all configuration data into a dictionary for the final ZIP creation.
        """
        ...