from abc import ABC, abstractmethod


class AnomizadorAdapter(ABC):

    @abstractmethod
    def encrypt(self, data: str) -> str:
        pass

    @abstractmethod
    def decrypt(self, data: str) -> str:
        pass