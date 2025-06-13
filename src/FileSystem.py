from settings import BLOCK_SIZE, FREE_START, TOTAL_MEMORY
from nodes import Directory, File
from bitarray import bitarray
import pickle
import os
import re

class FileSystem:
    def __init__(self, file_name):
        if os.path.exists(file_name):
            self.file = open(file_name, 'r+b')
            self.load()
        else:
            self.file = open(file_name, 'w+b')
            self.root: Directory = Directory('/')
            # denotes free blocks, custom bitarray() is used as it is much smaller to store in file
            self.free_spaces = bitarray((TOTAL_MEMORY - FREE_START) // BLOCK_SIZE)
            self.free_spaces.setall(True)
            self.save()

        self.current_path: list[Directory] = [self.root]
        self.opened_files = []
        
    def save(self):
        # as root contains references to all its children which further contain references, simply pickling the root stores the entire tree
        metadata = {
            'free': self.free_spaces,
            'root': self.root
        }
        
        data = pickle.dumps(metadata)
        
        if len(data) > FREE_START:
            raise MemoryError("Directory tree is too big to store in provided space, consider increasing FREE_START in settings.")
        
        # pad nulls for cleanliness
        data += b'\x00' * (FREE_START - len(data))
        
        self.file.seek(0)
        self.file.write(data)
        
    def load(self):
        self.file.seek(0)
        data = self.file.read(FREE_START)
        metadata = pickle.loads(data.rstrip(b'\x00'))   # rstrip to remove null padding
        self.free_spaces = metadata['free']
        self.root = metadata['root']
        self.set_fs(self.root)
        
    def set_fs(self, root):
        for child in root.children:
            if type(child) == File:
                child.fs = self
            else:
                self.set_fs(child)
                
    def is_abs(self, path: str):
        if path.startswith('/'):
            return True
        return False
                
    def str_to_path(self, path: str):
        if self.is_abs(path):
            node = self.root
            path_list = path.split('/')[1:]     # first is just ''
        else:   # relative path
            node = self.current_path[-1]
            path_list = path.split('/')
            
        while '' in path_list:
            path_list.remove('')
            
        return node, path_list
    
    def search_dir(self, dir: Directory, name: str, t):
        for node in dir.children:
            if node.name == name and type(node) == t:
                return node
        return None
    
    def search_path(self, path: str, t, parent=False, warn=False):
        node, path_list = self.str_to_path(path)
        prev_node = node
        for i in range(len(path_list) - 1):
            prev_node = node
            node = self.search_dir(node, path_list[i], Directory)
            if node == None:
                if warn:
                    print(f"Directory {'/' + '/'.join(path_list[:i+1])} does not exist.")
                return None
                
        node = self.search_dir(node, path_list[-1], t)
        if node == None and warn:
            print(f"{path} does not exist.")
        
        if not parent:
            return node
        else:
            return node, prev_node


    def mkdir(self, path: str, file=False):
        node, path_list = self.str_to_path(path)
        
        i = 0
        while i < len(path_list) - 1:
            new_node = self.search_dir(node, path_list[i], Directory)
            if new_node == None:
                break
            node = new_node
            i += 1

        # create each directory
        for dir_name in path_list[i:-1]:
            this_dir = Directory(dir_name)
            node.children.append(this_dir)
            node = this_dir
            
        if file:
            if self.search_dir(node, path_list[-1], File):
                print(f"File {'/' * self.is_abs(path) + str(path_list)} already exists.")
            else:
                node.children.append(File(path_list[-1], self))
        else:
            if self.search_dir(node, path_list[-1], Directory):
                print(f"Directory {'/' * self.is_abs(path) + str(path_list)} already exists.")
            else:
                node.children.append(Directory(path_list[-1]))

        self.save()
        
        return node.children[-1]

    def chdir(self, path: str):
        # to go backwards
        if path == ".." and len(self.current_path) > 1:
            self.current_path.pop()
            return
        
        node, path_list = self.str_to_path(path)
        if self.is_abs(path):
            self.current_path = [self.root]
        
        for i in range(len(path_list)):
            found = self.search_dir(self.current_path[-1], path_list[i], Directory)
            if found:
                self.current_path.append(found)
            else:
                print(f"Directory {'/' * self.is_abs(path) + '/'.join(path_list[:i+1])} does not exist.")

    def ls(self):
        output = ''
        if len(self.current_path[-1].children) == 0:
            output = "Empty"
        else:
            for child in self.current_path[-1].children:
                output += f"{child.name}\n"
        return output

    def create(self, path: str) -> File:
        return self.mkdir(path, True)

    def delete_file(self, path: str):
        found, parent = self.search_path(path, File, True, True)
        if found:
            found.truncate_file(0)
            parent.children.remove(found)
            del found
            self.save()

    def delete_file_t(self, file: File, parent: Directory):
        file.truncate_file(0)
        parent.children.remove(file)
        del file
        self.save()
        
    def delete_dir_t(self, dir: Directory, parent: Directory):
        for child in dir.children:
            if type(child) == File:
                self.delete_file_t(child, dir)
            else:
                self.delete_dir_t(child, dir) 
        parent.children.remove(dir)
        del dir
        self.save()

    def delete_dir(self, name: str):
        dir, parent = self.search_path(name, Directory, parent=True)
        if dir:
            for child in dir.children:
                if type(child) == File:
                    self.delete_file_t(child, dir)
                else:
                    self.delete_dir_t(child, dir)
            parent.children.remove(dir)
            del dir
            self.save()
            
    def move_file(self, src: str, dest: str):
        found_src, parent_src = self.search_path(src, File, True, True)
        found_dest = self.search_path(dest, Directory, False, True)
        if not found_src or not found_dest:
            return
        
        found_dest.children.append(found_src)
        parent_src.children.remove(found_src)
        
    def move_dir(self, src: str, dest: str):
        found_src, parent_src = self.search_path(src, Directory, True, True)
        found_dest = self.search_path(dest, Directory, False, True)
        if not found_src or not found_dest:
            return
        
        found_dest.children.append(found_src)
        parent_src.children.remove(found_src)
            
    # returns start index of a free block
    def allocate(self) -> int:
        for i, space in enumerate(self.free_spaces):
            if space:
                self.free_spaces[i] = False
                return (i + FREE_START // BLOCK_SIZE) * BLOCK_SIZE
        raise MemoryError("No free spaces available in file. Consider truncating existing files or changing TOTAL_MEMORY in settings.")

    def open(self, name: str, mode: str) -> File:
        if re.fullmatch(r'[raw]\+?$', mode) is None:    # valid modes are r, a, w, r+, a+, w+
            print(f"Invalid mode: {mode}")
            return
        
        found = self.search_path(name, File)
        
        if mode[0] == 'w':
            if found:
                self.delete_file(name)      # rewrite file in 'w'
            found = self.create(name)
        elif mode[0] == 'a' and not found:
            found = self.create(name)   # create if not exists in 'a'
        elif not found:
            print(f"File {name} does not exist.")
            return
        elif found in self.opened_files:
            print(f"File {name} already opened.")
            return
        
        if len(mode) == 2:      # if r+, a+, or w+, both read and write are allowed
            found.set_mode('all')
        else:
            found.set_mode(mode[0])     # only first letter is allowed
        self.opened_files.append(found)
        return found
    
    def close(self, file: File):
        if file in self.opened_files:
            self.opened_files.remove(file)
        else:
            print("File not open.")
        
    def print_current_path(self):
        print("PS /", end='')
        for dir in self.current_path[1:-1]:
            print(dir.name, end='/')
        if len(self.current_path) > 1:
            print(f"{self.current_path[-1].name}", end='')
        print("> ", end='')
        
    def print_dir_tree(self, file_details: list[str], node=None, prefix='', is_last=True):
        if not node:
            node = self.root
            print(node.name)
        else:
            icon = '📁' if type(node) == Directory else '📄'
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{icon} {node.name}")
            prefix += "     " if is_last else "│    "
    
        if type(node) == Directory:
            for index, child in enumerate(node.children):
                is_last_child = index == len(node.children) - 1
                self.print_dir_tree(file_details, child, prefix, is_last_child)
        else:
            file_details.append(node.get_details())

    def show_memory_map(self):
        file_details = []
        self.print_dir_tree(file_details)

        output = ''
        if len(file_details) > 0:
            output += "\nFile Memory\n"
            for details in file_details:
                output += details + '\n'
        return output
            
    def __del__(self):
        self.file.close()