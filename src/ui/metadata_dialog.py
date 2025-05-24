import os
import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMenu, QApplication, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class MetadataInvestigationDialog(QDialog):
    """Dialog for investigating comprehensive metadata of a file"""

    def __init__(self, file_path: str, exif_handler, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.exif_handler = exif_handler
        self.all_metadata = []
        self.filtered_metadata = []

        self.init_ui()
        self.load_metadata()

    def init_ui(self):
        self.setWindowTitle(f"Metadata Investigation - {os.path.basename(self.file_path)}")
        self.setModal(True)
        self.resize(900, 700)

        layout = QVBoxLayout()

        # Search section
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by field name or value...")
        self.search_input.textChanged.connect(self.filter_metadata)
        search_layout.addWidget(self.search_input)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_button)

        layout.addLayout(search_layout)

        # Metadata table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Field Name", "Value"])

        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_metadata(self):
        """Load comprehensive metadata from the single file"""
        try:
            # Show loading message
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("Loading..."))
            self.table.setItem(0, 1, QTableWidgetItem(
                f"Extracting comprehensive metadata from {os.path.basename(self.file_path)}..."))
            QApplication.processEvents()

            logger.info(f"Starting comprehensive metadata extraction for single file: {self.file_path}")

            # Get comprehensive metadata for THIS SINGLE FILE ONLY
            metadata_text = self.exif_handler.get_comprehensive_metadata(self.file_path)

            logger.info(f"Comprehensive metadata extraction completed, got {len(metadata_text)} characters")

            # Parse the grouped metadata
            self.parse_metadata(metadata_text)

            # Display all metadata initially
            self.filtered_metadata = self.all_metadata.copy()
            self.update_table()

            logger.info(f"Parsed {len(self.all_metadata)} metadata fields")

        except Exception as e:
            logger.error(f"Error in load_metadata: {str(e)}")
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("Error"))
            self.table.setItem(0, 1, QTableWidgetItem(f"Failed to load metadata: {str(e)}"))

    def parse_metadata(self, metadata_text: str):
        """Parse the grouped metadata text from ExifTool"""
        self.all_metadata = []
        current_group = ""

        lines = metadata_text.strip().split('\n')
        logger.debug(f"Parsing {len(lines)} lines of metadata")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a group header (like "---- EXIF ----")
            if line.startswith('----') and line.endswith('----'):
                current_group = line.strip('-').strip()
                logger.debug(f"Found group: {current_group}")
                continue

            # Parse field: value pairs
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    field_value = parts[1].strip()

                    # Add group prefix if we have one
                    if current_group:
                        display_name = f"{current_group}: {field_name}"
                    else:
                        display_name = field_name

                    self.all_metadata.append({
                        'group': current_group,
                        'field': field_name,
                        'display_name': display_name,
                        'value': field_value,
                        'is_time_field': self.is_time_related_field(field_name.lower())
                    })

        logger.debug(f"Parsed {len(self.all_metadata)} metadata fields")

    def is_time_related_field(self, field_name: str) -> bool:
        """Check if a field is time/date related"""
        time_keywords = [
            'date', 'time', 'create', 'modify', 'timestamp', 'when',
            'year', 'month', 'day', 'hour', 'minute', 'second',
            'gps', 'utc', 'zone', 'offset'
        ]
        return any(keyword in field_name for keyword in time_keywords)

    def update_table(self):
        """Update the table with current filtered metadata"""
        self.table.setRowCount(len(self.filtered_metadata))

        for row, item in enumerate(self.filtered_metadata):
            # Field name
            field_item = QTableWidgetItem(item['display_name'])
            if item['is_time_field']:
                font = field_item.font()
                font.setBold(True)
                field_item.setFont(font)
            self.table.setItem(row, 0, field_item)

            # Field value
            value_item = QTableWidgetItem(item['value'])
            if item['is_time_field']:
                font = value_item.font()
                font.setBold(True)
                value_item.setFont(font)
            self.table.setItem(row, 1, value_item)

    def filter_metadata(self):
        """Filter metadata based on search input"""
        search_text = self.search_input.text().lower()

        if not search_text:
            self.filtered_metadata = self.all_metadata.copy()
        else:
            self.filtered_metadata = []
            for item in self.all_metadata:
                if (search_text in item['display_name'].lower() or
                        search_text in item['value'].lower()):
                    self.filtered_metadata.append(item)

        self.update_table()

    def clear_search(self):
        """Clear the search input"""
        self.search_input.clear()

    def show_context_menu(self, position):
        """Show context menu for copying values"""
        if self.table.itemAt(position) is None:
            return

        row = self.table.itemAt(position).row()
        if row >= len(self.filtered_metadata):
            return

        item = self.filtered_metadata[row]

        menu = QMenu(self)

        copy_field_action = menu.addAction("Copy Field Name")
        copy_value_action = menu.addAction("Copy Value")
        copy_both_action = menu.addAction("Copy Both")

        action = menu.exec_(self.table.mapToGlobal(position))

        clipboard = QApplication.clipboard()

        if action == copy_field_action:
            clipboard.setText(item['display_name'])
        elif action == copy_value_action:
            clipboard.setText(item['value'])
        elif action == copy_both_action:
            clipboard.setText(f"{item['display_name']}: {item['value']}")