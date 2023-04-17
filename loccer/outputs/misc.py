from ..bases import OutputBase, LoccerOutput


class InMemoryOutput(OutputBase):
    def __init__(self):
        self.logs = []

    def output(self, exc: LoccerOutput) -> None:
        self.logs.append(exc.as_json())


class NullOuput(OutputBase):
    def output(self, exc: LoccerOutput) -> None:
        return None
