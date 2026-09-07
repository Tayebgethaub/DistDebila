import sys, math, json, os
from collections import deque
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenu, QPushButton, QDialog, QLabel, QLineEdit, QComboBox,
    QDialogButtonBox, QMessageBox, QInputDialog
)

# ============================================================================
# 1. المحرك (NetworkEngine)
# ============================================================================
class NetworkEngine:
    def __init__(self):
        self.posts = {}
        self.wires = []
        self.junction_points = []

    def add_post(self, pid, post):
        self.posts[pid] = post

    def update_power_flow(self):
        self._reset_power_state()
        sources = self._collect_power_sources()
        if sources:
            self._propagate_power(sources)

    def _reset_power_state(self):
        for wire in self.wires:
            wire.is_powered = False
            wire.powered_color = None
        for post in self.posts.values():
            if isinstance(post, dict):
                post["is_powered"] = False
                post["powered_color"] = None
            elif hasattr(post, 'cells'):
                post.is_powered = False
                post.powered_color = None
                for cell in post.cells:
                    cell.is_powered = False
                    cell.powered_color = None
        for jp in self.junction_points:
            jp.is_powered = False
            jp.powered_color = None

    def _collect_power_sources(self):
        sources = {}
        for pid, post in self.posts.items():
            if hasattr(post, 'shape') and post.shape == "source":
                for pt in post.connection_points:
                    sources[pt["id"]] = pt["color"]
        return sources

    def _propagate_power(self, sources):
        queue = deque([(pt_id, color) for pt_id, color in sources.items()])
        visited = set()
        max_iter = 5000
        count = 0
        wire_map = self._build_wire_map()
        while queue and count < max_iter:
            count += 1
            point_id, color = queue.popleft()
            if point_id in visited:
                continue
            visited.add(point_id)
            for jp in self.junction_points:
                if jp.id == point_id:
                    jp.is_powered = True
                    jp.powered_color = color
                    break
            for wire in wire_map.get(point_id, []):
                if wire.is_powered:
                    continue
                other = wire.end_post_id if wire.start_pt_id == point_id else wire.start_pt_id
                wire.is_powered = True
                wire.powered_color = color
                self._activate_point(other, color, queue, wire_map)
                if other not in visited:
                    queue.append((other, color))

    def _activate_point(self, point_id, color, queue, wire_map):
        for pid, post in self.posts.items():
            if not point_id.startswith(pid):
                continue
            if isinstance(post, dict):
                post["is_powered"] = True
                post["powered_color"] = color
                if post["shape"] == "breaker" and post.get("closed", False):
                    if point_id.endswith("_L"):
                        other = f"{pid}_R"
                    else:
                        other = f"{pid}_L"
                    queue.append((other, color))
                break
            elif hasattr(post, 'cells'):
                for idx, cell in enumerate(post.cells):
                    if point_id == f"{pid}_T{idx}":
                        if cell.closed:
                            cell.is_powered = True
                            cell.powered_color = color
                            post.is_powered = True
                            post.powered_color = color
                            for other_idx, other_cell in enumerate(post.cells):
                                if other_idx != idx and other_cell.closed:
                                    other_cell.is_powered = True
                                    other_cell.powered_color = color
                                    other_pt = f"{pid}_T{other_idx}"
                                    queue.append((other_pt, color))
                        else:
                            cell.is_powered = False
                            cell.powered_color = None
                        break
                break

    def toggle_cell(self, pid, idx):
        post = self.posts.get(pid)
        if not post or not hasattr(post, 'cells'):
            return False, "الخلية غير موجودة"
        if idx < 0 or idx >= len(post.cells):
            return False, "رقم الخلية غير صحيح"
        cell = post.cells[idx]
        if not cell.closed:
            cell.closed = True
            has_short, details = self._check_for_short()
            if has_short:
                cell.closed = False
                return False, f"لا يمكن إغلاق الخلية: {details}"
            self.update_power_flow()
            return True, "تم إغلاق الخلية"
        else:
            cell.closed = False
            self.update_power_flow()
            return True, "تم فتح الخلية"

    def toggle_breaker(self, pid):
        post = self.posts.get(pid)
        if not post or not isinstance(post, dict) or post.get("shape") != "breaker":
            return False, "العنصر ليس قاطعاً"
        if not post.get("closed", False):
            post["closed"] = True
            has_short, details = self._check_for_short()
            if has_short:
                post["closed"] = False
                return False, f"لا يمكن إغلاق القاطع: {details}"
            self.update_power_flow()
            return True, "تم إغلاق القاطع"
        else:
            post["closed"] = False
            self.update_power_flow()
            return True, "تم فتح القاطع"

    def _check_for_short(self):
        self._cleanup_junctions()
        wire_map = self._build_wire_map()
        post_bus_map = self._build_post_bus_map()
        breaker_map = self._build_breaker_map()
        source_points = {}
        for pid, post in self.posts.items():
            if hasattr(post, 'shape') and post.shape == "source":
                for pt in post.connection_points:
                    source_points[pt["id"]] = pt["color"]
        source_colors = set(source_points.values())
        if len(source_colors) <= 1:
            return False, "مصدر واحد فقط"
        visited_global = set()
        for start_pt, start_color in source_points.items():
            if start_pt in visited_global:
                continue
            visited = set()
            queue = deque([start_pt])
            while queue:
                current_pt = queue.popleft()
                if current_pt in visited:
                    continue
                visited.add(current_pt)
                visited_global.add(current_pt)
                if current_pt in source_points and current_pt != start_pt:
                    other_color = source_points[current_pt]
                    if other_color != start_color:
                        return True, f"مصدر {start_color} متصل بمصدر {other_color}"
                if current_pt in post_bus_map:
                    pid = post_bus_map[current_pt]
                    post = self.posts.get(pid)
                    if hasattr(post, 'cells'):
                        for other_idx, other_cell in enumerate(post.cells):
                            other_pt = f"{pid}_T{other_idx}"
                            if other_pt != current_pt and other_cell.closed:
                                if other_pt not in visited:
                                    queue.append(other_pt)
                if current_pt in breaker_map:
                    other_pt = breaker_map[current_pt]
                    if other_pt not in visited:
                        queue.append(other_pt)
                for wire in wire_map.get(current_pt, []):
                    next_pt = wire.end_post_id if wire.start_pt_id == current_pt else wire.start_pt_id
                    if next_pt not in visited:
                        queue.append(next_pt)
        return False, ""

    def _build_wire_map(self):
        wire_map = {}
        for wire in self.wires:
            wire_map.setdefault(wire.start_pt_id, []).append(wire)
            wire_map.setdefault(wire.end_post_id, []).append(wire)
        return wire_map

    def _build_post_bus_map(self):
        post_bus_map = {}
        for pid, post in self.posts.items():
            if hasattr(post, 'cells'):
                for idx in range(len(post.cells)):
                    post_bus_map[f"{pid}_T{idx}"] = pid
        return post_bus_map

    def _build_breaker_map(self):
        breaker_map = {}
        for pid, post in self.posts.items():
            if isinstance(post, dict) and post.get("shape") == "breaker" and post.get("closed", False):
                breaker_map[f"{pid}_L"] = f"{pid}_R"
                breaker_map[f"{pid}_R"] = f"{pid}_L"
        return breaker_map

    def _cleanup_junctions(self):
        active_wire_ids = {w.id for w in self.wires}
        self.junction_points = [jp for jp in self.junction_points if jp.wire_id in active_wire_ids]

