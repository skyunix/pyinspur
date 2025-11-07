import os
import shutil
from typing import Any, Dict, Optional, Tuple

import yaml

from utils.constants import DEFAULT_BASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    def __init__(self, config_file: str = "conf/config.yml"):
        self.config_file = config_file
        self._cache: Optional[Dict[str, Any]] = None

    def _load_data(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_file):
            template_file = os.path.join(
                os.path.dirname(self.config_file), "config.example.yml"
            )
            if os.path.exists(template_file):
                shutil.copy2(template_file, self.config_file)
                logger.info("已从模板文件创建默认配置")
            else:
                logger.warning("配置文件和模板文件都不存在，创建空配置")
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                with open(self.config_file, "w", encoding="utf-8") as f:
                    f.write("# 默认配置文件\n")

        try:
            with open(self.config_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("加载配置文件失败: {}", e)
            return {}

    def _save_data(self, data: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
            self._cache = None
        except Exception as e:
            logger.error("保存配置文件失败: {}", e)
            raise

    def _build_config_object(self, data: Dict[str, Any]) -> Dict[str, Any]:
        user_config = data["user_config"]
        app_data = data["app_data"]
        app_settings = user_config["app_settings"]
        attendance_data = app_data["attendance_data"]

        longitude, latitude = user_config["default_location"].split(",")

        return {
            "default_password": user_config["default_password"],
            "current_user": app_data["current_user"],
            "default_longitude": float(longitude),
            "default_latitude": float(latitude),
            "attendance_sites": attendance_data["sites"],
            "base_url": DEFAULT_BASE_URL,
            "auto_query_after_check": app_settings["auto_query_after_check"],
            "random_radius_meters": app_settings["random_radius_meters"],
            "log_level": app_settings["log_level"],
        }

    def load_config(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache

        data = self._load_data()
        config = self._build_config_object(data)
        self._cache = config
        return config

    def _ensure_section_exists(self, data: Dict[str, Any], section: str) -> None:
        if section not in data:
            data[section] = {}

    def update_config_section(self, section: str, key: str, value: Any) -> None:
        try:
            data = self._load_data()
            self._ensure_section_exists(data, section)
            data[section][key] = value
            self._save_data(data)
        except Exception as e:
            logger.error("更新配置失败: {}", e)
            raise

    def get_all_users(self) -> Dict[str, Dict[str, str]]:
        try:
            data = self._load_data()
            saved_users = data["app_data"]["saved_users"]

            users: Dict[str, Dict[str, str]] = {}
            for user in saved_users:
                phone_hash = user["phone_hash"]
                users[phone_hash] = {
                    "username": user["name"],
                    "password": user["password_hash"],
                    "encrypted_phone": phone_hash,
                }
            return users
        except Exception as e:
            logger.error("获取用户信息失败: {}", e)
            raise

    def add_user(
        self, encrypted_phone: str, encrypted_password: str, display_name: str
    ) -> None:
        try:
            data = self._load_data()
            self._ensure_section_exists(data, "app_data")
            saved_users = data["app_data"].setdefault("saved_users", [])

            for user in saved_users:
                if user["phone_hash"] == encrypted_phone:
                    user["name"] = display_name
                    user["password_hash"] = encrypted_password
                    self._save_data(data)
                    logger.info("用户凭据已更新")
                    return

            new_id = max([user["id"] for user in saved_users], default=0) + 1
            saved_users.append(
                {
                    "id": new_id,
                    "name": display_name,
                    "phone_hash": encrypted_phone,
                    "password_hash": encrypted_password,
                }
            )

            self._save_data(data)
            logger.info("用户凭据已保存")
        except Exception as e:
            logger.error("保存用户凭据失败: {}", e)
            raise

    def add_user_and_update_current(
        self, encrypted_phone: str, encrypted_password: str, display_name: str
    ) -> None:
        self.add_user(encrypted_phone, encrypted_password, display_name)
        self.update_current_user(encrypted_phone, display_name)

    def update_current_user(
        self, encrypted_phone: str, display_name: Optional[str] = None
    ) -> None:
        try:
            data = self._load_data()

            final_display_name = display_name
            if not final_display_name and encrypted_phone:
                saved_users = data["app_data"]["saved_users"]
                for user in saved_users:
                    if user["phone_hash"] == encrypted_phone:
                        final_display_name = user["name"]
                        break

            data["app_data"]["current_user"] = final_display_name or ""
            self._save_data(data)

            if display_name:
                logger.info("已切换当前用户为: {}", display_name)
        except Exception as e:
            logger.error("更新当前用户失败: {}", e)
            raise

    def save_attendance_coordinates(self, longitude: float, latitude: float) -> None:
        try:
            data = self._load_data()
            data["user_config"]["default_location"] = f"{longitude},{latitude}"
            self._save_data(data)
        except Exception as e:
            logger.error("保存考勤点坐标失败: {}", e)
            raise

    def save_attendance_sites(self, attendance_sites: Dict[str, Any]) -> None:
        try:
            data = self._load_data()
            data["app_data"]["attendance_data"]["sites"] = attendance_sites
            self._save_data(data)
        except Exception as e:
            logger.error("保存考勤点信息失败: {}", e)
            raise

    def save_checkin_site(self, site_address: str) -> None:
        try:
            data = self._load_data()
            data["app_data"]["attendance_data"]["checkin_site_address"] = site_address
            self._save_data(data)
        except Exception as e:
            logger.error("保存签到考勤点失败: {}", e)
            raise

    def save_checkout_site(self, site_address: str) -> None:
        try:
            data = self._load_data()
            data["app_data"]["attendance_data"]["checkout_site_address"] = site_address
            self._save_data(data)
        except Exception as e:
            logger.error("保存签退考勤点失败: {}", e)
            raise

    def load_attendance_sites(self) -> Dict[str, Any]:
        try:
            data = self._load_data()
            attendance_data = data["app_data"]["attendance_data"]
            return attendance_data["sites"]
        except Exception as e:
            logger.error("加载考勤点信息失败: {}", e)
            raise

    def load_checkin_site(self) -> Tuple[Dict[str, Any], str]:
        try:
            data = self._load_data()
            attendance_data = data["app_data"]["attendance_data"]

            attendance_sites = attendance_data["sites"]
            checkin_site_address = attendance_data["checkin_site_address"]

            if checkin_site_address and checkin_site_address in attendance_sites:
                return attendance_sites, checkin_site_address
            else:
                return {}, ""
        except Exception as e:
            logger.error("加载签到考勤点信息失败: {}", e)
            raise

    def load_checkout_site(self) -> Tuple[Dict[str, Any], str]:
        try:
            data = self._load_data()
            attendance_data = data["app_data"]["attendance_data"]

            attendance_sites = attendance_data["sites"]
            checkout_site_address = attendance_data["checkout_site_address"]

            if checkout_site_address and checkout_site_address in attendance_sites:
                return attendance_sites, checkout_site_address
            else:
                return {}, ""
        except Exception as e:
            logger.error("加载签退考勤点信息失败: {}", e)
            raise

    def save_client_uuid(self, encrypted_phone: str, client_uuid: str) -> None:
        try:
            data = self._load_data()
            self._ensure_section_exists(data, "app_data")
            client_uuids = data["app_data"].setdefault("client_uuids", {})

            client_uuids[encrypted_phone] = client_uuid
            self._save_data(data)
        except Exception as e:
            logger.error("保存考勤客户端UUID失败: {}", e)
            raise

    def get_client_uuid(self, encrypted_phone: str) -> Optional[str]:
        try:
            data = self._load_data()
            client_uuids = data["app_data"].get("client_uuids", {})
            return client_uuids.get(encrypted_phone)
        except Exception as e:
            logger.error("获取考勤客户端UUID失败: {}", e)
            return None
