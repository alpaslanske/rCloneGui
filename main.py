import sys
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QGridLayout,
    QFileDialog,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)

from PyQt6.QtWidgets import (

    QProgressBar
)

import re
import json
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QSplitter
from PyQt6.QtCore import Qt
from datetime import datetime

RCLONE_OPTIONS = {
    "--progress": True,
    "--onedrive-no-versions": True,
    "--fast-list": False,
    "--dry-run": False,
    "--ignore-existing": False,
    "--delete-empty-src-dirs": False,
    "--checksum": False,
    "--copy-links": False,
    "--create-empty-src-dirs": False,
    "--no-traverse": False,
    "--size-only": False,
    "--ignore-times": False,
    "--update": False,
    "--delete-after": False,
    "--delete-before": False,
    "--delete-during": False,
    "--track-renames": False,
    "--immutable": False,
}

SETTINGS_FILE = "settings.json"

class RcloneWorker(QThread):

    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(str)


    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        self.stopped = False

    def run(self):

        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in self.process.stdout:
                line = line.replace("\r", "\n")

                self.output_signal.emit(line.rstrip())
                self.progress_signal.emit(line.rstrip())

            self.process.wait()

        except Exception as e:
            self.output_signal.emit(f"HATA: {e}")

        self.finished_signal.emit()

    def stop(self):

        self.stopped = True

        if self.process:
            self.process.kill()


class MainWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.worker = None
        self.option_checkboxes = {}
        self.active_transfers = {}

        self.setWindowTitle("Rclone GUI")
        self.resize(1300, 850)

        self.build_ui()
        self.load_remotes()
        self.load_settings()
        self.apply_dark_theme()

    def build_ui(self):

        main_layout = QVBoxLayout()

        #
        # İşlem
        #

        op_layout = QHBoxLayout()

        op_layout.addWidget(QLabel("İşlem"))

        self.operation = QComboBox()
        self.operation.addItems([
            "copy",
            "sync",
            "move"
        ])

        op_layout.addWidget(self.operation)

        main_layout.addLayout(op_layout)

        #
        # Kaynak
        #

        #
        # Kaynak Tipi
        #
        src_type_layout = QHBoxLayout()

        self.local_source = QRadioButton("Yerel Klasör")
        self.remote_source = QRadioButton("Rclone Remote")

        self.local_source.setChecked(True)

        self.source_group = QButtonGroup()
        self.source_group.addButton(self.local_source)
        self.source_group.addButton(self.remote_source)

        src_type_layout.addWidget(self.local_source)
        src_type_layout.addWidget(self.remote_source)

        main_layout.addLayout(src_type_layout)

        self.local_source.toggled.connect(
            self.update_source_mode
        )

        #
        # Yerel Kaynak
        #
        self.local_source_widget = QWidget()

        src_layout = QHBoxLayout()

        src_layout.addWidget(QLabel("Kaynak"))

        self.source = QLineEdit()

        self.source_btn = QPushButton("Klasör Seç")
        self.source_btn.clicked.connect(
            self.select_source_folder
        )

        src_layout.addWidget(self.source)
        src_layout.addWidget(self.source_btn)

        self.local_source_widget.setLayout(src_layout)

        main_layout.addWidget(
            self.local_source_widget
        )

        #
        # Remote Kaynak
        #
        self.remote_source_widget = QWidget()

        remote_src_layout = QHBoxLayout()

        remote_src_layout.addWidget(
            QLabel("Remote")
        )

        self.source_remote_combo = QComboBox()

        remote_src_layout.addWidget(
            self.source_remote_combo
        )

        remote_src_layout.addWidget(
            QLabel("Klasör")
        )

        self.source_remote_path = QLineEdit()

        remote_src_layout.addWidget(
            self.source_remote_path
        )

        self.remote_source_widget.setLayout(
            remote_src_layout
        )

        main_layout.addWidget(
            self.remote_source_widget
        )

        self.remote_source_widget.hide()

        #
        # Hedef tipi
        #

        type_layout = QHBoxLayout()

        self.local_target = QRadioButton(
            "Yerel Klasör"
        )

        self.remote_target = QRadioButton(
            "Rclone Remote"
        )

        self.local_target.setChecked(True)

        self.target_group = QButtonGroup()
        self.target_group.addButton(
            self.local_target
        )
        self.target_group.addButton(
            self.remote_target
        )

        type_layout.addWidget(
            self.local_target
        )

        type_layout.addWidget(
            self.remote_target
        )

        main_layout.addLayout(type_layout)

        self.local_target.toggled.connect(
            self.update_target_mode
        )

        #
        # Yerel hedef
        #

        self.local_widget = QWidget()

        local_layout = QHBoxLayout()

        local_layout.addWidget(
            QLabel("Hedef")
        )

        self.destination = QLineEdit()

        self.destination_btn = QPushButton(
            "Klasör Seç"
        )

        self.destination_btn.clicked.connect(
            self.select_destination_folder
        )

        local_layout.addWidget(
            self.destination
        )

        local_layout.addWidget(
            self.destination_btn
        )

        self.local_widget.setLayout(
            local_layout
        )

        main_layout.addWidget(
            self.local_widget
        )

        #
        # Remote hedef
        #

        self.remote_widget = QWidget()

        remote_layout = QHBoxLayout()

        remote_layout.addWidget(
            QLabel("Remote")
        )

        self.remote_combo = QComboBox()

        remote_layout.addWidget(
            self.remote_combo
        )

        remote_layout.addWidget(
            QLabel("Klasör")
        )

        self.remote_path = QLineEdit()

        remote_layout.addWidget(
            self.remote_path
        )

        self.remote_widget.setLayout(
            remote_layout
        )

        main_layout.addWidget(
            self.remote_widget
        )

        self.remote_widget.hide()

        #
        # Parametre Arama
        #


        #
        # Parametreler
        #

        self.options_group = QGroupBox(
            "Rclone Parametreleri"
        )

        grid = QGridLayout()

        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(0)
        grid.setContentsMargins(2, 2, 2, 2)

        PARAMETER_COLUMNS = 5

        for index, (option, default) in enumerate(
                RCLONE_OPTIONS.items()):

            checkbox = QCheckBox(option)

            checkbox.setChecked(default)

            checkbox.setStyleSheet("""
                QCheckBox {
                    padding: 0px;
                    margin: 0px;
                }
            """)

            self.option_checkboxes[option] = checkbox

            row = index // PARAMETER_COLUMNS
            col = index % PARAMETER_COLUMNS

            grid.addWidget(
                checkbox,
                row,
                col
            )

        self.options_group.setLayout(grid)
        self.options_group.setMaximumHeight(100)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(
            self.options_group
        )

        main_layout.addWidget(scroll, 0)

        #
        # Transfers ve Checkers
        #

        tc_layout = QHBoxLayout()

        tc_layout.addWidget(
            QLabel("Transfers")
        )

        self.transfers = QSpinBox()
        self.transfers.setRange(1, 128)
        self.transfers.setValue(8)

        tc_layout.addWidget(
            self.transfers
        )

        tc_layout.addWidget(
            QLabel("Checkers")
        )

        self.checkers = QSpinBox()
        self.checkers.setRange(1, 128)
        self.checkers.setValue(16)

        tc_layout.addWidget(
            self.checkers
        )

        main_layout.addLayout(tc_layout)
        #
        # Backup Directory
        #
        backup_layout = QHBoxLayout()

        self.backup_enable = QCheckBox(
            "Backup Dir Kullan"
        )
        ### build_ui içine

        backup_layout.addWidget(
            self.backup_enable
        )

        self.backup_dir = QLineEdit()

        backup_layout.addWidget(
            self.backup_dir
        )

        self.backup_btn = QPushButton(
            "Seç"
        )

        self.backup_btn.clicked.connect(
            self.select_backup_folder
        )

        backup_layout.addWidget(
            self.backup_btn
        )

        main_layout.addLayout(
            backup_layout
        )

        #
        # Butonlar
        #

        button_layout = QHBoxLayout()

        self.start_button = QPushButton(
            "Başlat"
        )

        self.stop_button = QPushButton(
            "Durdur"
        )

        button_layout.addWidget(
            self.start_button
        )

        button_layout.addWidget(
            self.stop_button
        )

        main_layout.addLayout(
            button_layout
        )
        #
        #
        # İstatistikler
        #

        #
        # İSTATİSTİKLER
        #

        stats_group = QGroupBox("İstatistikler")

        stats_layout = QVBoxLayout()

        #
        # Toplam işlem
        #

        stats_layout.addWidget(
            QLabel("Toplam İlerleme")
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        stats_layout.addWidget(
            self.progress_bar
        )

        #
        # Hız ve ETA
        #

        info_layout = QHBoxLayout()

        self.speed_label = QLabel(
            "Hız: -"
        )

        self.eta_label = QLabel(
            "ETA: -"
        )

        info_layout.addWidget(
            self.speed_label
        )

        info_layout.addWidget(
            self.eta_label
        )

        stats_layout.addLayout(
            info_layout
        )

        #
        # Aktif dosya
        #


        stats_group.setLayout(
            stats_layout
        )

        main_layout.addWidget(
            stats_group
        )

        #
        # Aktif Transferler
        #

        transfer_group = QGroupBox(
            "Aktif Transferler"
        )

        transfer_layout = QVBoxLayout()

        self.transfer_table = QTableWidget()

        self.transfer_table.setColumnCount(2)

        self.transfer_table.setHorizontalHeaderLabels(
            [
                "Dosya",
                "İlerleme"
            ]
        )

        self.transfer_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )

        self.transfer_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents
        )

        transfer_layout.addWidget(
            self.transfer_table
        )

        transfer_group.setLayout(
            transfer_layout
        )

        #
        # Log
        #

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        #
        # Transfer Tablosu + Log Splitter
        #

        splitter = QSplitter(
            Qt.Orientation.Vertical
        )

        splitter.addWidget(
            transfer_group
        )

        splitter.addWidget(
            self.output
        )

        splitter.setSizes([
            450,
            250
        ])

        main_layout.addWidget(
            splitter
        )
        #print("BUILD OBJECT:", id(self.speed_label))
        #
        # Log
        #

        #self.output = QTextEdit()
        #self.output.setReadOnly(True)

        #main_layout.addWidget(self.output, 1)

        self.setLayout(main_layout)

        self.start_button.clicked.connect(
            self.start_rclone
        )

        self.stop_button.clicked.connect(
            self.stop_rclone
        )
    def update_source_mode(self):

        if self.local_source.isChecked():

            self.local_source_widget.show()
            self.remote_source_widget.hide()

        else:

            self.local_source_widget.hide()
            self.remote_source_widget.show()

    def load_remotes(self):

        try:

            result = subprocess.run(
                ["rclone", "listremotes"],
                capture_output=True,
                text=True
            )

            self.remote_combo.clear()
            self.source_remote_combo.clear()

            for remote in result.stdout.splitlines():

                remote = remote.strip()

                if remote:

                    self.remote_combo.addItem(remote)
                    self.source_remote_combo.addItem(remote)

        except Exception:
            pass

    def update_target_mode(self):

        if self.local_target.isChecked():

            self.local_widget.show()
            self.remote_widget.hide()

        else:

            self.local_widget.hide()
            self.remote_widget.show()

    def select_source_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Kaynak Klasörü Seç"
        )

        if folder:
            self.source.setText(folder)

    def select_destination_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Hedef Klasörü Seç"
        )

        if folder:
            self.destination.setText(folder)

    def build_command(self):

        #
        # Kaynak
        #
        if self.local_source.isChecked():

            source = self.source.text().strip()

        else:

            source = (
                self.source_remote_combo.currentText()
                +
                self.source_remote_path.text().strip()
            )

        #
        # Hedef
        #
        if self.local_target.isChecked():

            destination = (
                self.destination.text().strip()
            )

        else:

            destination = (
                self.remote_combo.currentText()
                +
                self.remote_path.text().strip()
            )

        #
        # Boş kontrolü
        #
        if not source:
            raise ValueError(
                "Kaynak belirtilmedi."
            )

        if not destination:
            raise ValueError(
                "Hedef belirtilmedi."
            )

        #
        # Komut
        #
        cmd = [
            "rclone",
            self.operation.currentText(),
            source,
            destination
        ]

        #
        # Parametreler
        #
        for option, checkbox in (
            self.option_checkboxes.items()
        ):
            if checkbox.isChecked():
                cmd.append(option)

        cmd.append(
            f"--transfers={self.transfers.value()}"
        )

        cmd.append(
            f"--checkers={self.checkers.value()}"
        )

        #
        # Backup Dir
        #
        if (
            self.operation.currentText() == "sync"
            and
            self.backup_enable.isChecked()
            and
            self.remote_target.isChecked()
        ):

            remote_name = (
                self.remote_combo.currentText()
            )

            if remote_name:

                backup_dir = (
                    remote_name
                    +
                    "Backup/"
                    +
                    datetime.now().strftime(
                        "%Y-%m-%d_%H-%M-%S"
                    )
                )

                cmd.append(
                    f"--backup-dir={backup_dir}"
                )

        cmd.append("--stats=1s")

        return cmd

    def select_backup_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Backup Klasörü Seç"
        )

        if folder:
            self.backup_dir.setText(folder)

    def refresh_transfer_table(self):

        self.transfer_table.setRowCount(
            len(self.active_transfers)
        )

        for row, (
            filename,
            percent
        ) in enumerate(
            self.active_transfers.items()
        ):

            self.transfer_table.setItem(
                row,
                0,
                QTableWidgetItem(
                    filename
                )
            )

            self.transfer_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    f"{percent}%"
                )
            )

    def start_rclone(self):

        try:
            cmd = self.build_command()

        except Exception as e:

            self.output.append(
                f"HATA: {e}"
            )

            return

        self.output.clear()

        self.output.append(
            "Çalıştırılan Komut:"
        )

        self.output.append(
            " ".join(cmd)
        )

        self.output.append(
            "\n--------------------------------\n"
        )

        self.worker = RcloneWorker(cmd)

        self.worker.output_signal.connect(
            self.append_log
        )

        self.worker.finished_signal.connect(
            self.on_finished
        )

        self.worker.progress_signal.connect(
            self.process_progress
        )

        self.worker.start()
        self.progress_bar.setValue(0)


    def append_log(self, line):
        clean = line.strip()

        if clean.startswith("Transferred:"):
            return

        if clean.startswith("Checks:"):
            return

        if clean.startswith("Elapsed time:"):
            return

        if clean.startswith("Transferring:"):
            return

        if clean.startswith("*"):
            return

        self.output.append(line)



    def on_finished(self):

        if self.worker and self.worker.stopped:

            self.output.append(
                "\nİşlem kullanıcı tarafından durduruldu."
            )

            return

        self.progress_bar.setValue(100)
        self.active_transfers.clear()
        self.refresh_transfer_table()


        self.speed_label.setText(
            "Hız: Tamamlandı"
        )

        self.eta_label.setText(
            "ETA: 0s"
        )

        self.output.append(
            "\nİşlem tamamlandı."
        )


    def stop_rclone(self):

        if self.worker:

            self.worker.stop()


    def apply_dark_theme(self):

        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                margin-top: 2px;
                padding-top: 2px;
                padding-bottom: 2px;
            }
        """)

    def process_progress(self, line):

        try:

            #
            # TOPLAM PROGRESS
            #

            if "Transferred:" in line:

                percentages = re.findall(
                    r"(\d+)%",
                    line
                )

                if percentages:

                    self.progress_bar.setValue(
                        int(percentages[-1])
                    )

            #
            # HIZ
            #

            speeds = re.findall(
                r"([0-9.]+\s+(?:B|KiB|MiB|GiB|TiB)/s)",
                line
            )

            if speeds:

                speed = speeds[-1]

                self.speed_label.setText(
                    f"Hız: {speed}"
                )

                QApplication.processEvents()

            #
            # ETA
            #

            eta_matches = re.findall(
                r"ETA\s+([^\s]+)",
                line
            )

            if eta_matches:

                eta = eta_matches[-1]

                self.eta_label.setText(
                    f"ETA: {eta}"
                )

                QApplication.processEvents()

            #
            # AKTİF DOSYA
            #

            file_match = re.search(
                r"\s*\*\s+(.*?):\s*(\d+)%",
                line
            )

            if file_match:

                filename = file_match.group(1).strip()

                file_percent = int(
                    file_match.group(2)
                )

                self.active_transfers[
                    filename
                ] = file_percent

                self.refresh_transfer_table()

                QApplication.processEvents()

        except Exception as e:

            print(
                "PARSER HATASI:",
                e
            )


    def save_settings(self):

        data = {

            "operation":
            self.operation.currentText(),

            "source":
            self.source.text(),

            "local_target":
            self.local_target.isChecked(),

            "destination":
            self.destination.text(),

            "remote":
            self.remote_combo.currentText(),

            "remote_path":
            self.remote_path.text(),

            "transfers":
            self.transfers.value(),

            "checkers":
            self.checkers.value(),

            "local_source":
                self.local_source.isChecked(),

            "source_remote":
                self.source_remote_combo.currentText(),

            "source_remote_path":
                self.source_remote_path.text(),

            "backup_enabled":
                self.backup_enable.isChecked(),

            "backup_dir":
                self.backup_dir.text(),

            "options": {
                name: checkbox.isChecked()
                for name, checkbox
                in self.option_checkboxes.items()
            }
        }

        with open(
            SETTINGS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def load_settings(self):

        if not os.path.exists(
            SETTINGS_FILE
        ):
            return

        try:

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.operation.setCurrentText(
                data.get(
                    "operation",
                    "copy"
                )
            )

            self.source.setText(
                data.get(
                    "source",
                    ""
                )
            )

            self.destination.setText(
                data.get(
                    "destination",
                    ""
                )
            )

            self.remote_path.setText(
                data.get(
                    "remote_path",
                    ""
                )
            )

            self.transfers.setValue(
                data.get(
                    "transfers",
                    8
                )
            )

            self.checkers.setValue(
                data.get(
                    "checkers",
                    16
                )
            )
###
            if data.get(
                "local_source",
                True
            ):
                self.local_source.setChecked(True)
            else:
                self.remote_source.setChecked(True)
###
            source_remote = data.get(
                "source_remote",
                ""
            )

            index = self.source_remote_combo.findText(
                source_remote
            )

            if index >= 0:
                self.source_remote_combo.setCurrentIndex(
                    index
                )
###
            self.source_remote_path.setText(
                data.get(
                    "source_remote_path",
                    ""
                )
            )
###
            self.backup_enable.setChecked(
                data.get(
                    "backup_enabled",
                    False
                )
            )

            self.backup_dir.setText(
                data.get(
                    "backup_dir",
                    ""
                )
            )
###
            if data.get(
                "local_target",
                True
            ):
                self.local_target.setChecked(
                    True
                )
            else:
                self.remote_target.setChecked(
                    True
                )

            remote_name = data.get(
                "remote",
                ""
            )

            index = self.remote_combo.findText(
                remote_name
            )

            if index >= 0:
                self.remote_combo.setCurrentIndex(
                    index
                )

            options = data.get(
                "options",
                {}
            )

            for option, state in options.items():

                if option in self.option_checkboxes:

                    self.option_checkboxes[
                        option
                    ].setChecked(state)

        except Exception as e:

            print(
                f"Ayar yükleme hatası: {e}"
            )

    def closeEvent(self, event):

        self.save_settings()

        super().closeEvent(event)

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
