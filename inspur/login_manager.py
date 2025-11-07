from typing import Any, Dict, Optional, Tuple

from inspur.config_manager import ConfigManager
from inspur.inspur_client import InspurClient, md5_encrypt
from utils.logger import get_logger

logger = get_logger(__name__)


class LoginManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.max_login_attempts = 3

    def login_with_credentials(
        self, phone: str, password: str, is_encrypted: bool = False
    ) -> Dict[str, Any]:
        try:
            config = self.config_manager.load_config()

            encrypted_phone = phone if is_encrypted else md5_encrypt(phone)

            client_uuid = self.config_manager.get_client_uuid(encrypted_phone)

            temp_client = InspurClient(
                random_radius_meters=config["random_radius_meters"],
                client_uuid=client_uuid,
            )

            login_method = (
                temp_client.login_with_encrypted_credentials
                if is_encrypted
                else temp_client.login
            )
            login_result = login_method(phone, password, silent=True)

            if login_result["success"]:
                login_result["encrypted_phone"] = encrypted_phone
                login_result["encrypted_password"] = (
                    password if is_encrypted else md5_encrypt(password)
                )
                login_result["user_info"] = temp_client.user_info
                login_result["logged_in_inspur"] = temp_client

            return login_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def reenter_password(
        self, phone: str
    ) -> Optional[Tuple[str, str, bool, InspurClient]]:
        for attempt_count in range(self.max_login_attempts):
            password = input("请输入密码: ").strip()
            if not password:
                logger.warning("密码不能为空！")
                continue

            is_encrypted = len(phone) == 32 and all(
                c in "0123456789abcdef" for c in phone.lower()
            )
            encrypted_phone = phone if is_encrypted else md5_encrypt(phone)

            login_result = self.login_with_credentials(
                encrypted_phone, md5_encrypt(password), is_encrypted=True
            )

            if login_result["success"]:
                login_result["encrypted_phone"] = encrypted_phone
                login_result["encrypted_password"] = md5_encrypt(password)
                # 获取用户名
                logged_in_client = login_result["logged_in_inspur"]
                actual_username = (
                    logged_in_client.user_info["user_name"]
                    if (logged_in_client and logged_in_client.user_info)
                    else phone
                )

                # 返回明文密码，而不是加密的密码
                return (actual_username, password, False, logged_in_client)
            else:
                logger.error("登录失败：{}", login_result.get("error", "未知错误"))
                if attempt_count < self.max_login_attempts - 1:
                    logger.warning(
                        "登录失败，请重新输入密码 (剩余尝试次数: {})",
                        self.max_login_attempts - attempt_count - 1,
                    )

        logger.error("登录失败次数过多，请检查用户名和密码")
        return None

    def get_client_uuid_for_user(self, encrypted_phone: str) -> Optional[str]:
        return self.config_manager.get_client_uuid(encrypted_phone)

    def save_client_uuid_for_user(self, encrypted_phone: str, client_uuid: str) -> None:
        self.config_manager.save_client_uuid(encrypted_phone, client_uuid)
