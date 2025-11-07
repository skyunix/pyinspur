from typing import Any, Dict, Optional, Tuple

from inspur.config_manager import ConfigManager
from inspur.inspur_client import (InspurClient, md5_encrypt)
from inspur.login_manager import LoginManager
from utils.common_utils import get_user_choice_from_list
from utils.logger import get_logger

logger = get_logger(__name__)


class UserManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.login_manager = LoginManager(config_manager)
        self.max_login_attempts = 3

    def process_successful_login(
        self,
        login_result: Dict[str, Any],
        display_name: str,
        save_credentials: bool = True,
    ) -> Tuple[str, InspurClient]:
        logged_in_client = login_result.get("logged_in_inspur")
        if logged_in_client and logged_in_client.user_info:
            actual_username = logged_in_client.user_info["user_name"]
        else:
            user_info = login_result["data"]["result"]
            actual_username = user_info["USER_NAME"]

        if save_credentials:
            encrypted_phone = login_result["encrypted_phone"]
            encrypted_password = login_result["encrypted_password"]
            self.config_manager.add_user_and_update_current(
                encrypted_phone, encrypted_password, actual_username
            )

            if logged_in_client and logged_in_client.client_uuid:
                self.config_manager.save_client_uuid(
                    encrypted_phone, logged_in_client.client_uuid
                )

        if logged_in_client is None:
            raise ValueError("登录成功但未获取到有效的客户端对象")

        return actual_username, logged_in_client

    def _get_user_choice(self, all_users: Dict[str, Dict[str, str]]) -> Optional[int]:
        logger.info("请选择要切换的用户:")
        user_list = list(all_users.items())
        display_texts = []
        for i, (encrypted_phone, user_data) in enumerate(user_list, 1):
            display_name = user_data["username"]
            display_text = display_name if display_name else f"用户{i}"
            display_texts.append(display_text)

        display_texts.append("添加新用户")
        display_texts.append("返回主菜单")

        return get_user_choice_from_list(display_texts, "请选择")

    def _reenter_password(
        self, phone: str
    ) -> Optional[Tuple[str, str, bool, InspurClient]]:
        return self.login_manager.reenter_password(phone)

    def _add_new_user(self) -> Optional[Tuple[str, str, bool, InspurClient]]:
        new_phone = input("请输入手机号: ").strip()
        if not new_phone:
            logger.warning("手机号不能为空！")
            return None

        encrypted_new_phone = md5_encrypt(new_phone)
        existing_client_uuid = self.login_manager.get_client_uuid_for_user(
            encrypted_new_phone
        )

        if existing_client_uuid:
            logger.info("使用已保存的设备UUID: {}", existing_client_uuid)

        all_users = self.config_manager.get_all_users()
        if encrypted_new_phone in all_users:
            logger.warning("该手机号已存在！")
            return None

        config = self.config_manager.load_config()
        if config["default_password"]:
            try:
                temp_client = InspurClient(
                    random_radius_meters=config["random_radius_meters"]
                )
                login_result = temp_client.login_with_encrypted_credentials(
                    encrypted_new_phone, config["default_password"]
                )
                if login_result["success"]:
                    login_result["encrypted_phone"] = encrypted_new_phone
                    login_result["encrypted_password"] = config["default_password"]
                    actual_username, logged_in_client = self.process_successful_login(
                        login_result, new_phone, save_credentials=True
                    )
                    return (
                        new_phone,
                        config["default_password"],
                        False,
                        logged_in_client,
                    )
            except Exception:
                pass

        logger.info("默认密码登录失败，请手动输入密码：")
        return self.login_manager.reenter_password(encrypted_new_phone)

    def _handle_user_selection(
        self, all_users: Dict[str, Dict[str, str]], choice_num: int
    ) -> Optional[Tuple[str, str, bool, InspurClient]]:
        user_list = list(all_users.items())
        config = self.config_manager.load_config()

        if 1 <= choice_num <= len(all_users):
            encrypted_phone, user_data = user_list[choice_num - 1]
            selected_password = user_data["password"]
            display_name = user_data["username"]

            login_result = self.login_manager.login_with_credentials(
                encrypted_phone, selected_password, is_encrypted=True
            )

            if login_result["success"]:
                login_result["encrypted_phone"] = encrypted_phone
                login_result["encrypted_password"] = selected_password
                actual_username, logged_in_client = self.process_successful_login(
                    login_result, display_name, save_credentials=False
                )
                self.config_manager.update_current_user(encrypted_phone, display_name)
                return (display_name, selected_password, True, logged_in_client)
            else:
                logger.warning("登录失败，请重新输入密码")
                reenter_result = self.login_manager.reenter_password(encrypted_phone)
                if reenter_result:
                    actual_username, password, used_saved_password, logged_in_client = (
                        reenter_result
                    )
                    encrypted_password = md5_encrypt(password)
                    self.config_manager.add_user_and_update_current(
                        encrypted_phone, encrypted_password, actual_username
                    )
                    logger.info("密码已更新并保存")
                return reenter_result

        elif choice_num == len(all_users) + 1:
            return self._add_new_user()

        elif choice_num == len(all_users) + 2:
            return None

        return None

    def switch_user(self) -> Optional[Tuple[str, str, bool, InspurClient]]:
        all_users = self.config_manager.get_all_users()

        if not all_users:
            logger.warning("没有保存的用户，请先登录")
            return None

        choice_num = self._get_user_choice(all_users)
        if choice_num is None:
            return None

        return self._handle_user_selection(all_users, choice_num)

    def get_user_credentials(self) -> Optional[Tuple[str, str, bool, InspurClient]]:
        all_users = self.config_manager.get_all_users()
        config = self.config_manager.load_config()
        current_user = config["current_user"]

        if all_users and current_user:
            for encrypted_phone, user_data in all_users.items():
                if user_data.get("username") == current_user:
                    selected_password = user_data["password"]
                    if selected_password:
                        logger.info("正在登录{}", current_user)
                        login_result = self.login_manager.login_with_credentials(
                            encrypted_phone, selected_password, is_encrypted=True
                        )

                        if login_result["success"]:
                            actual_username, logged_in_client = (
                                self.process_successful_login(
                                    login_result, current_user, save_credentials=False
                                )
                            )
                            return (
                                current_user,
                                selected_password,
                                True,
                                logged_in_client,
                            )
                        else:
                            logger.warning("当前用户登录失败，请重新输入密码")
                            reenter_result = self.login_manager.reenter_password(encrypted_phone)
                            if reenter_result:
                                actual_username, password, used_saved_password, logged_in_client = reenter_result
                                encrypted_password = md5_encrypt(password)
                                self.config_manager.add_user_and_update_current(
                                    encrypted_phone, encrypted_password, actual_username
                                )
                                logger.info("密码已更新并保存")
                            return reenter_result

        if all_users:
            choice_num = self._get_user_choice(all_users)
            if choice_num is None:
                return None

            return self._handle_user_selection(all_users, choice_num)

        phone = input("请输入手机号: ").strip()
        if not phone:
            logger.warning("手机号不能为空！")
            return None

        encrypted_phone = md5_encrypt(phone)
        config = self.config_manager.load_config()

        if config["default_password"]:
            try:
                temp_client = InspurClient(
                    random_radius_meters=config["random_radius_meters"]
                )
                login_result = temp_client.login_with_encrypted_credentials(
                    encrypted_phone, config["default_password"]
                )
                if login_result["success"]:
                    login_result["encrypted_phone"] = encrypted_phone
                    login_result["encrypted_password"] = config["default_password"]
                    actual_username, logged_in_client = self.process_successful_login(
                        login_result, phone, save_credentials=True
                    )
                    return (phone, config["default_password"], False, logged_in_client)
            except Exception:
                pass

        logger.info("默认密码登录失败，请手动输入密码：")
        reenter_result = self.login_manager.reenter_password(encrypted_phone)
        if reenter_result:
            actual_username, password, used_saved_password, logged_in_client = reenter_result
            encrypted_password = md5_encrypt(password)
            self.config_manager.add_user_and_update_current(
                encrypted_phone, encrypted_password, actual_username
            )
            logger.info("密码已更新并保存")
        return reenter_result
