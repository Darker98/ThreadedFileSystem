# A Threaded File System

A command-line interface (CLI) application that simulates a file system using a single file as a virtual disk. The file is partitioned to store both directory metadata and file contents, supporting persistence across sessions.

---

## Overview

This file system simulation stores a directory structure and file contents inside a single disk file (`sample.dat`). The directory tree and metadata are stored in the first part of the file, while the remaining blocks store actual file data.

The directory tree is represented in memory as a tree data structure. Changes to the directory or files are saved back to disk for persistence, even in the event of a crash.

---

## Features

- Directory management: create, delete, navigate directories
- File management: create, delete, move, read, write files
- Support for relative and absolute paths
- Persistence by saving directory tree and metadata on each operation
- Multi-threading support with separate command files per thread
- File operations include partial reads/writes, truncation, and moving data within files
- Visualize directory structure and disk memory map

---

## Getting Started

### Prerequisites

- Python 3.x
- `pickle` library (standard in Python)

### Running the File System

1. Open the `File-System` directory.
2. Run the main program with the number of threads you want to simulate:

   ```bash
   python main.py <threads_number>