# ============================================================================
# 2. عناصر الشبكة الأساسية (مصدر، بوست، قاطع، خلايا)
# ============================================================================
class MainSourceElement:
    def __init__(self, name, x, y):
        self.name = name; self.x = x; self.y = y; self.shape = "source"; self.angle = 0; self.connection_points = []
    def generate_points(self, r):
        br = r * 4
        raw_pts = []
        for i in range(-br, br + 1, r * 2):
            raw_pts.extend([(self.x + i, self.y - br), (self.x + i, self.y + br), (self.x - br, self.y + i), (self.x + br, self.y + i)])
        unique_pts = list(set(raw_pts))
        filtered_pts = [(px, py) for px, py in unique_pts if not (abs(px - self.x) == br and abs(py - self.y) == br)]
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#34495e", "#27ae60", "#2980b9", "#8e44ad", "#f39c12"]
        self.connection_points = [{"id": f"pt_{idx}", "x": px, "y": py, "color": colors[idx % len(colors)]} for idx, (px, py) in enumerate(filtered_pts)]
    def draw(self, painter, r):
        br = r * 4
        self.generate_points(r)
        painter.setPen(QPen(QColor("#000000"), 3)); painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawRect(self.x - br, self.y - br, br * 2, br * 2)
        painter.setPen(QPen(QColor("#000000"), 4))
        painter.drawEllipse(QPointF(self.x - 30, self.y), 45, 45)
        painter.drawEllipse(QPointF(self.x + 30, self.y), 45, 45)
        painter.setPen(Qt.PenStyle.NoPen)
        for pt in self.connection_points:
            painter.setBrush(QBrush(QColor(pt["color"])))
            painter.drawEllipse(QPointF(pt["x"], pt["y"]), 5, 5)
        painter.setPen(QPen(QColor("#000000"), 2.5))
        painter.drawText(self.x - 50, self.y + 75, 100, 30, Qt.AlignmentFlag.AlignCenter, self.name)

class JunctionPoint:
    _id_counter = 0
    def __init__(self, wire_id, pos_ratio=0.5):
        self.id = f"j_{JunctionPoint._id_counter}"; JunctionPoint._id_counter += 1
        self.wire_id = wire_id; self.pos_ratio = pos_ratio; self.is_powered = False; self.powered_color = None; self.x = 0.0; self.y = 0.0
    def update_position(self, wires):
        wire = next((w for w in wires if w.id == self.wire_id), None)
        if wire:
            self.x = wire.start_x + (wire.end_x - wire.start_x) * self.pos_ratio
            self.y = wire.start_y + (wire.end_y - wire.start_y) * self.pos_ratio
    def get_connection_point(self):
        return {"id": self.id, "x": self.x, "y": self.y, "color": self.powered_color if self.is_powered else "#000000", "type": "junction"}

