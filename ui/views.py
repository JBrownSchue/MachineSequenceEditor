import flet as ft
import os
import shutil

from helper import ZipService


UPLOAD_DIRECTORY_NAME = "uploads"
MACHINE_TYPE_PREFIX_STRING = ";MACHINE_TYPE_"
REAL_MACHINE_ID_PREFIX_STRING = "REAL_MACHINE_TYPE:"


os.makedirs(
    UPLOAD_DIRECTORY_NAME,
    exist_ok=True
)


def getUploadView(
    pageContext: ft.Page
) -> ft.View:
    """
    @brief Creates and returns the Upload View (Page 1).
    @param pageContext The current Flet page instance.
    @return The constructed ft.View object.
    """

    statusTextControl = ft.Text()

    proceedButtonControl = ft.ElevatedButton(
        text="Nächster Schritt: Sequenz Editor",
        icon=ft.Icons.ARROW_FORWARD,
        disabled=True
    )

    def handleFilePickerResult(
        eventDetails: ft.FilePickerResultEvent
    ):
        if eventDetails.files:

            firstFileObject = eventDetails.files[0]
            fileName = firstFileObject.name

            destinationPath = os.path.join(
                UPLOAD_DIRECTORY_NAME,
                fileName
            )

            shutil.copy2(
                firstFileObject.path,
                destinationPath
            )

            pageContext.session.set(
                "uploadedFilePath",
                destinationPath
            )

            statusTextControl.value = f"Ausgewählte Datei: {fileName}"
            statusTextControl.update()

            proceedButtonControl.disabled = False
            proceedButtonControl.update()

    def handleProceedButtonClick(
        eventDetails
    ):
        pageContext.go(
            "/editor"
        )

    proceedButtonControl.on_click = handleProceedButtonClick

    filePickerControl = ft.FilePicker(
        on_result=handleFilePickerResult
    )

    if filePickerControl not in pageContext.overlay:
        pageContext.overlay.append(
            filePickerControl
        )

    def triggerFilePick(
        eventDetails
    ):
        filePickerControl.pick_files(
            allow_multiple=False,
            allowed_extensions=["zip"]
        )

    uploadButtonControl = ft.ElevatedButton(
        text="Wähle eine ZIP Datei aus",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=triggerFilePick
    )

    headerIcon = ft.Icon(
        name=ft.Icons.UPLOAD_FILE,
        size=50
    )

    instructionText = ft.Text(
        value="Bitte lade deine ZIP Datei hoch.",
        size=20
    )

    divider = ft.Divider()

    layoutColumn = ft.Column(
        controls=[
            headerIcon,
            instructionText,
            uploadButtonControl,
            statusTextControl,
            divider,
            proceedButtonControl
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )

    mainContainer = ft.Container(
        content=layoutColumn,
        padding=50,
        alignment=ft.alignment.center
    )

    appBar = ft.AppBar(
        title=ft.Text(
            value="Schritt 1: ZIP Hochladen"
        ),
        bgcolor=ft.Colors.BLUE_GREY_100
    )

    return ft.View(
        route="/",
        controls=[
            appBar,
            mainContainer
        ]
    )


def getEditorView(
    pageContext: ft.Page
) -> ft.View:
    """
    @brief Creates the Sequence Editor View (Page 2).
    @details Loads machine config, handles dependency logic (Shelf/RobotMode), MountCount validation, and file reordering.
    @param pageContext The current Flet page instance.
    @return The constructed ft.View object.
    """

    uploadedZipPath = pageContext.session.get(
        "uploadedFilePath"
    )
    zipServiceInstance = ZipService()
    listOfUiControls = []

    machineIdDisplayString = "Unknown Machine"
    machineModelName = "UNKNOWN"

    rawConfigContentString = zipServiceInstance.readSingleFile(
        uploadedZipPath,
        "Configuration/MainKonfiguration.txt"
    )

    if rawConfigContentString:
        machineDefinitionsMap = {}
        foundRealIdString = None

        for line in rawConfigContentString.splitlines():
            line = line.strip()
            if line.startswith(MACHINE_TYPE_PREFIX_STRING) and "=" in line:
                parts = line.split("=")
                if len(parts) == 2:
                    machineDefinitionsMap[parts[1].strip()] = parts[0].strip()[
                        len(MACHINE_TYPE_PREFIX_STRING):]
            elif line.startswith(REAL_MACHINE_ID_PREFIX_STRING):
                parts = line.split(":")
                if len(parts) > 1:
                    foundRealIdString = parts[1].strip()

        idIsFound = foundRealIdString is not None
        idIsInMap = foundRealIdString in machineDefinitionsMap

        if idIsFound and idIsInMap:
            realName = machineDefinitionsMap[foundRealIdString]
            machineModelName = realName
            machineIdDisplayString = realName.replace("_", " ")
        elif idIsFound:
            machineModelName = foundRealIdString
            machineIdDisplayString = f"ID {foundRealIdString}"

    initialMountCount = 0
    if machineModelName in ["AF500", "AF510", "AS100"]:
        initialMountCount = 1

    headerTextLabel = ft.Text(
        value="Erkannte Maschinen Konfiguration:",
        size=12,
        color=ft.Colors.GREY
    )

    headerTextValue = ft.Text(
        value=f"{machineIdDisplayString}",
        size=24,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.BLUE_GREY_900
    )

    headerDivider = ft.Divider()

    headerColumn = ft.Column(
        controls=[
            headerTextLabel,
            headerTextValue,
            headerDivider
        ]
    )

    headerContainer = ft.Container(
        content=headerColumn,
        padding=ft.padding.only(
            bottom=5
        )
    )
    listOfUiControls.append(headerContainer)

    mountCountHintText = ft.Text(
        value="Range: 0-25",
        size=12,
        color=ft.Colors.GREY
    )

    featureStateDictionary = {
        "ShiftCutDevice": False,
        "createShelf": False,
        "createBigShelf": False,
        "RobotMode": False
    }

    def updateMountCountLogic(
        _e=None,
        data_only=False
    ):
        min_mc = 0
        max_mc = 25
        info_text = ""

        isSmallShelf = featureStateDictionary.get("createShelf", False)
        isBigShelf = featureStateDictionary.get("createBigShelf", False)

        if isSmallShelf:
            min_mc = 1
            max_mc = 9
            info_text = "(Small Shelf Limit)"
        elif isBigShelf:
            min_mc = 1
            max_mc = 25
            info_text = "(Big Shelf Limit)"
        elif machineModelName == "AS100":
            min_mc = 1
            max_mc = 10
            info_text = "(AS100 Limit)"

        mountCountHintText.value = f"Bereich: {min_mc} - {max_mc} {info_text}"

        try:
            val = int(
                mountCountInputControl.value) if mountCountInputControl.value else 0
        except ValueError:
            val = 0

        if val > max_mc:
            val = max_mc
            mountCountInputControl.value = str(val)
        elif val < min_mc:
            val = min_mc
            mountCountInputControl.value = str(val)

        if val < min_mc or val > max_mc:
            mountCountInputControl.border_color = ft.Colors.RED
            mountCountHintText.color = ft.Colors.RED
        else:
            mountCountInputControl.border_color = ft.Colors.TEAL_600
            mountCountHintText.color = ft.Colors.GREY

        if not data_only:
            mountCountHintText.update()
            mountCountInputControl.update()

    def handleMountCountFocus(
        eventDetails
    ):
        if eventDetails.control.value and len(eventDetails.control.value) == 1:
            eventDetails.control.value = ""
            eventDetails.control.update()

    def handleMountCountBlur(
        eventDetails
    ):
        if not eventDetails.control.value:
            eventDetails.control.value = "0"
            eventDetails.control.update()
        updateMountCountLogic()

    mountCountInputControl = ft.TextField(
        value=str(initialMountCount),
        label="MountCount",
        width=150,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(
            allow=True,
            regex_string=r"[0-9]",
            replacement_string=""
        ),
        on_focus=handleMountCountFocus,
        on_blur=handleMountCountBlur,
        on_change=updateMountCountLogic,
        border_color=ft.Colors.TEAL_600,
        focused_border_color=ft.Colors.TEAL_900
    )

    featuresColumn = ft.Column(
        spacing=5
    )

    def renderFeatureControls():
        featuresColumn.controls.clear()

        featureOrder = ["createShelf", "createBigShelf",
                        "RobotMode", "ShiftCutDevice"]
        controlsList = []

        for featureName in featureOrder:
            isFeatureActive = featureStateDictionary.get(featureName, False)

            isRobotMode = (featureName == "RobotMode")

            anyShelfActive = featureStateDictionary.get(
                "createShelf") or featureStateDictionary.get("createBigShelf")

            isDisabled = False

            if isRobotMode and not anyShelfActive:
                isDisabled = True
                isFeatureActive = False
                featureStateDictionary["RobotMode"] = False

            displayLabel = featureName
            if featureName == "createShelf":
                displayLabel = "Create Shelf (Small)"
            elif featureName == "createBigShelf":
                displayLabel = "Create Shelf (Big)"

            iconData = ft.Icons.CHECK_CIRCLE if isFeatureActive else ft.Icons.CANCEL
            iconColor = ft.Colors.GREEN if isFeatureActive else ft.Colors.RED_400

            if isDisabled:
                iconColor = ft.Colors.GREY_400
                displayLabel += " (Benötigt ein Shelf)"

            def createToggleHandler(targetFeature):
                def handler(eventDetails):
                    currentVal = featureStateDictionary.get(
                        targetFeature, False)
                    newState = not currentVal
                    featureStateDictionary[targetFeature] = newState

                    if targetFeature == "createShelf" and newState is True:
                        featureStateDictionary["createBigShelf"] = False
                        featureStateDictionary["RobotMode"] = True
                        featureStateDictionary["ShiftCutDevice"] = False

                    if targetFeature == "createBigShelf" and newState is True:
                        featureStateDictionary["createShelf"] = False
                        featureStateDictionary["RobotMode"] = True
                        featureStateDictionary["ShiftCutDevice"] = False

                    if targetFeature == "ShiftCutDevice" and newState is True:
                        if featureStateDictionary.get("createShelf") or featureStateDictionary.get("createBigShelf"):
                            featureStateDictionary["ShiftCutDevice"] = False

                    renderFeatureControls()
                    updateMountCountLogic()
                    pageContext.update()
                return handler

            toggleButton = ft.IconButton(
                icon=iconData,
                icon_color=iconColor,
                on_click=createToggleHandler(featureName),
                disabled=isDisabled,
                tooltip=f"Umschalten {featureName}"
            )

            labelText = ft.Text(
                value=displayLabel,
                color=ft.Colors.BLACK if not isDisabled else ft.Colors.GREY,
                weight=ft.FontWeight.BOLD
            )

            featureRow = ft.Row(
                controls=[
                    toggleButton,
                    labelText
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )

            rowContainer = ft.Container(
                content=featureRow,
                bgcolor=ft.Colors.WHITE,
                border_radius=5,
                padding=ft.padding.symmetric(
                    horizontal=10,
                    vertical=0
                )
            )

            controlsList.append(rowContainer)

        featureListColumn = ft.Column(
            controls=controlsList
        )

        featureListContainer = ft.Container(
            content=featureListColumn,
            bgcolor=ft.Colors.BLUE_GREY_50,
            padding=10,
            border_radius=8,
            border=ft.border.all(
                width=1,
                color=ft.Colors.BLUE_GREY_200
            )
        )

        featuresColumn.controls.append(
            featureListContainer
        )

    currentFileOrderList = []
    initialFolder = "Bars/"
    editorStateDictionary = {
        "activeFolder": initialFolder,
        "isBarsMode": True
    }

    filesListViewColumn = ft.Column(
        spacing=8
    )

    def renderFileSequenceList():
        filesListViewColumn.controls.clear()

        if not currentFileOrderList:
            activeFolderName = editorStateDictionary['activeFolder']
            emptyText = ft.Text(
                value=f"Keine Dateien gefunden in {activeFolderName}",
                italic=True,
                color=ft.Colors.GREY
            )
            filesListViewColumn.controls.append(emptyText)

        totalItemCount = len(currentFileOrderList)

        for itemIndex, fileNameString in enumerate(currentFileOrderList):

            def createMoveUpHandler(targetIndex):
                def handler(eventDetails):
                    if targetIndex > 0:
                        currentFileOrderList[targetIndex], currentFileOrderList[targetIndex -
                                                                                1] = currentFileOrderList[targetIndex-1], currentFileOrderList[targetIndex]
                        renderFileSequenceList()
                        pageContext.update()
                return handler

            def createMoveDownHandler(targetIndex):
                def handler(eventDetails):
                    if targetIndex < totalItemCount - 1:
                        currentFileOrderList[targetIndex], currentFileOrderList[targetIndex +
                                                                                1] = currentFileOrderList[targetIndex+1], currentFileOrderList[targetIndex]
                        renderFileSequenceList()
                        pageContext.update()
                return handler

            def createRowVisualContainer(isItemBeingDragged=False):
                isFirst = (itemIndex == 0)
                isLast = (itemIndex == totalItemCount - 1)

                bgCol = ft.Colors.BLUE_50 if isItemBeingDragged else ft.Colors.WHITE
                borderCol = ft.Colors.BLUE if isItemBeingDragged else ft.Colors.GREY_300

                dragHandleIcon = ft.Icon(
                    name=ft.Icons.DRAG_HANDLE,
                    color=ft.Colors.GREY_400
                )

                indexText = ft.Text(
                    value=f"{itemIndex + 1}",
                    color=ft.Colors.WHITE,
                    size=10,
                    weight=ft.FontWeight.BOLD
                )

                indexContainer = ft.Container(
                    content=indexText,
                    bgcolor=ft.Colors.BLUE_GREY_400,
                    padding=5,
                    border_radius=10,
                    width=25,
                    alignment=ft.alignment.center
                )

                displayName = os.path.splitext(fileNameString)[0]

                fileNameText = ft.Text(
                    value=displayName,
                    size=15,
                    weight=ft.FontWeight.W_500
                )

                leftSideRow = ft.Row(
                    controls=[
                        dragHandleIcon,
                        indexContainer,
                        fileNameText
                    ]
                )

                arrowUpButton = ft.IconButton(
                    icon=ft.Icons.ARROW_UPWARD,
                    icon_size=20,
                    icon_color=ft.Colors.BLUE,
                    opacity=0 if isFirst else 1,
                    disabled=isFirst,
                    on_click=createMoveUpHandler(itemIndex)
                )

                arrowDownButton = ft.IconButton(
                    icon=ft.Icons.ARROW_DOWNWARD,
                    icon_size=20,
                    icon_color=ft.Colors.BLUE,
                    opacity=0 if isLast else 1,
                    disabled=isLast,
                    on_click=createMoveDownHandler(itemIndex)
                )

                rightSideRow = ft.Row(
                    controls=[
                        arrowUpButton,
                        arrowDownButton
                    ]
                )

                mainRow = ft.Row(
                    controls=[
                        leftSideRow,
                        rightSideRow
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )

                return ft.Container(
                    content=mainRow,
                    padding=10,
                    bgcolor=bgCol,
                    border=ft.border.all(
                        width=1,
                        color=borderCol
                    ),
                    border_radius=8,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=3,
                        color=ft.Colors.GREY_200,
                        offset=ft.Offset(0, 2)
                    )
                )

            def createDragAcceptHandler(destinationIndex):
                def handler(eventDetails):
                    srcIdx = int(pageContext.get_control(
                        eventDetails.src_id).data)
                    if srcIdx != destinationIndex:
                        item = currentFileOrderList.pop(srcIdx)
                        currentFileOrderList.insert(destinationIndex, item)
                        renderFileSequenceList()
                        pageContext.update()
                    else:
                        eventDetails.control.content.content.bgcolor = ft.Colors.WHITE
                        eventDetails.control.update()
                return handler

            draggable = ft.Draggable(
                group="file_items",
                content=createRowVisualContainer(
                    isItemBeingDragged=False
                ),
                content_feedback=ft.Container(
                    content=createRowVisualContainer(
                        isItemBeingDragged=True
                    ),
                    opacity=0.7
                ),
                data=str(itemIndex)
            )

            target = ft.DragTarget(
                group="file_items",
                content=draggable,
                on_accept=createDragAcceptHandler(itemIndex),
                on_will_accept=lambda e: (setattr(
                    e.control.content.content, 'bgcolor', ft.Colors.BLUE_50), e.control.update()),
                on_leave=lambda e: (setattr(
                    e.control.content.content, 'bgcolor', ft.Colors.WHITE), e.control.update())
            )
            filesListViewColumn.controls.append(target)

    def handleModeSwitchEvent(eventDetails):
        editorStateDictionary["isBarsMode"] = eventDetails.control.value
        modeLabel.value = "Test Bars" if eventDetails.control.value else "Test Profiles"
        loadFilesForCurrentMode()
        renderFileSequenceList()
        pageContext.update()

    modeSwitch = ft.Switch(
        value=True,
        active_color=ft.Colors.BLUE_600,
        on_change=handleModeSwitchEvent
    )

    modeLabel = ft.Text(
        value="Test Bars",
        weight=ft.FontWeight.BOLD,
        size=16
    )

    def loadFilesForCurrentMode():
        isBars = editorStateDictionary["isBarsMode"]
        folder = "Bars/" if isBars else "Profiles/"
        editorStateDictionary["activeFolder"] = folder
        currentFileOrderList.clear()
        currentFileOrderList.extend(
            zipServiceInstance.getFileNamesInFolder(uploadedZipPath, folder)
        )

    loadFilesForCurrentMode()
    renderFileSequenceList()

    modeRow = ft.Row(
        controls=[
            modeSwitch,
            modeLabel
        ],
        alignment=ft.MainAxisAlignment.START
    )

    mountCountIcon = ft.Icon(
        name=ft.Icons.NUMBERS,
        size=20,
        color=ft.Colors.TEAL_700
    )

    mountCountColumn = ft.Column(
        controls=[
            mountCountInputControl,
            mountCountHintText
        ],
        spacing=0
    )

    mountCountRow = ft.Row(
        controls=[
            mountCountIcon,
            mountCountColumn
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    controlsMainRow = ft.Row(
        controls=[
            modeRow,
            mountCountRow
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    controlsRowContainer = ft.Container(
        content=controlsMainRow,
        bgcolor=ft.Colors.BLUE_GREY_50,
        padding=10,
        border_radius=8,
        border=ft.border.all(
            width=1,
            color=ft.Colors.BLUE_GREY_200
        )
    )
    listOfUiControls.append(controlsRowContainer)

    featureHeader = ft.Text(
        value="Features Konfigurieren:",
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.GREY_800
    )
    listOfUiControls.append(featureHeader)

    renderFeatureControls()
    listOfUiControls.append(featuresColumn)

    spacer = ft.Container(height=10)
    listOfUiControls.append(spacer)

    listOfUiControls.append(filesListViewColumn)

    def handleProceedButtonClick(eventDetails):
        pageContext.session.set("finalFileOrder", currentFileOrderList)
        pageContext.session.set(
            "activeFolder", editorStateDictionary["activeFolder"])
        pageContext.session.set("machineModel", machineModelName)

        finalFeaturesList = []

        for featKey, featActive in featureStateDictionary.items():
            if featActive:
                singleFeatureObject = {}

                if featKey == "createShelf":
                    singleFeatureObject["createShelf"] = "smallShelf"
                    finalFeaturesList.append(singleFeatureObject)
                elif featKey == "createBigShelf":
                    singleFeatureObject["createShelf"] = "bigShelf"
                    finalFeaturesList.append(singleFeatureObject)
                else:
                    singleFeatureObject[featKey] = featActive
                    finalFeaturesList.append(singleFeatureObject)

        pageContext.session.set("finalFeatures", finalFeaturesList)

        try:
            currentMountCountValue = int(mountCountInputControl.value)
        except ValueError:
            currentMountCountValue = 0

        pageContext.session.set("finalMountCount", currentMountCountValue)
        pageContext.go("/result")

    saveButtonControl = ft.ElevatedButton(
        text="Sequenz bestätigen & Beenden",
        icon=ft.Icons.CHECK_CIRCLE,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_600,
            padding=20
        ),
        on_click=handleProceedButtonClick
    )

    bottomSpacer = ft.Container(height=30)
    listOfUiControls.append(bottomSpacer)
    listOfUiControls.append(saveButtonControl)

    updateMountCountLogic(data_only=True)

    mainColumn = ft.Column(
        controls=listOfUiControls
    )

    mainContainer = ft.Container(
        content=mainColumn,
        padding=20
    )

    appBarControl = ft.AppBar(
        title=ft.Text("Sequenz Editor"),
        bgcolor=ft.Colors.BLUE_GREY_100
    )

    return ft.View(
        route="/editor",
        scroll=ft.ScrollMode.AUTO,
        controls=[
            appBarControl,
            mainContainer
        ]
    )


def getResultView(
    pageContext: ft.Page
) -> ft.View:
    """
    @brief Creates and returns the Result View (Page 3).
    @details Displays the summary, handles the final ZIP export with the generated config.json, and allows downloading.
    @param pageContext The current Flet page instance.
    @return The constructed ft.View object.
    """

    finalFileSequence = pageContext.session.get("finalFileOrder") or []
    activeFolderName = pageContext.session.get("activeFolder") or "Unknown"
    featuresData = pageContext.session.get("finalFeatures") or []
    finalMountCount = pageContext.session.get("finalMountCount") or 0
    originalZipPath = pageContext.session.get("uploadedFilePath")
    finalMachineModel = pageContext.session.get("machineModel") or "UNKNOWN"

    zipServiceInstance = ZipService()

    progressBarControl = ft.ProgressBar(
        width=400,
        color=ft.Colors.BLUE,
        bgcolor=ft.Colors.BLUE_100,
        visible=False
    )

    saveFilePickerControl = ft.FilePicker()
    if saveFilePickerControl not in pageContext.overlay:
        pageContext.overlay.append(saveFilePickerControl)

    def handleFileSaveResult(eventDetails: ft.FilePickerResultEvent):
        targetPath = eventDetails.path
        if targetPath:
            progressBarControl.visible = True
            downloadButtonControl.disabled = True
            pageContext.update()

            isTestBars = "Bars" in activeFolderName

            finalConfigurationData = {
                "MachineModel": finalMachineModel,
                "TestBars": isTestBars,
                "FileOrder": finalFileSequence,
                "MountCount": finalMountCount,
                "Features": featuresData
            }

            success = zipServiceInstance.createZipWithAddedConfig(
                originalZipPath=originalZipPath,
                targetZipPath=targetPath,
                configurationData=finalConfigurationData
            )

            progressBarControl.visible = False
            downloadButtonControl.disabled = False
            pageContext.update()

            if success:
                pageContext.open(
                    ft.SnackBar(
                        content=ft.Text(
                            f"Erfolg! Gespeichert unter {os.path.basename(targetPath)}"),
                        bgcolor=ft.Colors.GREEN
                    )
                )
            else:
                pageContext.open(
                    ft.SnackBar(
                        content=ft.Text("Fehler beim Speichern der Datei."),
                        bgcolor=ft.Colors.RED
                    )
                )

    saveFilePickerControl.on_result = handleFileSaveResult

    def openSaveFileDialog(eventDetails):
        suggestedName = "configured_machine.zip"
        if originalZipPath:
            baseName = os.path.basename(originalZipPath)
            fileNameWithoutExt, _ = os.path.splitext(baseName)
            suggestedName = f"{fileNameWithoutExt}_configured.zip"

        saveFilePickerControl.save_file(
            file_name=suggestedName,
            allowed_extensions=["zip"]
        )

    def triggerRestart(eventDetails):
        pageContext.go("/")

    isTestBarsUI = "Bars" in activeFolderName
    modeDisplayString = "Bars Mode" if isTestBarsUI else "Profiles Mode"

    resultListColumn = ft.Column(spacing=2)
    for i, f in enumerate(finalFileSequence):
        resultListColumn.controls.append(
            ft.Text(
                value=f"{i+1}. {f}",
                size=14
            )
        )

    resultListContainer = ft.Container(
        content=resultListColumn,
        padding=15,
        bgcolor=ft.Colors.GREY_100,
        border_radius=8,
        border=ft.border.all(
            width=1,
            color=ft.Colors.GREY_300
        ),
        width=400,
        height=150,
    )

    featuresColumn = ft.Column(spacing=2)
    featuresColumn.controls.append(
        ft.Text(
            value=f"Machine: {finalMachineModel}",
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_800
        )
    )
    featuresColumn.controls.append(
        ft.Text(
            value=f"MountCount: {finalMountCount}",
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_800
        )
    )
    featuresColumn.controls.append(
        ft.Text(
            value=f"TestBars: {isTestBarsUI}",
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_800
        )
    )

    for featureObject in featuresData:
        for key, value in featureObject.items():
            featuresColumn.controls.append(
                ft.Text(
                    value=f"{key}: {value}",
                    size=12,
                    color=ft.Colors.BLUE_GREY_800
                )
            )

    featuresPreviewContainer = ft.Container(
        content=featuresColumn,
        padding=10,
        border=ft.border.all(
            width=1,
            color=ft.Colors.BLUE_100
        ),
        bgcolor=ft.Colors.BLUE_50,
        border_radius=5,
        width=400
    )

    downloadButtonControl = ft.ElevatedButton(
        text="Konfigurierte ZIP-Datei herunterladen",
        icon=ft.Icons.DOWNLOAD,
        on_click=openSaveFileDialog
    )

    restartButtonControl = ft.OutlinedButton(
        text="Neu starten",
        on_click=triggerRestart
    )

    successIcon = ft.Icon(
        name=ft.Icons.TASK_ALT,
        color=ft.Colors.GREEN,
        size=60
    )

    summaryText = ft.Text(
        value=f"Sequenz für '{modeDisplayString}' definiert.",
        size=20,
        weight=ft.FontWeight.BOLD
    )

    featureHeader = ft.Text(
        value="Features zu speichern:",
        weight=ft.FontWeight.BOLD
    )

    fileOrderHeader = ft.Text(
        value="Endgültige Dateireihenfolge:",
        weight=ft.FontWeight.BOLD
    )

    spacer = ft.Container(height=20)

    layoutColumn = ft.Column(
        controls=[
            successIcon,
            summaryText,
            featureHeader,
            featuresPreviewContainer,
            fileOrderHeader,
            resultListContainer,
            spacer,
            progressBarControl,
            downloadButtonControl,
            restartButtonControl
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    mainContainer = ft.Container(
        content=layoutColumn,
        alignment=ft.alignment.center,
        padding=15
    )

    appBarControl = ft.AppBar(
        title=ft.Text("Prozess abgeschlossen"),
        bgcolor=ft.Colors.GREEN_100
    )

    return ft.View(
        route="/result",
        scroll=ft.ScrollMode.AUTO,
        controls=[
            appBarControl,
            mainContainer
        ]
    )
