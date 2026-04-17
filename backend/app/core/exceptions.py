class PasswordRequiredError(Exception):
    """Lanzada cuando un PDF requiere contraseña pero no se proporcionó una o la guardada falló."""
    def __init__(self, message="El archivo PDF requiere una contraseña para ser procesado.", origen=None, tipo_doc=None):
        self.message = message
        self.origen = origen
        self.tipo_doc = tipo_doc
        super().__init__(self.message)

class InvalidPasswordError(Exception):
    """Lanzada cuando la contraseña proporcionada es incorrecta."""
    def __init__(self, message="La contraseña del PDF es incorrecta.", origen=None, tipo_doc=None):
        self.message = message
        self.origen = origen
        self.tipo_doc = tipo_doc
        super().__init__(self.message)