class WireElement:
    _id_counter = 0
    def __init__(self, start_pt_id, start_x, start_y, end_post_id, end_x, end_y, color="#000000", name="Cable", wire_type="straight"):
        self.id = f"w_{WireElement._id_counter}"
        WireElement._id_counter += 1
        self.start_pt_id = start_pt_id
        self.start_x = start_x
        self.start_y = start_y
        self.end_post_id = end_post_id
        self.end_x = end_x
        self.end_y = end_y
        self.color = color
        self.name = name
        self.wire_type = wire_type  # "straight" أو "bent" (يعني متقطع)
        self.is_powered = False
        self.powered_color = None

    def draw(self, painter):
        wire_color = QColor(self.powered_color) if (self.is_powered and self.powered_color) else QColor(self.color)
        if self.wire_type == "straight":
            painter.setPen(QPen(wire_color, 4 if self.is_powered else 3, Qt.PenStyle.SolidLine))
        else:  # "bent" = متقطع
            painter.setPen(QPen(wire_color, 4 if self.is_powered else 3, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(self.start_x, self.start_y), QPointF(self.end_x, self.end_y))

        # اسم السلك في المنتصف
        mid_x = (self.start_x + self.end_x) / 2
        mid_y = (self.start_y + self.end_y) / 2
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.drawText(mid_x - 20, mid_y - 12, self.name)

        # نقاط التوصيل
        painter.setBrush(QBrush(QColor("#e74c3c")))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawEllipse(QPointF(self.start_x, self.start_y), 5, 5)
        painter.drawEllipse(QPointF(self.end_x, self.end_y), 5, 5)

class Cell:
    def __init__(self, name="Cell", x_offset=0, y_offset=0):
        self.name = name; self.closed = True; self.is_powered = False; self.powered_color = None; self.x_offset = x_offset; self.y_offset = y_offset
    def toggle(self):
        self.closed = not self.closed

class SquarePost:
    def __init__(self, name, x, y, filled_type, cells_count, cell_names):
        self.name = name; self.x = x; self.y = y; self.shape = "square"; self.filled_type = filled_type; self.angle = 0
        self.is_powered = False; self.powered_color = None; self.cells = []
        offsets = [(0, -30)] if cells_count == 1 else [(-30, 0), (30, 0)] if cells_count == 2 else [(0, -30), (-30, 0), (30, 0)]
        for i, (dx, dy) in enumerate(offsets):
            name_cell = cell_names[i] if i < len(cell_names) else f"Cell_{i+1}"
            self.cells.append(Cell(name_cell, dx, dy))
    def get_connection_points(self, pid):
        pts = []; rad = math.radians(self.angle)
        def rot(px, py):
            return QPointF((px - self.x)*math.cos(rad) - (py - self.y)*math.sin(rad) + self.x,
                           (px - self.x)*math.sin(rad) + (py - self.y)*math.cos(rad) + self.y)
        for idx, cell in enumerate(self.cells):
            pt = rot(self.x + cell.x_offset, self.y + cell.y_offset)
            pts.append({"pid": pid, "type": "post", "pt_id": f"{pid}_T{idx}", "x": pt.x(), "y": pt.y(), "color": "#000000", "cell_index": idx})
        return pts
    def toggle_cell(self, index):
        if 0 <= index < len(self.cells):
            self.cells[index].toggle()

# ============================================================================
# 3. حوار إعدادات العنصر الجديد
# ============================================================================
class PostSettingsDialog(QDialog):
    def __init__(self, shape, filled_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إعدادات العنصر الجديد")
        layout = QVBoxLayout(self)
        self.cells_inputs = []
        layout.addWidget(QLabel("اسم العنصر:"))
        if shape == "source": default_text = "SOURCE"
        elif shape == "breaker": default_text = "IACM"
        else: default_text = "P"
        self.txt_name = QLineEdit(default_text, self); layout.addWidget(self.txt_name)
        if shape not in ["breaker", "source"]:
            layout.addWidget(QLabel("نوع البوست (النوع الفرعي):"))
            self.cmb_fill = QComboBox(self)
            self.fill_modes = ([("Post DP", "false"), ("Post MX", "half"), ("Post LV", "true")] if shape == "square" else [("Post DP", "false"), ("Post LV", "true")])
            for lbl, fl in self.fill_modes: self.cmb_fill.addItem(lbl, fl)
            idx = next((i for i, (_, fl) in enumerate(self.fill_modes) if fl == filled_type), 0)
            self.cmb_fill.setCurrentIndex(idx); layout.addWidget(self.cmb_fill)
        if shape == "square":
            layout.addWidget(QLabel("عدد الخلايا بالداخل:"))
            self.cmb_cells = QComboBox(self); self.cmb_cells.addItems(["1", "2", "3"])
            self.cmb_cells.currentIndexChanged.connect(self.update_cell_names); layout.addWidget(self.cmb_cells)
            self.cells_frame = QWidget(); self.cells_layout = QVBoxLayout(self.cells_frame)
            layout.addWidget(QLabel("أسماء الخلايا:")); layout.addWidget(self.cells_frame)
            self.update_cell_names()
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def update_cell_names(self):
        for widget in self.cells_inputs: widget.deleteLater()
        self.cells_inputs.clear()
        if not hasattr(self, 'cmb_cells'): return
        count = int(self.cmb_cells.currentText())
        for i in range(count):
            label = QLabel(f"الخلية {i+1}:"); entry = QLineEdit(f"Cell_{i+1}")
            self.cells_layout.addWidget(label); self.cells_layout.addWidget(entry); self.cells_inputs.append(entry)

    def get_values(self, default_fill):
        fill_val = self.cmb_fill.currentData() if hasattr(self, 'cmb_fill') else default_fill
        cells_val = int(self.cmb_cells.currentText()) if hasattr(self, 'cmb_cells') else 1
        cell_names = [entry.text() for entry in self.cells_inputs] if self.cells_inputs else ["Cell_1"]
        return self.txt_name.text(), fill_val, cells_val, cell_names

# ============================================================================
# 4. اللوحات القماشية الأساسية
# ============================================================================
class InfiniteGridCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.grid_size = 30; self.offset_x = 0.0; self.offset_y = 0.0; self.zoom = 1.0
        self.is_dragging = False; self.last_pos = None; self.menu_visible = False
    def draw_background_grid(self, painter):
        painter.setPen(QPen(QColor("#b2bec3"), 2)); r = self.grid_size
        sx = int(-self.offset_x / self.zoom - (-self.offset_x / self.zoom % r)) - r
        sy = int(-self.offset_y / self.zoom - (-self.offset_y / self.zoom % r)) - r
        for x in range(sx, sx + int(self.width() / self.zoom) + 60, r):
            for y in range(sy, sy + int(self.height() / self.zoom) + 60, r):
                painter.drawPoint(QPointF(x, y))
    def wheelEvent(self, event):
        if self.menu_visible: return
        pos = event.position()
        wx = (pos.x() - self.offset_x) / self.zoom; wy = (pos.y() - self.offset_y) / self.zoom
        delta = event.angleDelta().y()
        if delta != 0:
            factor = 1.12 if delta > 0 else 1.0 / 1.12
            self.zoom = max(0.3, min(3.0, self.zoom * factor))
            self.offset_x = pos.x() - wx * self.zoom; self.offset_y = pos.y() - wy * self.zoom
            if hasattr(self, 'stream_visible_elements'): self.stream_visible_elements()
            self.update()

class ElectricalNetworkCanvas(InfiniteGridCanvas):
    def __init__(self):
        super().__init__()
        self.engine = NetworkEngine()
        self.posts = {}
        self.wires = []
        self.selected_id = None
        self.drag_start_point = None
        self.next_post_id = 0

        self.full_backup_posts = {}
        self.full_backup_wires = []
        self.full_backup_junctions = []

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(1000)
        self.save_timer.timeout.connect(self.save_network_internally)

        self.junction_points = []
        self.load_network_internally()

    def get_all_available_points(self):
        pts = []
        r = self.grid_size
        for pid, post in self.posts.items():
            if isinstance(post, MainSourceElement):
                post.generate_points(r)
                pts.extend([
                    {"pid": pid, "type": "source", "pt_id": pt["id"],
                     "x": pt["x"], "y": pt["y"], "color": pt["color"]}
                    for pt in post.connection_points
                ])
            elif isinstance(post, SquarePost):
                pts.extend(post.get_connection_points(pid))
            else:
                rad = math.radians(post["angle"])
                rot = lambda px, py: QPointF(
                    (px - post["x"]) * math.cos(rad) - (py - post["y"]) * math.sin(rad) + post["x"],
                    (px - post["x"]) * math.sin(rad) + (py - post["y"]) * math.cos(rad) + post["y"]
                )
                shape = post["shape"]
                if shape == "breaker":
                    pts.extend([
                        {"pid": pid, "type": "breaker", "pt_id": f"{pid}_L",
                         "x": rot(post["x"] - 30, post["y"]).x(),
                         "y": rot(post["x"] - 30, post["y"]).y(), "color": "#000000"},
                        {"pid": pid, "type": "breaker", "pt_id": f"{pid}_R",
                         "x": rot(post["x"] + 30, post["y"]).x(),
                         "y": rot(post["x"] + 30, post["y"]).y(), "color": "#000000"}
                    ])
                elif shape == "circle":
                    pts.append({
                        "pid": pid, "type": "post", "pt_id": f"{pid}_T0",
                        "x": rot(post["x"], post["y"] - 30).x(),
                        "y": rot(post["x"], post["y"] - 30).y(),
                        "color": "#000000"
                    })
        for jp in self.junction_points:
            jp.update_position(self.wires)
            pts.append({
                "pid": jp.id,
                "type": "junction",
                "pt_id": jp.id,
                "x": jp.x,
                "y": jp.y,
                "color": jp.powered_color if jp.is_powered else "#000000"
            })
        return pts

    def add_element_smart(self, shape, filled_type):
        dialog = PostSettingsDialog(shape, filled_type, self)
        if dialog.exec() == QDialog.Accepted:
            name, final_fill, cells_count, cell_names = dialog.get_values(filled_type)

            cx = round(((self.width() / 2 - self.offset_x) / self.zoom) / self.grid_size) * self.grid_size
            cy = round(((self.height() / 2 - self.offset_y) / self.zoom) / self.grid_size) * self.grid_size

            def get_pos(p):
                if hasattr(p, 'x'):
                    return p.x, p.y
                elif isinstance(p, dict):
                    return p.get('x', 0), p.get('y', 0)
                return 0, 0

            while any(
                get_pos(p)[0] == cx and get_pos(p)[1] == cy
                for p in self.posts.values()
            ):
                cx += self.grid_size * 3

            pid = f"p_{self.next_post_id}"
            self.next_post_id += 1

            if shape == "source":
                self.posts[pid] = MainSourceElement(name, cx, cy)
            elif shape == "square":
                self.posts[pid] = SquarePost(name, cx, cy, final_fill, cells_count, cell_names)
            else:
                self.posts[pid] = {
                    "name": name,
                    "x": cx,
                    "y": cy,
                    "shape": shape,
                    "filled_type": final_fill,
                    "angle": 0,
                    "closed": False
                }

            self.engine.add_post(pid, self.posts[pid])
            self.save_timer.start()
            self.stream_visible_elements()

    def save_network_internally(self):
        data = {
            "posts": {},
            "wires": [],
            "junction_points": [],
            "counters": {
                "post": self.next_post_id,
                "wire": WireElement._id_counter,
                "junction": JunctionPoint._id_counter
            }
        }
        for pid, post in self.posts.items():
            if isinstance(post, MainSourceElement):
                data["posts"][pid] = {"type": "source", "name": post.name, "x": post.x, "y": post.y}
            elif isinstance(post, SquarePost):
                data["posts"][pid] = {
                    "type": "square",
                    "name": post.name,
                    "x": post.x,
                    "y": post.y,
                    "filled_type": post.filled_type,
                    "angle": post.angle,
                    "cells": [{"name": c.name, "closed": c.closed,
                               "x_offset": c.x_offset, "y_offset": c.y_offset} for c in post.cells]
                }
            else:
                data["posts"][pid] = {"type": "dict", **post}

        for w in self.wires:
            data["wires"].append({
                "start_pt_id": w.start_pt_id,
                "start_x": w.start_x,
                "start_y": w.start_y,
                "end_post_id": w.end_post_id,
                "end_x": w.end_x,
                "end_y": w.end_y,
                "color": w.color,
                "name": w.name,
                "wire_type": w.wire_type
            })

        for jp in self.junction_points:
            data["junction_points"].append({
                "id": jp.id,
                "wire_id": jp.wire_id,
                "pos_ratio": jp.pos_ratio
            })

        try:
            with open("network_config.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.full_backup_posts = data["posts"]
            self.full_backup_wires = data["wires"]
            self.full_backup_junctions = data["junction_points"]
        except Exception:
            pass

    def load_network_internally(self):
        if not os.path.exists("network_config.json"):
            return
        try:
            with open("network_config.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            self.posts.clear()
            self.wires.clear()
            self.junction_points.clear()
            JunctionPoint._id_counter = 0
            WireElement._id_counter = 0

            counters = data.get("counters", {})
            self.next_post_id = counters.get("post", 0)

            for pid, p_dict in data.get("posts", {}).items():
                if p_dict["type"] == "source":
                    self.posts[pid] = MainSourceElement(p_dict["name"], p_dict["x"], p_dict["y"])
                elif p_dict["type"] == "square":
                    self.posts[pid] = self.rebuild_square_post(p_dict)
                else:
                    p_copy = dict(p_dict)
                    p_copy.pop("type", None)
                    self.posts[pid] = p_copy

            for w_data in data.get("wires", []):
                wire = WireElement(
                    w_data["start_pt_id"], w_data["start_x"], w_data["start_y"],
                    w_data["end_post_id"], w_data["end_x"], w_data["end_y"],
                    w_data["color"],
                    w_data.get("name", "Cable"),
                    w_data.get("wire_type", "straight")
                )
                self.wires.append(wire)

            for jd in data.get("junction_points", []):
                wire = next((w for w in self.wires if w.id == jd["wire_id"]), None)
                if wire:
                    jp = JunctionPoint(jd["wire_id"], jd["pos_ratio"])
                    jp.id = jd["id"]
                    jp.update_position(self.wires)
                    self.junction_points.append(jp)

            self.full_backup_posts = data.get("posts", {})
            self.full_backup_wires = data.get("wires", [])
            self.full_backup_junctions = data.get("junction_points", [])

            self.stream_visible_elements()
        except Exception:
            pass

    def rebuild_square_post(self, data):
        post = SquarePost(
            data["name"],
            data["x"],
            data["y"],
            data["filled_type"],
            len(data["cells"]),
            [c["name"] for c in data["cells"]]
        )
        post.angle = data.get("angle", 0)
        for i, cell_data in enumerate(data["cells"]):
            if i < len(post.cells):
                post.cells[i].closed = cell_data["closed"]
                post.cells[i].x_offset = cell_data.get("x_offset", post.cells[i].x_offset)
                post.cells[i].y_offset = cell_data.get("y_offset", post.cells[i].y_offset)
        return post

    def stream_visible_elements(self):
        left = -self.offset_x / self.zoom - 5000
        right = (self.width() - self.offset_x) / self.zoom + 5000
        top = -self.offset_y / self.zoom - 5000
        bottom = (self.height() - self.offset_y) / self.zoom + 5000

        for pid, p_dict in self.full_backup_posts.items():
            if left <= p_dict.get("x", 0) <= right and top <= p_dict.get("y", 0) <= bottom:
                if pid not in self.posts:
                    if p_dict["type"] == "source":
                        self.posts[pid] = MainSourceElement(p_dict["name"], p_dict["x"], p_dict["y"])
                    elif p_dict["type"] == "square":
                        self.posts[pid] = self.rebuild_square_post(p_dict)
                    else:
                        p_copy = dict(p_dict)
                        p_copy.pop("type", None)
                        self.posts[pid] = p_copy

        for w_dict in self.full_backup_wires:
            if not any(
                w.start_pt_id == w_dict["start_pt_id"] and w.end_post_id == w_dict["end_post_id"]
                for w in self.wires
            ):
                wire = WireElement(
                    w_dict["start_pt_id"], w_dict["start_x"], w_dict["start_y"],
                    w_dict["end_post_id"], w_dict["end_x"], w_dict["end_y"],
                    w_dict["color"],
                    w_dict.get("name", "Cable"),
                    w_dict.get("wire_type", "straight")
                )
                self.wires.append(wire)

        for jd in self.full_backup_junctions:
            wire = next((w for w in self.wires if w.id == jd["wire_id"]), None)
            if wire:
                jp = JunctionPoint(jd["wire_id"], jd["pos_ratio"])
                jp.id = jd["id"]
                jp.update_position(self.wires)
                self.junction_points.append(jp)

        self.update()

    def update_power_flow(self):
        self.engine.posts = self.posts
        self.engine.wires = self.wires
        self.engine.junction_points = self.junction_points
        self.engine.update_power_flow()

    def _draw_posts(self, painter):
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        for pid, post in self.posts.items():
            if isinstance(post, MainSourceElement):
                post.draw(painter, 30)
            elif isinstance(post, SquarePost):
                self._draw_square_post(painter, pid, post)
            else:
                self._draw_other_post(painter, pid, post)

    def _draw_square_post(self, painter, pid, post):
        cx, cy = post.x, post.y
        rad = math.radians(post.angle)
        def rot(px, py):
            return QPointF(
                (px - cx) * math.cos(rad) - (py - cy) * math.sin(rad) + cx,
                (px - cx) * math.sin(rad) + (py - cy) * math.cos(rad) + cy
            )

        pt1 = rot(cx, cy - 30)
        pt2 = rot(cx - 30, cy + 30)
        pt3 = rot(cx + 30, cy + 30)

        any_powered = any(cell.is_powered and cell.closed for cell in post.cells)
        triangle_color = QColor(post.powered_color) if any_powered else QColor("#2c3e50")

        painter.setPen(QPen(triangle_color, 2))
        if post.filled_type == "half":
            pm = rot(cx, cy + 30)
            painter.setBrush(QBrush(triangle_color))
            painter.drawPolygon(QPolygonF([pt1, pt2, pm]))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPolygon(QPolygonF([pt1, pm, pt3]))
        else:
            if post.filled_type == "true":
                painter.setBrush(QBrush(triangle_color))
            else:
                painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPolygon(QPolygonF([pt1, pt2, pt3]))

        for idx, cell in enumerate(post.cells):
            pt = rot(cx + cell.x_offset, cy + cell.y_offset)
            if cell.is_powered and cell.closed:
                cell_color = QColor(cell.powered_color)
            else:
                cell_color = QColor("#95a5a6")
            painter.setBrush(QBrush(cell_color))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawEllipse(pt, 8, 8)

            if cell.closed:
                painter.drawText(pt.x() - 10, pt.y() - 12, "🔒")
            else:
                painter.drawText(pt.x() - 10, pt.y() - 12, "🔓")

        border_color = QColor(post.powered_color) if any_powered else QColor("#2c3e50")
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.setPen(QPen(border_color, 2.5))
        painter.drawRoundedRect(cx - 30, cy - 30, 60, 60, 2, 2)

        painter.setPen(QPen(QColor("#000000")))
        painter.drawText(cx - 15, cy + 30 + 14, post.name)

    def _draw_other_post(self, painter, pid, post):
        cx, cy = post["x"], post["y"]
        rad = math.radians(post["angle"])
        def rot(px, py):
            return QPointF(
                (px - cx) * math.cos(rad) - (py - cy) * math.sin(rad) + cx,
                (px - cx) * math.sin(rad) + (py - cy) * math.cos(rad) + cy
            )
        is_powered = post.get("is_powered", False)
        fill_color = QColor(post.get("powered_color", "#ffffff")) if is_powered else QColor("#ffffff")
        symbol_color = QColor(post.get("powered_color", "#000000")) if is_powered else QColor("#000000")

        if post["shape"] == "breaker":
            painter.setBrush(QBrush(fill_color if is_powered else QColor("#000000")))
            painter.drawEllipse(rot(cx - 30, cy), 3.5, 3.5)
            painter.drawEllipse(rot(cx + 30, cy), 3.5, 3.5)
            line_color = QColor(post["powered_color"]) if (is_powered and post.get("closed", False)) else (
                QColor("#d35400") if post.get("closed", False) else QColor("#000000")
            )
            painter.setPen(QPen(line_color, 3))
            if post.get("closed", False):
                painter.drawLine(rot(cx - 30, cy), rot(cx + 30, cy))
            else:
                painter.drawLine(rot(cx - 30, cy), rot(cx + 20, cy - 20))
            painter.setPen(QPen(QColor("#000000")))
            painter.drawText(cx - 15, cy + 30 + 14, post["name"])
            return

        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(symbol_color, 2.5))
        painter.drawEllipse(QPointF(cx, cy), 30, 30)

        pt1 = rot(cx, cy - 30)
        pt2 = rot(cx + 30 * math.cos(math.radians(230)), cy - 30 * math.sin(math.radians(230)))
        pt3 = rot(cx + 30 * math.cos(math.radians(310)), cy - 30 * math.sin(math.radians(310)))
        painter.setPen(QPen(symbol_color, 2))
        if post["filled_type"] == "half":
            pm = rot((pt2.x() + pt3.x()) / 2, (pt2.y() + pt3.y()) / 2)
            painter.setBrush(QBrush(symbol_color))
            painter.drawPolygon(QPolygonF([pt1, pt2, pm]))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPolygon(QPolygonF([pt1, pm, pt3]))
        else:
            painter.setBrush(QBrush(symbol_color) if post["filled_type"] == "true" else QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPolygon(QPolygonF([pt1, pt2, pt3]))

        painter.setBrush(QBrush(QColor("#e74c3c")))
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.drawEllipse(pt1, 4, 4)

        painter.setPen(QPen(QColor("#000000")))
        painter.drawText(cx - 15, cy + 30 + 14, post["name"])

# ============================================================================
# 5. اللوحة القماشية التفاعلية (مع دعم الأسلاك العادية)
# ============================================================================
class InteractiveNetworkCanvas(ElectricalNetworkCanvas):
    def __init__(self):
        super().__init__()
        self._click_pos = None
        self.junction_points = []
        self._selected_wire = None  # لتحديد السلك عند النقر

    # ============================================================
    # دوال مساعدة للبحث (بدون تغيير)
    # ============================================================
    def _find_point_at(self, wx, wy, threshold=12):
        for pt in self.get_all_available_points():
            if math.hypot(wx - pt["x"], wy - pt["y"]) < threshold:
                return pt
        return None

    def _find_element_at(self, wx, wy):
        for pid, post in self.posts.items():
            px, py = (post.x, post.y) if hasattr(post, 'x') else (post["x"], post["y"])
            hit_radius = 130 if isinstance(post, MainSourceElement) else 30
            if math.hypot(wx - px, wy - py) < hit_radius:
                return pid
        return None

    def _find_wire_at(self, wx, wy, threshold=10):
        for wire in self.wires:
            ax, ay = wire.start_x, wire.start_y
            bx, by = wire.end_x, wire.end_y
            dx = bx - ax
            dy = by - ay
            length_sq = dx*dx + dy*dy
            if length_sq == 0:
                continue
            t = ((wx - ax) * dx + (wy - ay) * dy) / length_sq
            t = max(0.0, min(1.0, t))
            proj_x = ax + t * dx
            proj_y = ay + t * dy
            dist = math.hypot(wx - proj_x, wy - proj_y)
            if dist < threshold:
                return wire, t
        return None, None

    # ============================================================
    # مزامنة المحرك (بدون تغيير)
    # ============================================================
    def _sync_engine(self):
        self.engine.posts = {}
        self.engine.wires = []
        self.engine.junction_points = []
        self.engine.posts.update(self.posts)
        self.engine.wires.extend(self.wires)
        self.engine.junction_points.extend(self.junction_points)
        self.engine.update_power_flow()

    # ============================================================
    # إدارة نقاط التفرع (بدون تغيير في السلوك، فقط تعديل بسيط للحفاظ على الاسم والنوع)
    # ============================================================
    def add_junction_point(self, wire, pos_ratio=0.5):
        jp = JunctionPoint(wire.id, pos_ratio)
        jp.update_position(self.wires)
        self.wires.remove(wire)
        # إنشاء سلكين جديدين مع الاحتفاظ بالاسم والنوع
        wire1 = WireElement(wire.start_pt_id, wire.start_x, wire.start_y,
                            jp.id, jp.x, jp.y, wire.color, wire.name + "_1", wire.wire_type)
        wire2 = WireElement(jp.id, jp.x, jp.y,
                            wire.end_post_id, wire.end_x, wire.end_y, wire.color, wire.name + "_2", wire.wire_type)
        self.wires.append(wire1)
        self.wires.append(wire2)
        self.junction_points.append(jp)
        self._sync_engine()
        self.save_timer.start()
        self.update()

    def show_junction_menu(self, junction_point, global_pos):
        self.menu_visible = True
        menu = QMenu(self)
        menu.setStyleSheet("background-color: #ffffff; color: #2c3e50; font-weight: bold;")
        delete_action = QAction("🗑️ مسح النقطة", menu)
        delete_action.triggered.connect(lambda: self._delete_junction_point(junction_point["pt_id"]))
        menu.addAction(delete_action)
        menu.exec(global_pos)
        self.menu_visible = False

    def _delete_junction_point(self, point_id):
        jp = next((j for j in self.junction_points if j.id == point_id), None)
        if not jp:
            return
        self.wires = [w for w in self.wires if w.start_pt_id != point_id and w.end_post_id != point_id]
        self.junction_points.remove(jp)
        self._sync_engine()
        self.save_timer.start()
        self.update()

    # ============================================================
    # تحديث مواقع نقاط التوصيل (بدون تغيير)
    # ============================================================
    def _update_wire_endpoints(self):
        all_pts = {pt["pt_id"]: pt for pt in self.get_all_available_points() if "pt_id" in pt}
        for wire in self.wires:
            start = all_pts.get(wire.start_pt_id)
            end = all_pts.get(wire.end_post_id)
            if start:
                wire.start_x, wire.start_y = start["x"], start["y"]
            if end:
                wire.end_x, wire.end_y = end["x"], end["y"]
        for jp in self.junction_points:
            jp.update_position(self.wires)

    # ============================================================
    # رسم نقاط التفرع (بدون تغيير)
    # ============================================================
    def _draw_junction_points(self, painter):
        for jp in self.junction_points:
            jp.update_position(self.wires)
            color = QColor(jp.powered_color) if jp.is_powered else QColor("#888888")
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawEllipse(QPointF(jp.x, jp.y), 6, 6)

    # ============================================================
    # دوال السلك الجديدة (القائمة، تعديل الاسم، النوع، نقطة تفرع، مسح)
    # ============================================================
    def _show_wire_menu(self, wire, global_pos):
        self.menu_visible = True
        menu = QMenu(self)
        menu.setStyleSheet("background-color: #ffffff; color: #2c3e50; font-weight: bold;")
        edit_name_action = QAction("✏️ تعديل الاسم", menu)
        edit_name_action.triggered.connect(lambda: self._edit_wire_name(wire))
        menu.addAction(edit_name_action)

        change_type_action = QAction("🔀 تغيير النوع", menu)
        change_type_action.triggered.connect(lambda: self._change_wire_type(wire))
        menu.addAction(change_type_action)

        junction_action = QAction("➕ نقطة تفرع", menu)
        junction_action.triggered.connect(lambda: self._add_junction_from_wire(wire))
        menu.addAction(junction_action)

        menu.addSeparator()
        delete_action = QAction("🗑️ مسح", menu)
        delete_action.triggered.connect(lambda: self._delete_wire(wire))
        menu.addAction(delete_action)

        menu.exec(global_pos)
        self.menu_visible = False

    def _edit_wire_name(self, wire):
        new_name, ok = QInputDialog.getText(self, "تعديل اسم السلك", "أدخل الاسم الجديد:", text=wire.name)
        if ok and new_name.strip():
            wire.name = new_name.strip()
            self._sync_engine()
            self.save_timer.start()
            self.update()

    def _change_wire_type(self, wire):
        items = ["مستقيم", "متقطع"]
        current_index = 0 if wire.wire_type == "straight" else 1
        new_type, ok = QInputDialog.getItem(self, "تغيير نوع السلك", "اختر النوع:", items, current_index, False)
        if ok:
            wire.wire_type = "straight" if new_type == "مستقيم" else "bent"
            self._sync_engine()
            self.save_timer.start()
            self.update()

    def _delete_wire(self, wire):
        if wire in self.wires:
            self.wires.remove(wire)
            self.junction_points = [jp for jp in self.junction_points if jp.wire_id != wire.id]
            self._sync_engine()
            self.save_timer.start()
            self.update()

    def _add_junction_from_wire(self, wire):
        self.add_junction_point(wire, 0.5)

    # ============================================================
    # القائمة السياقية للبوستات والمصادر (بدون تغيير)
    # ============================================================
    def show_tactical_menu(self, pid, global_pos):
        self.menu_visible = True
        menu = QMenu(self)
        menu.setStyleSheet("background-color: #ffffff; color: #2c3e50; font-weight: bold;")
        post = self.posts[pid]

        if not isinstance(post, MainSourceElement):
            rotate_action = QAction("🔄 تدوير (90°)", menu)
            rotate_action.triggered.connect(lambda: self._rotate_post(pid))
            menu.addAction(rotate_action)
            menu.addSeparator()

        delete_action = QAction("🗑️ مسح", menu)
        delete_action.triggered.connect(lambda: self._delete_post_and_connections(pid))
        menu.addAction(delete_action)

        menu.exec(global_pos)
        self.menu_visible = False

    def _rotate_post(self, pid):
        post = self.posts[pid]
        if hasattr(post, 'angle'):
            post.angle = (post.angle + 90) % 360
        else:
            post["angle"] = (post["angle"] + 90) % 360
        self._sync_engine()
        self.save_timer.start()
        self.update()

    def _delete_post_and_connections(self, pid):
        if pid in self.posts:
            del self.posts[pid]
        if pid in self.full_backup_posts:
            del self.full_backup_posts[pid]
        self.wires = [w for w in self.wires if not (w.end_post_id.startswith(pid) or w.start_pt_id.startswith(pid))]
        self.junction_points = [jp for jp in self.junction_points if any(w.start_pt_id == jp.id or w.end_post_id == jp.id for w in self.wires)]
        self._sync_engine()
        self.save_timer.start()
        self.update()

    # ============================================================
    # دوال السحب والإنهاء (مع تعديل بسيط لإنشاء سلك باسم افتراضي)
    # ============================================================
    def _drag_element(self, dx, dy):
        post = self.posts.get(self.selected_id)
        if not post:
            return
        if hasattr(post, 'x'):
            post.x += dx / self.zoom
            post.y += dy / self.zoom
            if isinstance(post, MainSourceElement):
                post.generate_points(30)
        else:
            post["x"] += dx / self.zoom
            post["y"] += dy / self.zoom
        self._update_wire_endpoints()
        self.save_timer.start()
        self.update()

    def _drag_canvas(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        self.stream_visible_elements()

    def _finish_wire_drag(self, wx, wy):
        end_point = self._find_point_at(wx, wy, threshold=25)
        if end_point and end_point["pid"] != self.drag_start_point["pid"]:
            color = self.drag_start_point["color"] if self.drag_start_point["type"] == "source" else "#000000"
            # إنشاء سلك باسم افتراضي
            wire_name = f"Cable_{len(self.wires) + 1}"
            wire = WireElement(
                self.drag_start_point["pt_id"],
                self.drag_start_point["x"],
                self.drag_start_point["y"],
                end_point["pt_id"],
                end_point["x"],
                end_point["y"],
                color,
                wire_name,
                "straight"
            )
            self.wires.append(wire)
            self._sync_engine()
            self.save_timer.start()
            self.update()

    def _finish_element_drag(self, event):
        post = self.posts[self.selected_id]
        if hasattr(post, 'x'):
            post.x = round(post.x / 30) * 30
            post.y = round(post.y / 30) * 30
            if isinstance(post, MainSourceElement):
                post.generate_points(30)
        else:
            if (self.last_pos and
                math.hypot(event.position().x() - self.last_pos.x(),
                           event.position().y() - self.last_pos.y()) < 4 and
                post["shape"] == "breaker"):
                self._sync_engine()
                success, message = self.engine.toggle_breaker(self.selected_id)
                if not success:
                    QMessageBox.warning(self, "تحذير - قصر كهربائي", message)
                self._sync_engine()
                self.save_timer.start()
                self.update()
                return

            post["x"] = round(post["x"] / 30) * 30
            post["y"] = round(post["y"] / 30) * 30

        self._update_wire_endpoints()
        self._sync_engine()
        self.save_timer.start()
        self.update()

    # ============================================================
    # أحداث الماوس (معدلة للتعامل مع السلك فقط)
    # ============================================================
    def mousePressEvent(self, event):
        pos = event.position()
        wx = (pos.x() - self.offset_x) / self.zoom
        wy = (pos.y() - self.offset_y) / self.zoom
        self.selected_id = None
        self.drag_start_point = None
        self._click_pos = None
        self._selected_wire = None

        # 1. نقاط التوصيل (بدون تغيير)
        clicked_point = self._find_point_at(wx, wy)
        if clicked_point:
            if event.button() == Qt.MouseButton.LeftButton:
                pid = clicked_point.get("pid")
                post = self.posts.get(pid) if pid else None
                if post is not None and hasattr(post, "cells") and "cell_index" in clicked_point:
                    self.drag_start_point = clicked_point
                    self.last_pos = event.position()
                    self._click_pos = event.position()
                    return
                self.drag_start_point = clicked_point
                self.last_pos = event.position()
                self._click_pos = event.position()
                return
            elif event.button() == Qt.MouseButton.RightButton:
                if clicked_point.get("type") == "junction":
                    self.show_junction_menu(clicked_point, event.globalPosition().toPoint())
                    return

        # 2. عنصر (بوست، مصدر، قاطع) – بدون تغيير
        element_id = self._find_element_at(wx, wy)
        if element_id:
            if event.button() == Qt.MouseButton.LeftButton:
                self.selected_id = element_id
                self.last_pos = event.position()
                self._click_pos = event.position()
                return
            elif event.button() == Qt.MouseButton.RightButton:
                self.is_dragging = False
                self.show_tactical_menu(element_id, event.globalPosition().toPoint())
                return

        # 3. سلك – نحدده لعرض القائمة عند التحرير (بدون إضافة نقطة تفرع فورية)
        if event.button() == Qt.MouseButton.LeftButton:
            wire, t = self._find_wire_at(wx, wy)
            if wire:
                self._selected_wire = wire
                self.last_pos = event.position()
                self._click_pos = event.position()
                return

        # 4. خلفية (سحب الشبكة)
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        if not self.last_pos:
            return
        pos = event.position()
        dx = pos.x() - self.last_pos.x()
        dy = pos.y() - self.last_pos.y()
        self.last_pos = pos

        if self.drag_start_point:
            self.update()
        elif self.selected_id and event.buttons() == Qt.MouseButton.LeftButton:
            self._drag_element(dx, dy)
        elif self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self._drag_canvas(dx, dy)

    def mouseReleaseEvent(self, event):
        pos = event.position()
        wx = (pos.x() - self.offset_x) / self.zoom
        wy = (pos.y() - self.offset_y) / self.zoom

        # 1. نقاط التوصيل (بدون تغيير)
        if self.drag_start_point and event.button() == Qt.MouseButton.LeftButton:
            if self._click_pos:
                dist = math.hypot(event.position().x() - self._click_pos.x(),
                                  event.position().y() - self._click_pos.y())
                if dist < 5:
                    pid = self.drag_start_point.get("pid")
                    post = self.posts.get(pid) if pid else None
                    if post is not None and hasattr(post, "cells") and "cell_index" in self.drag_start_point:
                        idx = self.drag_start_point["cell_index"]
                        self._sync_engine()
                        success, message = self.engine.toggle_cell(pid, idx)
                        if not success:
                            QMessageBox.warning(self, "تحذير - قصر كهربائي", message)
                        self._sync_engine()
                        self.save_timer.start()
                        self.update()
                        self.drag_start_point = None
                        self._click_pos = None
                        return
            self._finish_wire_drag(wx, wy)
            self.drag_start_point = None
            self._click_pos = None
            return

        # 2. القواطع والبوستات والمصادر (بدون تغيير)
        if self.selected_id and event.button() == Qt.MouseButton.LeftButton:
            if self._click_pos:
                dist = math.hypot(event.position().x() - self._click_pos.x(),
                                  event.position().y() - self._click_pos.y())
                if dist < 5:
                    # التحقق إذا كان قاطعاً أم لا
                    post = self.posts.get(self.selected_id)
                    if isinstance(post, dict) and post.get("shape") == "breaker":
                        # تبديل حالة القاطع
                        self._sync_engine()
                        success, message = self.engine.toggle_breaker(self.selected_id)
                        if not success:
                            QMessageBox.warning(self, "تحذير - قصر كهربائي", message)
                        self._sync_engine()
                        self.save_timer.start()
                        self.update()
                        self.selected_id = None
                        self._click_pos = None
                        self.last_pos = None
                        return
                    else:
                        # عرض القائمة للبوستات والمصادر
                        self.show_tactical_menu(self.selected_id, event.globalPosition().toPoint())
                        self.selected_id = None
                        self._click_pos = None
                        self.last_pos = None
                        return
            self._finish_element_drag(event)
            self.selected_id = None
            self._click_pos = None

        # 3. السلك: عرض القائمة عند النقر الأيسر (بدون سحب)
        if self._selected_wire and event.button() == Qt.MouseButton.LeftButton:
            if self._click_pos:
                dist = math.hypot(event.position().x() - self._click_pos.x(),
                                  event.position().y() - self._click_pos.y())
                if dist < 5:
                    self._show_wire_menu(self._selected_wire, event.globalPosition().toPoint())
            self._selected_wire = None
            self._click_pos = None
            self.last_pos = None
            return

        # 4. سحب الشبكة
        if self.is_dragging:
            self.is_dragging = False

        self.last_pos = None

    # ============================================================
    # حدث الرسم الرئيسي (بدون تغيير)
    # ============================================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8f9fa"))

        self.update_power_flow()

        painter.save()
        try:
            painter.translate(self.offset_x, self.offset_y)
            painter.scale(self.zoom, self.zoom)

            self.draw_background_grid(painter)
            self._update_wire_endpoints()

            # رسم الأسلاك (الاسم والنوع يُرسمان داخل WireElement.draw)
            for wire in self.wires:
                wire.draw(painter)

            self._draw_junction_points(painter)

            if self.drag_start_point and self.last_pos:
                painter.setPen(QPen(QColor(self.drag_start_point["color"]), 3, Qt.PenStyle.DashLine))
                mx = (self.last_pos.x() - self.offset_x) / self.zoom
                my = (self.last_pos.y() - self.offset_y) / self.zoom
                painter.drawLine(QPointF(self.drag_start_point["x"], self.drag_start_point["y"]), QPointF(mx, my))

            self._draw_posts(painter)

        finally:
            painter.restore()
        

# ============================================================================
# 6. النافذة الرئيسية والقائمة
# ============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مُحاكي الشبكات الكهربائية الرسومي (Qt/PySide6)")
        self.resize(1000, 750)
        self.canvas = InteractiveNetworkCanvas()
        layout = QVBoxLayout()
        layout.setSpacing(0); layout.setContentsMargins(0, 0, 0, 0)
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar); layout.addWidget(self.canvas)
        container = QWidget(); container.setLayout(layout); self.setCentralWidget(container)

    def _create_toolbar(self):
        toolbar_widget = QWidget()
        toolbar_widget.setFixedHeight(45)
        toolbar_widget.setStyleSheet("background-color:#ffffff; border-bottom:1px solid #dcdde1;")
        layout = QHBoxLayout(toolbar_widget); layout.setContentsMargins(15, 5, 15, 5)
        btn_add = QPushButton("➕ New Post")
        btn_add.setFixedSize(160, 35)
        btn_add.setStyleSheet("background-color:#3498db; color:white; font-weight:bold; border-radius:4px;")
        main_menu = self._build_menu()
        btn_add.setMenu(main_menu)
        layout.addWidget(btn_add); layout.addStretch()
        return toolbar_widget

    def _build_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("background-color:#ffffff; color:#2c3e50; font-weight:bold;")
        style = "background-color:#ffffff; color:#2c3e50; font-weight:bold;"
        act_src = QAction("⚡ Main Source", menu)
        act_src.triggered.connect(lambda: self.canvas.add_element_smart("source", "false"))
        menu.addAction(act_src); menu.addSeparator()
        cp_menu = menu.addMenu("📦 Post CP"); cp_menu.setStyleSheet(style)
        for label, fill in [("Post DP", "false"), ("Post MX", "half"), ("Post LV", "true")]:
            act = QAction(label, cp_menu)
            act.triggered.connect(lambda _, f=fill: self.canvas.add_element_smart("square", f))
            cp_menu.addAction(act)
        acc_menu = menu.addMenu("⭕ Post ACC"); acc_menu.setStyleSheet(style)
        for label, fill in [("Post DP", "false"), ("Post LV", "true")]:
            act = QAction(label, acc_menu)
            act.triggered.connect(lambda _, f=fill: self.canvas.add_element_smart("circle", f))
            acc_menu.addAction(act)
        menu.addSeparator()
        act_b = QAction("🔌 IACM", menu)
        act_b.triggered.connect(lambda: self.canvas.add_element_smart("breaker", "false"))
        menu.addAction(act_b)
        return menu

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
