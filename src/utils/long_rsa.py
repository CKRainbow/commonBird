import re
import base64
from pathlib import Path
from typing import Optional

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

LT1_REGEX = r".{1,117}"
LT2_REGEX = r".{1,256}"


class LongRSAKey:
    def __init__(self, public_key_file: Path):
        self.rsa_key = RSA.import_key(public_key_file.read_bytes())
        self.cipher = PKCS1_v1_5.new(self.rsa_key)
        
    def _encrypt(self, message: str) -> bytes:
        try:
            max_length = (self.rsa_key.n.bit_length() + 7 >> 3) - 11
            ct_1 = b""
            if len(message) > max_length:
                lt = re.findall(LT1_REGEX, message)
                for i in lt:
                    i = i.encode("utf-8")
                    t1 = self.cipher.encrypt(i)
                    ct_1 += t1
                return base64.b64encode(ct_1)
            message = message.encode("utf-8")
            t = self.cipher.encrypt(message)
            return base64.b64encode(t)
        except Exception as e:
            print(e)
            return None

    def encrypt(self, message: str) -> str:
        encrypted = self._encrypt(message)
        return encrypted.decode("utf-8")

if __name__ == "__main__":
    key = LongRSAKey(Path("public_key.pem"))
    print(key.encrypt('1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111'))