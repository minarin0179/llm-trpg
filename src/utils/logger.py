import sys


class Logger:
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log = open(file_path, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # flushメソッドは何もしない場合でも必要です
        self.terminal.flush()
        self.log.flush()

