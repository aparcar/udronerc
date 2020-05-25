class DroneNotReachableError(EnvironmentError):
    pass


class DroneNotFoundError(EnvironmentError):
    pass


class DroneRuntimeError(EnvironmentError):
    pass


class DroneConflict(EnvironmentError):
    pass
