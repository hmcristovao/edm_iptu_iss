from Crypto.Cipher import AES
import base64


class AnonimizadorReversivel:
    def __init__(self, filepath: str = "../senha_criptografia.txt"):
        self.key = self._load_key_from_file(filepath)

    @staticmethod
    def _load_key_from_file(filepath: str) -> bytes:
        with open(filepath, "r", encoding="utf-8") as f:
            b64 = f.read().strip()

        key = base64.b64decode(b64)
        print("Chave carregada (bytes):", len(key))

        if len(key) != 32:
            raise ValueError(
                f"A chave carregada deve ter 32 bytes (AES-256), mas tem {len(key)} bytes."
            )

        return key

    def _pad(self, data: bytes) -> bytes:
        pad_len = AES.block_size - (len(data) % AES.block_size)
        return data + bytes([pad_len]) * pad_len

    def _unpad(self, data: bytes) -> bytes:
        pad_len = data[-1]
        return data[:-pad_len]

    def encrypt(self, text: str) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC)
        iv = cipher.iv

        padded = self._pad(text.encode("utf-8"))
        encrypted = cipher.encrypt(padded)

        return base64.b64encode(iv + encrypted).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        raw = base64.b64decode(encrypted_b64)
        iv = raw[:AES.block_size]
        ciphertext = raw[AES.block_size:]

        cipher = AES.new(self.key, AES.MODE_CBC, iv=iv)
        decrypted = cipher.decrypt(ciphertext)

        return self._unpad(decrypted).decode("utf-8")
