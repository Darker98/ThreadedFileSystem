from settings import BLOCK_SIZE, FREE_START

class TreeNode:
    def __init__(self, name):
        self.name: str = name

class Directory(TreeNode):
    def __init__(self, name):
        super().__init__(name)
        self.children: list[TreeNode] = []

class File(TreeNode):
    def __init__(self, name, fs):
        super().__init__(name)
        self.size: int = 0
        self.blocks: list[int] = []
        self.fs = fs
        
    # part of a solution for pickling files - taken from chatGPT
    # pickling causes problems if files contain a reference to FileSystem, which contains a file object
    # so remove this reference before pickling and add it back after
    def __getstate__(self):
        state = self.__dict__.copy()
        del state['fs']
        return state
        
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.fs = None
        
    # returns remaining empty space in the last allocated block
    def last_block_remaining_size(self):
        if self.size % BLOCK_SIZE == 0 and self.size != 0:
            return 0
        else:
            return BLOCK_SIZE - (self.size % BLOCK_SIZE)
    
    def set_mode(self, mode: str):
        self.mode = mode
    
    def append_to_file(self, data: str):
        if self.mode == 'r':
            print("Attempt to write in read mode.")
            return

        if len(self.blocks) == 0:
            self.blocks.append(self.fs.allocate())
            
        f = self.fs.file
        if type(data) != bytes:
            data = data.encode()
        last_block_offset = self.size % BLOCK_SIZE
        remaining = self.last_block_remaining_size()
        
        # enough space in current block
        if len(data) <= remaining:
            f.seek(self.blocks[-1] + last_block_offset)
            f.write(data)
            self.size += len(data)
        
        else:   # data more than space in current block
            this_block_data = data[:remaining]
            data = data[remaining:]
            chunk_data = [data[i:i+BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]    # split the data into chunks the size of a block
            
            # fill current last block
            f.seek(self.blocks[-1] + last_block_offset)
            f.write(this_block_data)
            
            # new blocks
            for chunk in chunk_data:
                self.blocks.append(self.fs.allocate())
                f.seek(self.blocks[-1])
                f.write(chunk)
                
            # + this_block_data as that was removed from data originally
            self.size += len(data) + len(this_block_data)
        self.fs.save()
            
    def write_to_file(self, data: str, write_at: int = None):
        # because python does not support overloading
        if write_at == None:
            self.append_to_file(data)
            return
        
        if self.mode == 'r':
            print("Attempt to write in read mode.")
            return
        
        if write_at < 0:
            print("Arguments cannot be negative.")
            return
        
        if len(self.blocks) == 0:
            self.blocks.append(self.fs.allocate())
        
        f = self.fs.file
        if type(data) != bytes:
            data = data.encode()
        last_block_offset = self.size % BLOCK_SIZE
        remaining = self.last_block_remaining_size()
        
        # write_at is after end of file, pad nulls until write_at
        if write_at >= self.size:
            # write_at is in the last block
            if write_at - self.size < remaining:
                  f.seek(self.blocks[-1] + last_block_offset)
                  f.write(b'\x00' * (write_at - self.size))      # pad null bytes
                  
            else:   # write_at is further ahead, more blocks are needed
                f.seek(self.blocks[-1] + last_block_offset)
                f.write(b'\x00' * remaining)   # fill last block
                
                for i in range((write_at - self.size) // BLOCK_SIZE):   # new null blocks
                    this_block = self.fs.allocate()
                    self.blocks.append(this_block)
                    f.seek(this_block)
                    f.write(b'\x00' * BLOCK_SIZE)
                
                self.blocks.append(self.fs.allocate())
                f.seek(self.blocks[-1])
                f.write(b'\x00' * (write_at % BLOCK_SIZE))       # last block partially null
            
            # f now contains padded nulls upto relevant point, simply writing data remains
            self.size = write_at
            self.write_to_file(data)      # same logic as normal writing
        
        else:
            start_block = write_at // BLOCK_SIZE
            start_block_offset = write_at % BLOCK_SIZE
            
            required_size = write_at + len(data)
            # add new blocks if required
            while required_size > len(self.blocks) * BLOCK_SIZE:
                self.blocks.append(self.fs.allocate())
            
            # write remaining start block data
            start_block_data = data[:(BLOCK_SIZE - start_block_offset)]
            data = data[(BLOCK_SIZE - start_block_offset):]
            f.seek(self.blocks[start_block] + start_block_offset)
            f.write(start_block_data)
            
            # split remaining data into chunks
            chunk_data = [data[i:i+BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]
            
            # write chunks
            for i in range(len(chunk_data)):
                f.seek(self.blocks[i + start_block + 1])
                f.write(chunk_data[i])
            
            # either the data is still bound within original f size, or it has exceeded
            # update size accordingly
            self.size = max(self.size, write_at + len(data) + len(start_block_data))
        self.fs.save()
        
    def read_entire_file(self) -> bytes:
        if self.mode != 'r' and self.mode != 'all':
            print("Attempt to read in wrong mode.")
            return
        
        f = self.fs.file
        data = b''
        remaining = self.size
        for block in self.blocks:
            f.seek(block)
            if remaining > BLOCK_SIZE:
                data += f.read(BLOCK_SIZE)
            else:
                data += f.read(remaining)
            remaining -= BLOCK_SIZE
        
        return data

    def read_from_file(self, start: int = None, size: int = None) -> bytes:
        # overloading
        if start == None and size == None:
            return self.read_entire_file()
        
        if start < 0 or size < 0:
            print("Arguments cannot be negative.")
            return
        
        if self.mode != 'r' and self.mode != 'all':
            print("Attempt to read in wrong mode.")
            return
        
        if start > self.size:   # reading outside file
            return b''
        
        if start + size > self.size:
            size = self.size - start
        
        f = self.fs.file
        start_block = start // BLOCK_SIZE
        start_block_offset = start % BLOCK_SIZE
    
        data = b''
        remaining = size
        current_block = start_block

        while remaining > 0 and current_block < len(self.blocks):
            f.seek(self.blocks[current_block])
            block_data = f.read(BLOCK_SIZE)

            # if start block, remove initial data before start
            if current_block == start_block:
                block_data = block_data[start_block_offset:]

            data += block_data[:remaining]  # slices trailing data from last block, otherwise appends entire block to data
            remaining -= len(block_data[:remaining])
            current_block += 1

        return data
    
    def move_within_file(self, source, dest, size):
        if source < 0 or dest < 0 or size < 0:
            print("Arguments cannot be negative.")
            return
        
        data = self.read_from_file(source, size)
        self.write_to_file(b'\x00' * size, source)
        self.write_to_file(data, dest)
    
    def truncate_file(self, size):
        start_block = size // BLOCK_SIZE
        if size % BLOCK_SIZE != 0:
            start_block += 1
            
        for i in range(start_block, len(self.blocks)):
            self.fs.free_spaces[(self.blocks[i] - FREE_START) // BLOCK_SIZE] = True
        self.blocks = self.blocks[:start_block]
        self.size = size
        self.fs.save()
        
    def get_details(self):
        details = f"{self.name} of {self.size} bytes"
        if len(self.blocks) > 0:
            details += f" at blocks {self.blocks}"
        return details