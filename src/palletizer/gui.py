"""PyQt5 GUI for the palletization application."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from src.palletizer.exceptions import ValidationError
from src.palletizer.io import load_problem_from_json, save_problem_to_json
from src.palletizer.logging_utils import configure_logger
from src.palletizer.models import BinConfig, ItemType, Placement, SolveResult, UnplacedItem
from src.palletizer.solver import solve_palletization
from src.palletizer.validation import validate_inputs


class QtLogHandler(logging.Handler):
    """Logging handler that forwards messages to a QTextEdit widget."""

    def __init__(self, widget: QtWidgets.QPlainTextEdit) -> None:
        super().__init__()
        self.widget = widget
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        self.widget.appendPlainText(self.format(record))


class GraphicsView(QtWidgets.QGraphicsView):
    """Graphics view with wheel zoom support."""

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("2D Palletization Benchmark App")
        self.resize(1400, 900)

        self.logger = configure_logger()
        self.result: SolveResult | None = None

        self._build_ui()
        self._connect_signals()
        self._configure_logging()
        self._load_demo_data()
        self.update_controls()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root_layout = QtWidgets.QHBoxLayout(central)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root_layout.addWidget(splitter)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        splitter.addWidget(left_panel)

        form_group = QtWidgets.QGroupBox("Input Parameters")
        form_layout = QtWidgets.QFormLayout(form_group)
        self.bin_width_spin = self._create_dimension_spinbox()
        self.bin_height_spin = self._create_dimension_spinbox()
        self.gap_spin = self._create_dimension_spinbox()
        form_layout.addRow("Pallet Width [mm]", self.bin_width_spin)
        form_layout.addRow("Pallet Height [mm]", self.bin_height_spin)
        form_layout.addRow("Gap g [mm]", self.gap_spin)
        left_layout.addWidget(form_group)

        items_group = QtWidgets.QGroupBox("Item Types")
        items_layout = QtWidgets.QVBoxLayout(items_group)
        self.items_table = QtWidgets.QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["Name", "Width [mm]", "Height [mm]", "Quantity", "Rotate 90°"])
        self.items_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        items_layout.addWidget(self.items_table)

        item_button_row = QtWidgets.QHBoxLayout()
        self.add_item_button = QtWidgets.QPushButton("Add Item")
        self.remove_item_button = QtWidgets.QPushButton("Remove Item")
        item_button_row.addWidget(self.add_item_button)
        item_button_row.addWidget(self.remove_item_button)
        items_layout.addLayout(item_button_row)
        left_layout.addWidget(items_group, stretch=1)

        io_row = QtWidgets.QHBoxLayout()
        self.load_json_button = QtWidgets.QPushButton("Load JSON")
        self.save_config_button = QtWidgets.QPushButton("Save JSON")
        io_row.addWidget(self.load_json_button)
        io_row.addWidget(self.save_config_button)
        left_layout.addLayout(io_row)

        controls_group = QtWidgets.QGroupBox("Controls")
        controls_layout = QtWidgets.QHBoxLayout(controls_group)
        self.run_button = QtWidgets.QPushButton("Run / Start")
        self.reset_button = QtWidgets.QPushButton("Reset Scene")
        self.clear_logger_button = QtWidgets.QPushButton("Clear Logger")
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.reset_button)
        controls_layout.addWidget(self.clear_logger_button)
        left_layout.addWidget(controls_group)

        metrics_group = QtWidgets.QGroupBox("Metrics")
        metrics_layout = QtWidgets.QFormLayout(metrics_group)
        self.placed_label = QtWidgets.QLabel("0")
        self.unplaced_label = QtWidgets.QLabel("0")
        self.utilization_label = QtWidgets.QLabel("0.00 %")
        self.time_label = QtWidgets.QLabel("0.00 ms")
        self.unplaced_summary = QtWidgets.QPlainTextEdit()
        self.unplaced_summary.setReadOnly(True)
        self.unplaced_summary.setMaximumHeight(120)
        metrics_layout.addRow("Placed items", self.placed_label)
        metrics_layout.addRow("Unplaced items", self.unplaced_label)
        metrics_layout.addRow("Utilization", self.utilization_label)
        metrics_layout.addRow("Compute time", self.time_label)
        metrics_layout.addRow("Unplaced detail", self.unplaced_summary)
        left_layout.addWidget(metrics_group)

        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(right_splitter)

        canvas_group = QtWidgets.QGroupBox("Visualization")
        canvas_layout = QtWidgets.QVBoxLayout(canvas_group)
        self.scene = QtWidgets.QGraphicsScene(self)
        self.graphics_view = GraphicsView()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.graphics_view.setBackgroundBrush(QtGui.QColor("#f4f6f8"))
        canvas_layout.addWidget(self.graphics_view)
        right_splitter.addWidget(canvas_group)

        logger_group = QtWidgets.QGroupBox("System Logger")
        logger_layout = QtWidgets.QVBoxLayout(logger_group)
        self.logger_text = QtWidgets.QPlainTextEdit()
        self.logger_text.setReadOnly(True)
        logger_layout.addWidget(self.logger_text)
        right_splitter.addWidget(logger_group)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)

    def _connect_signals(self) -> None:
        self.add_item_button.clicked.connect(self.add_item_row)
        self.remove_item_button.clicked.connect(self.remove_selected_item)
        self.run_button.clicked.connect(self.run_solver)
        self.reset_button.clicked.connect(self.reset_scene)
        self.clear_logger_button.clicked.connect(self.logger_text.clear)
        self.load_json_button.clicked.connect(self.load_json)
        self.save_config_button.clicked.connect(self.save_configuration)
        self.items_table.itemChanged.connect(self.update_controls)
        for spinbox in (self.bin_width_spin, self.bin_height_spin, self.gap_spin):
            spinbox.valueChanged.connect(self.update_controls)

    def _configure_logging(self) -> None:
        self.log_handler = QtLogHandler(self.logger_text)
        if not any(isinstance(handler, QtLogHandler) for handler in self.logger.handlers):
            self.logger.addHandler(self.log_handler)

    def _create_dimension_spinbox(self) -> QtWidgets.QDoubleSpinBox:
        spinbox = QtWidgets.QDoubleSpinBox()
        spinbox.setDecimals(2)
        spinbox.setRange(0.0, 1_000_000.0)
        spinbox.setSingleStep(10.0)
        return spinbox

    def _create_integer_spinbox(self) -> QtWidgets.QSpinBox:
        spinbox = QtWidgets.QSpinBox()
        spinbox.setRange(0, 1_000_000)
        return spinbox

    def _load_demo_data(self) -> None:
        self.bin_width_spin.setValue(1200)
        self.bin_height_spin.setValue(800)
        self.gap_spin.setValue(20)
        for row in [
            ("Box A", 300, 200, 4, True),
            ("Box B", 250, 180, 5, True),
            ("Box C", 180, 120, 6, False),
        ]:
            self.add_item_row(*row)

    def add_item_row(
        self,
        name: str = "",
        width: float = 100.0,
        height: float = 100.0,
        quantity: int = 1,
        can_rotate: bool = False,
    ) -> None:
        self.items_table.blockSignals(True)
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        name_item = QtWidgets.QTableWidgetItem(name or f"Item {row + 1}")
        self.items_table.setItem(row, 0, name_item)

        width_spin = self._create_dimension_spinbox()
        width_spin.setValue(width)
        width_spin.valueChanged.connect(self.update_controls)
        self.items_table.setCellWidget(row, 1, width_spin)

        height_spin = self._create_dimension_spinbox()
        height_spin.setValue(height)
        height_spin.valueChanged.connect(self.update_controls)
        self.items_table.setCellWidget(row, 2, height_spin)

        quantity_spin = self._create_integer_spinbox()
        quantity_spin.setValue(quantity)
        quantity_spin.valueChanged.connect(self.update_controls)
        self.items_table.setCellWidget(row, 3, quantity_spin)

        rotate_checkbox = QtWidgets.QCheckBox()
        rotate_checkbox.setChecked(can_rotate)
        rotate_checkbox.stateChanged.connect(self.update_controls)
        rotate_container = QtWidgets.QWidget()
        rotate_layout = QtWidgets.QHBoxLayout(rotate_container)
        rotate_layout.setContentsMargins(0, 0, 0, 0)
        rotate_layout.setAlignment(QtCore.Qt.AlignCenter)
        rotate_layout.addWidget(rotate_checkbox)
        self.items_table.setCellWidget(row, 4, rotate_container)
        self.items_table.blockSignals(False)

        self.update_controls()

    def remove_selected_item(self) -> None:
        selected_rows = sorted({index.row() for index in self.items_table.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            self.items_table.removeRow(row)
        self.update_controls()

    def _read_items(self) -> list[ItemType]:
        items: list[ItemType] = []
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 0)
            width_spin = self.items_table.cellWidget(row, 1)
            height_spin = self.items_table.cellWidget(row, 2)
            quantity_spin = self.items_table.cellWidget(row, 3)
            rotate_container = self.items_table.cellWidget(row, 4)
            if not all((name_item, width_spin, height_spin, quantity_spin, rotate_container)):
                continue
            rotate_checkbox = rotate_container.layout().itemAt(0).widget()

            items.append(
                ItemType(
                    name=name_item.text().strip() if name_item else f"Item {row + 1}",
                    width=float(width_spin.value()),
                    height=float(height_spin.value()),
                    quantity=int(quantity_spin.value()),
                    can_rotate=bool(rotate_checkbox.isChecked()),
                )
            )
        return items

    def _read_bin(self) -> BinConfig:
        return BinConfig(
            width=float(self.bin_width_spin.value()),
            height=float(self.bin_height_spin.value()),
            gap=float(self.gap_spin.value()),
        )

    def update_controls(self) -> None:
        self.run_button.setEnabled(True)
        try:
            validate_inputs(self._read_bin(), self._read_items())
        except ValidationError as exc:
            self.statusBar().showMessage(f"Invalid input: {exc}")
            return
        except Exception as exc:
            self.statusBar().showMessage(f"Input parsing error: {exc}")
            return

        self.statusBar().showMessage("Inputs are valid.")

    def run_solver(self) -> None:
        try:
            bin_config = self._read_bin()
            items = self._read_items()
            validate_inputs(bin_config, items)
            self.logger.info("Starting palletization with %s item types.", len(items))
            result = solve_palletization(bin_config, items)
            self.result = result
            self._render_result(result)
            self._update_metrics(result)

            metrics = result.metrics
            assert metrics is not None
            if metrics.unplaced_count:
                self.logger.warning("Partial solution: %s items could not be placed.", metrics.unplaced_count)
            self.logger.info(
                "Finished: placed=%s, unplaced=%s, utilization=%.2f%%, time=%.2f ms",
                metrics.placed_count,
                metrics.unplaced_count,
                metrics.utilization_ratio * 100.0,
                metrics.computation_time_ms,
            )
        except ValidationError as exc:
            self.logger.error("Cannot start palletization: %s", exc)
            QtWidgets.QMessageBox.warning(self, "Invalid Input", str(exc))
        except Exception as exc:
            self.logger.exception("Unexpected error during solve: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Application Error", str(exc))

        self.update_controls()

    def _render_result(self, result: SolveResult) -> None:
        self.scene.clear()
        bin_rect = QtCore.QRectF(0, 0, result.bin_config.width, result.bin_config.height)
        self.scene.addRect(bin_rect, QtGui.QPen(QtGui.QColor("#203040"), 2), QtGui.QBrush(QtGui.QColor("#ffffff")))

        for placement in result.placements:
            self._add_placement_item(placement)

        self._render_unplaced_items(result.bin_config, result.unplaced_items, self._read_items())
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20, -20, 20, 20))
        self.graphics_view.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def _render_unplaced_items(
        self,
        bin_config: BinConfig,
        unplaced_items: list[UnplacedItem],
        items: list[ItemType],
    ) -> None:
        if not unplaced_items:
            return

        start_x = bin_config.width + 60
        current_y = 0.0
        title = self.scene.addText("Unplaced items", QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
        title.setPos(start_x, current_y)
        current_y += 30

        for unplaced in unplaced_items:
            item = items[unplaced.item_index]
            preview_width = max(40.0, min(item.width, 180.0))
            preview_height = max(30.0, min(item.height, 120.0))
            rect = QtCore.QRectF(start_x, current_y, preview_width, preview_height)
            pen = QtGui.QPen(QtGui.QColor("#c23b22"), 1.5, QtCore.Qt.DashLine)
            brush = QtGui.QBrush(QtGui.QColor(255, 220, 220))
            self.scene.addRect(rect, pen, brush)
            label = self.scene.addText(
                f"{unplaced.item_name}\nqty: {unplaced.quantity}\n{item.width:.0f} x {item.height:.0f}",
                QtGui.QFont("Segoe UI", 8),
            )
            label.setDefaultTextColor(QtGui.QColor("#7a1f12"))
            label.setPos(start_x + 5, current_y + 5)
            current_y += preview_height + 24

    def _add_placement_item(self, placement: Placement) -> None:
        hue = (placement.item_index * 67) % 360
        color = QtGui.QColor.fromHsv(hue, 180, 220)
        rect = QtCore.QRectF(placement.x, placement.y, placement.width, placement.height)
        self.scene.addRect(rect, QtGui.QPen(QtGui.QColor("#243447"), 1.2), QtGui.QBrush(color))

        orientation = "R" if placement.rotated else "N"
        label = f"{placement.item_name} #{placement.instance_id}\n{placement.width:.0f} x {placement.height:.0f} [{orientation}]"
        text_item = self.scene.addText(label, QtGui.QFont("Segoe UI", 8))
        text_item.setDefaultTextColor(QtGui.QColor("#102030"))
        text_item.setPos(placement.x + 4, placement.y + 4)

    def _update_metrics(self, result: SolveResult) -> None:
        assert result.metrics is not None
        self.placed_label.setText(str(result.metrics.placed_count))
        self.unplaced_label.setText(str(result.metrics.unplaced_count))
        self.utilization_label.setText(f"{result.metrics.utilization_ratio * 100.0:.2f} %")
        self.time_label.setText(f"{result.metrics.computation_time_ms:.2f} ms")
        if result.unplaced_items:
            self.unplaced_summary.setPlainText(
                "\n".join(f"{item.item_name}: {item.quantity}" for item in result.unplaced_items)
            )
        else:
            self.unplaced_summary.setPlainText("All requested items were placed.")

    def reset_scene(self) -> None:
        self.scene.clear()
        self.result = None
        self.placed_label.setText("0")
        self.unplaced_label.setText("0")
        self.utilization_label.setText("0.00 %")
        self.time_label.setText("0.00 ms")
        self.unplaced_summary.clear()
        self.logger.info("Scene reset.")

    def load_json(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load JSON",
            str(Path.cwd()),
            "JSON files (*.json)",
        )
        if not path:
            return

        try:
            bin_config, items = load_problem_from_json(path)
            self.bin_width_spin.setValue(bin_config.width)
            self.bin_height_spin.setValue(bin_config.height)
            self.gap_spin.setValue(bin_config.gap)
            self.items_table.setRowCount(0)
            for item in items:
                self.add_item_row(item.name, item.width, item.height, item.quantity, item.can_rotate)
            self.logger.info("Loaded input data from %s", path)
        except Exception as exc:
            self.logger.exception("Failed to load JSON: %s", exc)
            QtWidgets.QMessageBox.critical(self, "JSON Load Error", str(exc))

        self.update_controls()

    def save_configuration(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save JSON Configuration",
            str(Path.cwd() / "config.json"),
            "JSON files (*.json)",
        )
        if not path:
            return

        try:
            save_problem_to_json(path, self._read_bin(), self._read_items())
            self.logger.info("Saved configuration to %s", path)
        except Exception as exc:
            self.logger.exception("Failed to save configuration: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Save Error", str(exc))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.logger.info("Application closed.")
        super().closeEvent(event)


def create_application() -> QtWidgets.QApplication:
    """Create and configure the Qt application instance."""

    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    application.setApplicationName("2D Palletization Benchmark")
    application.setStyle("Fusion")
    return application
