# Write result files atomically

atomic_write(path, text) must create missing parent directories, write UTF-8 text to a temporary sibling, and atomically replace the destination with os.replace. It must leave no temporary file.
