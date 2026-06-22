
class ExtractError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)



class NotFoundExtensionError(ExtractError):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class UnknownExtensioError(ExtractError):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class NotFoundPathError(ExtractError):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
