# Keep benchmark paths inside their root

resolve_path(root, relative_path) currently resolves paths without checking their boundary. Return the resolved Path only when it is root itself or a descendant of root. Raise ValueError for ../ traversal and absolute paths outside root.
