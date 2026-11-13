"""Generate a local PBKDF2 password hash for .env; never print the password."""
import getpass
import hashlib
import secrets

def main():
    first=getpass.getpass("편집장 비밀번호: ")
    second=getpass.getpass("비밀번호 재입력: ")
    if len(first)<12 or first!=second:
        raise SystemExit("비밀번호는 12자 이상이고 두 번 일치해야 합니다.")
    salt=secrets.token_bytes(16)
    iterations=310000
    digest=hashlib.pbkdf2_hmac("sha256",first.encode(),salt,iterations)
    print("다음 한 줄을 이 프로젝트의 .env에 추가하세요:")
    print(f"EDITOR_PASSWORD_HASH=pbkdf2_sha256:{iterations}:{salt.hex()}:{digest.hex()}")

if __name__=="__main__":
    main()
