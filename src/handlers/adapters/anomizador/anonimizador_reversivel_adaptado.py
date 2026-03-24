import os
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from src.handlers.adapters.anomizador.IAnomizador import AnomizadorAdapter


class AnonimizadorReversivel(AnomizadorAdapter):
    def __init__(self):
        b64_key = os.getenv('key')

        if not b64_key:
            raise ValueError("A variável de ambiente 'key' não foi configurada.")


        self.key = base64.b64decode(b64_key)

        if len(self.key) != 32:
            raise ValueError(f"AES-256 requer 32 bytes. Encontrado: {len(self.key)}")

    def encrypt(self, text: str) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC)

        padded_data = pad(text.encode("utf-8"), AES.block_size)
        encrypted = cipher.encrypt(padded_data)

        return base64.b64encode(cipher.iv + encrypted).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        raw = base64.b64decode(encrypted_b64)

        iv = raw[:AES.block_size]
        ciphertext = raw[AES.block_size:]

        cipher = AES.new(self.key, AES.MODE_CBC, iv=iv)
        decrypted_padded = cipher.decrypt(ciphertext)

        return unpad(decrypted_padded, AES.block_size).decode("utf-8")