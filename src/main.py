from FileSystem import FileSystem
from nodes import File
import threading
import sys
import csv
import io
import os
import traceback

fs_lock = threading.Lock()

def run_thread(thread_id):
    base_dir = os.path.dirname(__file__)
    input_file = os.path.join(base_dir, f"input_thread{thread_id}.txt")
    output_file = os.path.join(base_dir, f"output_thread{thread_id}.txt")

    # Check if the input file exists
    if not os.path.exists(input_file):
        print(f"Error: The input file {input_file} does not exist.")
        return

    # Redirect print output
    buffer = io.StringIO()

    with open(input_file, 'r') as infile:
        commands = infile.readlines()

    fs = FileSystem('sample.dat')

    with fs_lock:
        fs.load()  # Ensure exclusive access to disk

    for command in commands:
        if command.strip().lower() == 'exit':
            break
        result = execute(command.strip())
        if result:
            buffer.write(result)

    with open(output_file, 'w') as out:
        out.write(buffer.getvalue())

    with fs_lock:
        fs.save()  # Write updated state safely

def extract_cmd(str: str):
    i = str.find(' ')
    if i == -1:
        return str.strip().lower()
    return str[:i].lower()

def extract_args(str: str):
    i = str.find(' ')
    if i == -1:
        return []

    str = str[i + 1:]  # everything except cmd
    reader = csv.reader(io.StringIO(str), skipinitialspace=True)
    str = next(reader)
    return [x.strip() for x in str]  # Strip spaces in each argument

def warn_args(cmd, takes, given):
    if given != takes:
        print(f"{cmd} takes exactly {takes} argument(s). {given} were provided.")
        return True
    return False

def arg_to_int(arg):
    try:
        arg = int(arg)
        return True
    except ValueError:
        print(f"Error converting argument {arg} to integer.")
    return False

fs = FileSystem("sample.dat")

p = ''
opened_files: dict[str, File] = {}

def execute(command):
    output = io.StringIO()
    cmd = extract_cmd(command)
    args = extract_args(command)
    l = len(args)

    try:
        match cmd:
            case "create":
                if warn_args("create", 1, l):
                    return ""
                fs.create(args[0])
                output.write(f"File {args[0]} created.\n")

            case "delete_file":
                if warn_args("delete_file", 1, l):
                    return ""
                fs.delete_file(args[0])
                output.write(f"File {args[0]} deleted.\n")

            case "delete_dir":
                if warn_args("delete_dir", 1, l):
                    return ""
                fs.delete_dir(args[0])
                output.write(f"Directory {args[0]} deleted.\n")

            case "mkdir":
                if warn_args("mkdir", 1, l):
                    return ""
                fs.mkdir(args[0])
                output.write(f"Directory {args[0]} created.\n")

            case "chdir":
                if warn_args("chdir", 1, l):
                    return ""
                fs.chdir(args[0])
                output.write(f"Changed current directory to {args[0]}.\n")

            case "move_file":
                if warn_args("move_file", 2, l):
                    return ""
                fs.move_file(args[0], args[1])
                output.write(f"File {args[0]} moved to {args[1]}.\n")

            case "move_dir":
                if warn_args("move_dir", 2, l):
                    return ""
                fs.move_dir(args[0], args[1])
                output.write(f"Directory {args[0]} moved to {args[1]}.\n")

            case "open":
                if warn_args("open", 2, l):
                    return ""
                file = fs.open(args[0], args[1])
                if file:
                    opened_files[args[0]] = file
                    output.write(f"File {args[0]} opened in {args[1]} mode.\n")
                else:
                    output.write(f"Failed to open file {args[0]}.\n")

            case "close":
                if warn_args("close", 1, l):
                    return ""
                if args[0] in opened_files:
                    fs.close(opened_files[args[0]])
                    del opened_files[args[0]]
                    output.write(f"File {args[0]} closed.\n")
                else:
                    output.write(f"File {args[0]} is not opened. Cannot close.\n")

            case "write_to_file":
                if l != 2 and l != 3:
                    output.write(f"write_to_file takes 2 or 3 arguments. {l} were provided.\n")
                    return ""
                if args[0] not in opened_files:
                    output.write(f"{args[0]} is not opened. Cannot write.\n")
                    return ""
                if l == 2:
                    opened_files[args[0]].write_to_file(args[1].strip('"').strip("'"))
                    output.write(f"Data written to file {args[0]}.\n")
                elif arg_to_int(args[2]):
                    opened_files[args[0]].write_to_file(args[1].strip('"').strip("'"), int(args[2]))
                    output.write(f"Data written to file {args[0]} at position {args[2]}.\n")

            case "read_from_file":
                if l != 1 and l != 3:
                    output.write(f"read_from_file takes 1 or 3 arguments. {l} were provided.\n")
                    return ""
                if args[0] not in opened_files:
                    output.write(f"{args[0]} is not opened. Cannot read.\n")
                    return ""
                if l == 1:
                    output.write(opened_files[args[0]].read_from_file() + '\n')
                    output.write(f"Data read from file {args[0]}.\n")
                elif arg_to_int(args[1]) and arg_to_int(args[2]):
                    output.write(opened_files[args[0]].read_from_file(int(args[1]), int(args[2])) + '\n')
                    output.write(f"Data read from file {args[0]} between positions {args[1]} and {args[2]}.\n")

            case "move_within_file":
                if warn_args("move_within_file", 4, l):
                    return ""
                if args[0] not in opened_files:
                    output.write(f"{args[0]} is not opened. Cannot move.\n")
                    return ""
                if arg_to_int(args[1]) and arg_to_int(args[2]) and arg_to_int(args[3]):
                    opened_files[args[0]].move_within_file(int(args[1]), int(args[2]), int(args[3]))
                    output.write(f"Moved data within file {args[0]} from {args[1]} to {args[2]} with length {args[3]}.\n")

            case "truncate_file":
                if warn_args("truncate_file", 2, l):
                    return ""
                if args[0] not in opened_files:
                    output.write(f"{args[0]} is not opened. Cannot truncate.\n")
                    return ""
                if arg_to_int(args[1]):
                    opened_files[args[0]].truncate_file(int(args[1]))
                    output.write(f"File {args[0]} truncated to {args[1]} bytes.\n")

            case "ls":
                if warn_args("ls", 0, l):
                    return ""
                output.write(fs.ls() + '\n')
                output.write("Listing the contents of the current directory.\n")

            case "show_memory_map":
                if warn_args("show_memory_map", 0, l):
                    return ""
                output.write("Displaying memory map.\n")
                output.write(fs.show_memory_map() + '\n')

            case "exit":
                output.write("Exiting the file system simulation.\n")
                return ""

            case _:
                output.write(f"Function {cmd} is not recognized.\n")

    except Exception as e:
        output.write(f"Exception: {str(e)}\n")
        output.write(traceback.format_exc())  # This will show the full traceback

    return output.getvalue()

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <num_threads>")
        return

    num_threads = int(sys.argv[1])
    threads = []

    for i in range(num_threads):
        t = threading.Thread(target=run_thread, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("All threads finished.")

if __name__ == "__main__":
    main()