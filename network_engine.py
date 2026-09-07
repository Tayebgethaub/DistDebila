# network_engine.py – الإصدار النهائي مع تحسينات كشف القصر

import math
from collections import deque

class NetworkEngine:
    def __init__(self):
        self.posts = {}
        self.wires = []
        self.junction_points = []

    def add_post(self, pid, post):
        self.posts[pid] = post

    # ============================================================
    #  تحديث تدفق الطاقة (للتشغيل العادي)
    # ============================================================
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

    # ============================================================
    #  كشف القصر بالمحاكاة (المنطق الجديد المُحسَّن)
    # ============================================================
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

    # ============================================================
    #  فحص وجود قصر كهربائي (بعد الإغلاق الافتراضي)
    # ============================================================
    def _check_for_short(self):
        """
        تبحث عن وجود مصدرين مختلفين متصلين عبر مسار موصل.
        تعبر الشبكة بنفس قواعد _propagate_power (الخلايا المغلقة، القواطع المغلقة، الأسلاك).
        إرجاع (True, "تفاصيل") إذا وجد قصر، وإلا (False, "").
        """
        self._cleanup_junctions()
        
        # 1. بناء خرائط التوصيل
        wire_map = self._build_wire_map()
        post_bus_map = self._build_post_bus_map()
        breaker_map = self._build_breaker_map()
        
        # 2. جمع نقاط المصادر وألوانها
        source_points = {}
        for pid, post in self.posts.items():
            if hasattr(post, 'shape') and post.shape == "source":
                for pt in post.connection_points:
                    source_points[pt["id"]] = pt["color"]
        
        # إذا كان هناك مصدر واحد أو أقل، لا يوجد قصر
        if len(set(source_points.values())) <= 1:
            return False, ""
        
        # 3. BFS من كل مصدر للعثور على مصادر أخرى متصلة
        visited_global = set()
        
        for start_pt, start_color in source_points.items():
            if start_pt in visited_global:
                continue
            
            # BFS من نقطة المصدر الحالية
            queue = deque([(start_pt, [start_pt])])  # (نقطة, المسار)
            visited = set()
            
            while queue:
                current_pt, path = queue.popleft()
                if current_pt in visited:
                    continue
                visited.add(current_pt)
                visited_global.add(current_pt)
                
                # هل وصلنا إلى مصدر آخر بلون مختلف؟
                if current_pt in source_points and current_pt != start_pt:
                    other_color = source_points[current_pt]
                    if other_color != start_color:
                        # بناء رسالة مختصرة للمسار
                        path_str = " → ".join(path[-5:])
                        return True, f"مصدر {start_color} متصل بمصدر {other_color} عبر: {path_str}"
                
                # 4. عبور البوستات المربعة (فقط الخلايا المغلقة)
                if current_pt in post_bus_map:
                    pid = post_bus_map[current_pt]
                    post = self.posts.get(pid)
                    if hasattr(post, 'cells'):
                        for other_idx, other_cell in enumerate(post.cells):
                            # ✅ فقط الخلايا المغلقة توصل
                            if other_cell.closed:
                                other_pt = f"{pid}_T{other_idx}"
                                if other_pt != current_pt and other_pt not in visited:
                                    queue.append((other_pt, path + [other_pt]))
                
                # 5. عبور القواطع المغلقة
                if current_pt in breaker_map:
                    other_pt = breaker_map[current_pt]
                    if other_pt not in visited:
                        queue.append((other_pt, path + [other_pt]))
                
                # 6. عبور الأسلاك (دائمًا)
                for wire in wire_map.get(current_pt, []):
                    next_pt = wire.end_post_id if wire.start_pt_id == current_pt else wire.start_pt_id
                    if next_pt not in visited:
                        queue.append((next_pt, path + [next_pt]))
        
        return False, ""

    # ============================================================
    #  دوال بناء الخرائط المساعدة
    # ============================================================
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
               for idx, cell in enumerate(post.cells):
                # إضافة الخلية فقط إذا كانت مغلقة (لأن المفتوحة لا توصل)
                if cell.closed:
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
