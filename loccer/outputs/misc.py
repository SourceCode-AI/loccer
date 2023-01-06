from ..bases import OutputBase, ExceptionData


class InMemoryOutput(OutputBase):
    def __init__(self):
        self.logs = []

    def output(self, exc: ExceptionData) -> None:
        self.logs.append(exc.as_json())


class NullOuput(OutputBase):
    def output(self, exc: ExceptionData) -> None:
        return None
