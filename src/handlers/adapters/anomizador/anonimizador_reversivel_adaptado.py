import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from src.handlers.adapters.anomizador.IAnomizador import AnomizadorAdapter


class AnonimizadorReversivel(AnomizadorAdapter):
    """
    Adaptador para anonimização reversível utilizando AES-256 modo CBC.
    Garante que a chave fornecida via variável de ambiente seja compatível
    através de hashing SHA-256.
    """

    def __init__(self):
        # Obtém a chave da variável de ambiente (definida na UI)
        raw_key = os.getenv('key')

        if not raw_key:
            raise ValueError("A variável de ambiente 'key' não foi configurada. Verifique a interface gráfica.")

        # SEGURANÇA: O AES-256 exige exatamente 32 bytes.
        # Em vez de b64decode, usamos SHA-256 para derivar uma chave de 32 bytes estável
        # a partir de qualquer string digitada pelo utilizador.
        self.key = hashlib.sha256(raw_key.encode("utf-8")).digest()

    def encrypt(self, text: str) -> str:
        """Criptografa um texto e retorna uma string em Base64 contendo IV + Dados."""
        if not text:
            return ""

        try:
            # Cria um novo vetor de inicialização (IV) aleatório para cada operação
            cipher = AES.new(self.key, AES.MODE_CBC)

            # Aplica preenchimento (padding) para alinhar ao tamanho do bloco do AES
            padded_data = pad(text.encode("utf-8"), AES.block_size)

            # Criptografa os dados
            encrypted_bytes = cipher.encrypt(padded_data)

            # O IV é necessário para a decriptografia, por isso concatenamos no início
            # Resultado final: Base64(IV + Ciphertext)
            return base64.b64encode(cipher.iv + encrypted_bytes).decode("utf-8")

        except Exception as e:
            raise RuntimeError(f"Falha na criptografia: {str(e)}")

    def decrypt(self, encrypted_b64: str) -> str:
        """Recebe uma string Base64 (IV + Dados) e retorna o texto original."""
        if not encrypted_b64:
            return ""

        try:
            # Decodifica a string Base64 para bytes
            raw_data = base64.b64decode(encrypted_b64)

            # Separa o IV (primeiros 16 bytes) do conteúdo criptografado
            iv = raw_data[:AES.block_size]
            ciphertext = raw_data[AES.block_size:]

            # Inicializa o cipher com a mesma chave e o IV extraído
            cipher = AES.new(self.key, AES.MODE_CBC, iv=iv)

            # Decriptografa e remove o preenchimento (unpad)
            decrypted_padded = cipher.decrypt(ciphertext)
            original_text = unpad(decrypted_padded, AES.block_size).decode("utf-8")

            return original_text

        except (ValueError, KeyError) as e:
            # Erros comuns: Chave incorreta ou dados corrompidos
            return f"[ERRO: Chave inválida ou dado corrompido]"
        except Exception as e:
            return f"[ERRO SISTEMA: {str(e)}]"