from .PricewarsObject import PricewarsObject


class ApiError(PricewarsObject):

    def __init__(self, code=-1, message=''):
        self.code = code
        self.message = message
