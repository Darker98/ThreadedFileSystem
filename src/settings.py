# 'disk' size constants
BLOCK_SIZE = 32   # size of one block in 'disk memory'
FREE_START = 100 * BLOCK_SIZE   # free space for file content starts at block 1, block 0 is for file metadata and directory structure
TOTAL_MEMORY = 1024 * 10  # total 'disk memory'