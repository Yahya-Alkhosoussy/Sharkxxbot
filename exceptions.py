class ClipFail(Exception):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg


class ClipNotFound(Exception):
    def __init__(self, *args):
        self.msg = str(args[0])

    def __str__(self):
        return self.msg
