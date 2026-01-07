import zipfile
import os
import json
from typing import List, Dict, Any
import xml.etree.ElementTree as ET


class ZipService:
    """
    @brief Provides services to handle ZIP file operations.
    """

    def readContentFromZip(
        self,
        pathToZipFile: str,
        targetFolders: List[str]
    ) -> Dict[str, str]:
        """
        @brief Reads specific files from a ZIP archive that are located in target folders.
        @param pathToZipFile The absolute path to the ZIP file.
        @param targetFolders A list of folder names (ending with /) to filter the files.
        @return A dictionary containing the filename as key and file content as value.
        """

        extractedContentMap = {}

        pathExists = os.path.exists(pathToZipFile)
        if not pathExists:
            return extractedContentMap

        try:
            with zipfile.ZipFile(pathToZipFile, 'r') as zipFileHandle:

                unsortedFileNames = zipFileHandle.namelist()
                listOfFileNames = sorted(unsortedFileNames)

                for currentFileName in listOfFileNames:

                    isTargetFile = False

                    for targetFolderString in targetFolders:
                        startsWithFolder = currentFileName.startswith(
                            targetFolderString)

                        if startsWithFolder:
                            isTargetFile = True
                            break

                    isDirectory = currentFileName.endswith("/")
                    shouldProcessFile = isTargetFile and not isDirectory

                    if shouldProcessFile:
                        try:
                            with zipFileHandle.open(currentFileName) as fileHandle:
                                fileContentBytes = fileHandle.read()
                                fileContentString = fileContentBytes.decode(
                                    'utf-8')

                                extractedContentMap[currentFileName] = fileContentString

                        except Exception:
                            errorMessage = "Error: Could not decode file content."
                            extractedContentMap[currentFileName] = errorMessage

        except Exception as exceptionObject:
            print(f"Error reading zip: {exceptionObject}")

        return extractedContentMap


    def readSingleFile(
        self,
        pathToZipFile: str,
        targetFileName: str
    ) -> str:
        """
        @brief Reads the content of a single specific file from the ZIP archive.
        @param pathToZipFile The path to the ZIP file.
        @param targetFileName The exact path/name of the file inside the ZIP.
        @return Content of the file as string, or empty string if failed.
        """
        fileContentResult = ""

        pathExists = os.path.exists(pathToZipFile)
        if not pathExists:
            return fileContentResult

        try:
            with zipfile.ZipFile(pathToZipFile, 'r') as zipFileHandle:

                allFileNamesList = zipFileHandle.namelist()
                fileIsPresentInZip = targetFileName in allFileNamesList

                if fileIsPresentInZip:
                    with zipFileHandle.open(targetFileName) as fileHandle:
                        rawBytes = fileHandle.read()
                        fileContentResult = rawBytes.decode(
                            'utf-8', errors='ignore')
                else:
                    print(f"File {targetFileName} not found in ZIP.")

        except Exception as exceptionObject:
            print(f"Error reading single file: {exceptionObject}")

        return fileContentResult

    def extractXmlDataFromFolders(
        self,
        pathToZipFile: str,
        targetFolders: List[str],
        tagsToFind: List[str]
    ) -> Dict[str, Dict[str, str]]:
        """
        @brief Liest XML-Dateien aus bestimmten Ordnern und extrahiert spezifische Werte.
        @param targetFolders Liste der Ordner (z.B. ["FolderA/", "FolderB/"])
        @param tagsToFind Liste der XML-Tags, deren Text extrahiert werden soll.
        @return Ein Dictionary: { dateiname: { tag_name: wert } }
        """
        extractedDataMap = {}

        if not os.path.exists(pathToZipFile):
            return extractedDataMap

        try:
            with zipfile.ZipFile(pathToZipFile, 'r') as zipFileHandle:
                for fileName in zipFileHandle.namelist():
                    
                    isInTargetFolder = any(fileName.startswith(folder) for folder in targetFolders)
                    isXmlFile = fileName.lower().endswith('.xml')
                    
                    if isInTargetFolder and isXmlFile:
                        try:
                            with zipFileHandle.open(fileName) as fileHandle:
                                tree = ET.parse(fileHandle)
                                root = tree.getroot()
                                
                                fileResults = {}
                                for tag in tagsToFind:
                                    if tag in root.attrib:
                                        fileResults[tag] = root.attrib[tag]
                                    else:
                                        element = root.find(f".//{tag}")
                                        fileResults[tag] = element.text if element is not None else "NOT_FOUND"
                                
                                extractedDataMap[fileName] = fileResults
                                
                        except ET.ParseError:
                            print(f"Fehler: {fileName} ist kein gültiges XML.")
                        except Exception as error:
                            print(f"Fehler beim Verarbeiten von {fileName}: {error}")

        except Exception as error:
            print(f"Allgemeiner Fehler beim Zugriff auf ZIP: {error}")

        return extractedDataMap

    def getFileNamesInFolder(
        self,
        pathToZipFile: str,
        folderName: str
    ) -> list[str]:
        """
        @brief Retrieves a list of filenames within a specific folder inside the ZIP.
        @param pathToZipFile The path to the ZIP file.
        @param folderName The folder prefix to search for (e.g. "Bars/").
        @return List of strings representing the filenames (without path prefix).
        """
        fileListResult = []

        pathExists = os.path.exists(pathToZipFile)
        if not pathExists:
            return fileListResult

        try:
            with zipfile.ZipFile(pathToZipFile, 'r') as zipFileHandle:

                unsortedFiles = zipFileHandle.namelist()
                allFilesSorted = sorted(unsortedFiles)

                for fullPathString in allFilesSorted:

                    isInFolder = fullPathString.startswith(folderName)
                    isNotTheFolderItself = fullPathString != folderName

                    if isInFolder and isNotTheFolderItself:

                        cleanFileName = os.path.basename(fullPathString)

                        fileNameIsValid = len(cleanFileName) > 0

                        if fileNameIsValid:
                            fileListResult.append(cleanFileName)

        except Exception as exceptionObject:
            print(f"Error listing files: {exceptionObject}")

        return fileListResult


    def createNewZipWithChanges(
        self,
        originalZipPath: str,
        newZipPath: str,
        editedDataMap: Dict[str, str]
    ) -> bool:
        """
        @brief Creates a new ZIP file by merging original content with edited data.
        @param originalZipPath Path to the source ZIP.
        @param newZipPath Path where the modified ZIP will be saved.
        @param editedDataMap Dictionary of {filename: new_content}.
        @return True if successful, False otherwise.
        """
        try:
            with zipfile.ZipFile(originalZipPath, 'r') as sourceZipHandle:
                with zipfile.ZipFile(newZipPath, 'w') as targetZipHandle:

                    listOfInfoObjects = sourceZipHandle.infolist()

                    for zipInfoObject in listOfInfoObjects:
                        currentFileName = zipInfoObject.filename

                        fileWasEdited = currentFileName in editedDataMap

                        if fileWasEdited:
                            newContentString = editedDataMap[currentFileName]

                            targetZipHandle.writestr(
                                currentFileName,
                                newContentString
                            )
                        else:
                            originalContentBytes = sourceZipHandle.read(
                                currentFileName)

                            targetZipHandle.writestr(
                                zipInfoObject,
                                originalContentBytes
                            )
            return True

        except Exception as exceptionObject:
            print(f"Error saving zip: {exceptionObject}")
            return False


    def createZipWithAddedConfig(
            self,
            originalZipPath: str,
            targetZipPath: str,
            configurationData: Dict[str, Any],
            configFileName: str = "config.json"
    ) -> bool:
        """
        @brief Creates a new ZIP based on the original one and adds a generated config.json to the root.
        @param originalZipPath Path to the source ZIP.
        @param targetZipPath Path where the final ZIP should be saved.
        @param configurationData Dictionary containing the data to be written into config.json.
        @param configFileName The name of the config file inside the ZIP (default: config.json).
        @return True if successful, False otherwise.
        """
        pathExists = os.path.exists(originalZipPath)
        if not pathExists:
            return False

        try:
            jsonContentString = json.dumps(configurationData, indent=4)

            with zipfile.ZipFile(originalZipPath, 'r') as sourceZipHandle:
                with zipfile.ZipFile(targetZipPath, 'w') as targetZipHandle:

                    for item in sourceZipHandle.infolist():
                        originalContent = sourceZipHandle.read(item.filename)
                        targetZipHandle.writestr(item, originalContent)

                    targetZipHandle.writestr(configFileName, jsonContentString)

            return True

        except Exception as exceptionObject:
            print(f"Error creating final zip: {exceptionObject}")
            return False
