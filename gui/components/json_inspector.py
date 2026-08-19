"""
JSON Inspector Tree Component.
Parses JSON contract data and presents keys/values in a structured hierarchical Treeview.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
import tkinter as tk
from tkinter import ttk


class JSONInspectorWidget(ttk.Frame):
    """Hierarchical Treeview widget for inspecting JSON Contract v1.1 data with search filter."""

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, **kwargs)
        self._raw_data: Optional[Any] = None
        self.var_search = tk.StringVar()
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
        if self._raw_data is None:
            return

        query = self.var_search.get().strip().lower()
        self._populate_node("", self._raw_data, query=query)

    def _populate_node(self, parent_id: str, data: Any, node_name: str = "", query: str = "") -> bool:
        """Recursively inserts matching nodes. Returns True if this node or any child matches query."""
        if isinstance(data, dict):
            matched_any = False
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    if not query:
                        node = self.tree.insert(parent_id, "end", text=str(k), values=("", type(v).__name__), open=True)
                        self._populate_node(node, v, str(k), query)
                    else:
                        key_matched = query in str(k).lower()
                        temp_node = self.tree.insert(parent_id, "end", text=str(k), values=("", type(v).__name__), open=True)
                        child_matched = self._populate_node(temp_node, v, str(k), query)
                        if key_matched or child_matched:
                            matched_any = True
                        else:
                            self.tree.delete(temp_node)
                else:
                    val_str = str(v)
                    type_str = type(v).__name__
                    key_str = str(k)
                    if not query or query in key_str.lower() or query in val_str.lower():
                        self.tree.insert(parent_id, "end", text=key_str, values=(val_str, type_str))
                        matched_any = True
            return matched_any or (bool(query) and query in node_name.lower())

        elif isinstance(data, list):
            matched_any = False
            for i, item in enumerate(data):
                idx_str = f"[{i}]"
                if isinstance(item, (dict, list)):
                    if not query:
                        node = self.tree.insert(parent_id, "end", text=idx_str, values=("", type(item).__name__), open=True)
                        self._populate_node(node, item, idx_str, query)
                    else:
                        temp_node = self.tree.insert(parent_id, "end", text=idx_str, values=("", type(item).__name__), open=True)
                        child_matched = self._populate_node(temp_node, item, idx_str, query)
                        if child_matched:
                            matched_any = True
                        else:
                            self.tree.delete(temp_node)
                else:
                    val_str = str(item)
                    type_str = type(item).__name__
                    if not query or query in val_str.lower():
                        self.tree.insert(parent_id, "end", text=idx_str, values=(val_str, type_str))
                        matched_any = True
            return matched_any

        else:
            val_str = str(data)
            type_str = type(data).__name__
            if not query or query in node_name.lower() or query in val_str.lower():
                self.tree.insert(parent_id, "end", text=node_name, values=(val_str, type_str))
                return True
            return False

