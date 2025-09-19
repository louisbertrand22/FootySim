class FootySimError(Exception):
    pass


class NotFoundError(FootySimError):
    pass


class ValidationError(FootySimError):
    pass


class TransferError(FootySimError):
    pass


class SimulationError(FootySimError):
    pass


class ScheduleError(FootySimError):
    pass
