"""
JSON Inspector Tree Component with Interactive Two-Way Selection and Inline Live Editing.
Parses JSON contract data and presents keys/values in a structured hierarchical Treeview.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union
import tkinter as tk
from tkinter import ttk


class JSONInspectorWidget(ttk.Frame):
    """Hierarchical Treeview widget for inspecting JSON Contract v1.1 data with search filter,
    two-way selection callbacks, and inline double-click editing."""

    def __init__(
        self,
        parent: tk.Widget,
        on_field_selected: Optional[Callable[[str], None]] = None,
        on_field_changed: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._raw_data: Optional[Dict[str, Any]] = None
        self.on_field_selected = on_field_selected
        self.on_field_changed = on_field_changed
        self._path_to_item: Dict[str, str] = {}
        self._item_to_path: Dict[str, str] = {}
        self._suppress_select_event = False
        self.var_search = tk.StringVar()
        self._edit_entry: Optional[ttk.Entry] = None

        self._build_ui()


    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Header Label
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ttk.Label(
            header_frame,
            text="SAP JSON Contract Inspector (v1.1)",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        # Search Bar Frame
        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=2)
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Filter:").grid(row=0, column=0, padx=(0, 4), sticky="w")
        entry_search = ttk.Entry(search_frame, textvariable=self.var_search)
        entry_search.grid(row=0, column=1, sticky="ew", padx=2)

        btn_clear = ttk.Button(search_frame, text="X", width=3, command=lambda: self.var_search.set(""))
        btn_clear.grid(row=0, column=2, padx=(2, 0))

        self.var_search.trace_add("write", self._on_search_changed)

        # Treeview with Scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)


        self.tree = ttk.Treeview(
            tree_frame,
            columns=("value", "type"),
            selectmode="browse",
            show="tree headings",
        )
        self.tree.heading("#0", text="Key / Property", anchor="w")
        self.tree.heading("value", text="Value", anchor="w")
        self.tree.heading("type", text="Type", anchor="center")

        self.tree.column("#0", width=160, minwidth=100)
        self.tree.column("value", width=180, minwidth=100)
        self.tree.column("type", width=60, minwidth=40, anchor="center")
        # Double-click to inline edit value column
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)


        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    def load_json(self, source: Union[str, Path, dict]) -> None:
        """Loads JSON data, resets search, and populates the Treeview."""
        if isinstance(source, (str, Path)):
            p = Path(source)
            if p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    self._raw_data = json.load(f)
            else:
                self._raw_data = json.loads(str(source))
        elif isinstance(source, dict):
            self._raw_data = source
        else:
            raise ValueError(f"Unsupported JSON source type: {type(source)}")

        self.var_search.set("")
        self._refresh_tree()

    def _on_search_changed(self, *args):
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._path_to_item.clear()
        self._item_to_path.clear()
        if self._raw_data is None:
            return

        query = self.var_search.get().strip().lower()
        self._populate_node("", self._raw_data, current_path="", query=query)

    def _populate_node(self, parent_id: str, data: Any, current_path: str = "", query: str = "") -> bool:
        """Recursively inserts matching nodes, tracking dotted JSON path."""
        if isinstance(data, dict):
            matched_any = False
            for k, v in data.items():
                p = f"{current_path}.{k}" if current_path else str(k)
                if isinstance(v, (dict, list)):
                    if not query:
                        node = self.tree.insert(parent_id, "end", text=str(k), values=("", type(v).__name__), open=True)
                        self._path_to_item[p] = node
                        self._item_to_path[node] = p
                        self._populate_node(node, v, p, query)
                    else:
                        key_matched = query in str(k).lower()
                        temp_node = self.tree.insert(parent_id, "end", text=str(k), values=("", type(v).__name__), open=True)
                        self._path_to_item[p] = temp_node
                        self._item_to_path[temp_node] = p
                        child_matched = self._populate_node(temp_node, v, p, query)
                        if key_matched or child_matched:
                            matched_any = True
                        else:
                            self.tree.delete(temp_node)
                            self._path_to_item.pop(p, None)
                            self._item_to_path.pop(temp_node, None)
                else:
                    val_str = str(v)
                    type_str = type(v).__name__
                    key_str = str(k)
                    if not query or query in key_str.lower() or query in val_str.lower():
                        node = self.tree.insert(parent_id, "end", text=key_str, values=(val_str, type_str))
                        self._path_to_item[p] = node
                        self._item_to_path[node] = p
                        matched_any = True
            return matched_any

        elif isinstance(data, list):
            matched_any = False
            for i, item in enumerate(data):
                idx_str = f"[{i}]"
                p = f"{current_path}[{i}]"
                if isinstance(item, (dict, list)):
                    if not query:
                        node = self.tree.insert(parent_id, "end", text=idx_str, values=("", type(item).__name__), open=True)
                        self._path_to_item[p] = node
                        self._item_to_path[node] = p
                        self._populate_node(node, item, p, query)
                    else:
                        temp_node = self.tree.insert(parent_id, "end", text=idx_str, values=("", type(item).__name__), open=True)
                        self._path_to_item[p] = temp_node
                        self._item_to_path[temp_node] = p
                        child_matched = self._populate_node(temp_node, item, p, query)
                        if child_matched:
                            matched_any = True
                        else:
                            self.tree.delete(temp_node)
                            self._path_to_item.pop(p, None)
                            self._item_to_path.pop(temp_node, None)
                else:
                    val_str = str(item)
                    type_str = type(item).__name__
                    if not query or query in val_str.lower():
                        node = self.tree.insert(parent_id, "end", text=idx_str, values=(val_str, type_str))
                        self._path_to_item[p] = node
                        self._item_to_path[node] = p
                        matched_any = True
            return matched_any

        return False

    def select_path(self, target_path: str) -> bool:
        """
        Canvas-to-JSON selection: finds the tree node matching target_path (or suffix),
        opens its parent nodes, selects it, and scrolls it into view.
        """
        item = self._path_to_item.get(target_path)
        if not item:
            suffix = f".{target_path}"
            for p, node_id in self._path_to_item.items():
                if p == target_path or p.endswith(suffix):
                    item = node_id
                    break

        if not item or not self.tree.exists(item):
            return False

        parent = self.tree.parent(item)
        while parent:
            self.tree.item(parent, open=True)
            parent = self.tree.parent(parent)

        self._suppress_select_event = True
        try:
            self.tree.selection_set(item)
            self.tree.focus(item)
            self.tree.see(item)
        finally:
            self._suppress_select_event = False

        return True

    def _on_tree_select(self, event=None):
        """Dispatches on_field_selected when user clicks a row in the JSON tree."""
        if self._suppress_select_event:
            return
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        json_path = self._item_to_path.get(item_id)
        if json_path and self.on_field_selected:
            self.on_field_selected(json_path)

    def _on_double_click(self, event):
        """Allows inline editing of the leaf Value column upon double-click."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        if column != "#1":
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return

        json_path = self._item_to_path.get(item)
        if not json_path:
            return

        current_val = self.tree.item(item, "values")[0] if self.tree.item(item, "values") else ""
        item_type = self.tree.item(item, "values")[1] if len(self.tree.item(item, "values")) > 1 else ""
        if item_type in ("dict", "list"):
            return

        bbox = self.tree.bbox(item, column)
        if not bbox:
            return

        if self._edit_entry:
            self._edit_entry.destroy()

        entry = ttk.Entry(self.tree)
        entry.insert(0, str(current_val))
        entry.select_range(0, tk.END)
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        entry.focus_set()
        self._edit_entry = entry

        def apply_edit(event=None):
            new_text = entry.get()
            entry.destroy()
            self._edit_entry = None
            self.tree.item(item, values=(new_text, item_type))
            self._update_raw_data_at_path(json_path, new_text)
            if self.on_field_changed:
                self.on_field_changed(json_path, new_text, self._raw_data)

        def cancel_edit(event=None):
            entry.destroy()
            self._edit_entry = None

        entry.bind("<Return>", apply_edit)
        entry.bind("<FocusOut>", apply_edit)
        entry.bind("<Escape>", cancel_edit)

    def _update_raw_data_at_path(self, path: str, new_value: Any) -> None:
        """Updates internal raw JSON dictionary at dotted path."""
        if not self._raw_data:
            return
        keys = path.split(".")
        curr = self._raw_data
        for k in keys[:-1]:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return
        final_key = keys[-1]
        if isinstance(curr, dict):
            curr[final_key] = new_value

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Returns the current in-memory JSON data."""
        return self._raw_data


