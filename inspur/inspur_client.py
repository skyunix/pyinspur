import hashlib
import math
import random
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from inspur.config_manager import ConfigManager
from utils.common_utils import get_user_choice_from_list
from utils.constants import (DEFAULT_BASE_URL, EARTH_RADIUS_METERS,
                             MAX_RETRIES, PI, REQUEST_TIMEOUT)
from utils.logger import get_logger

logger = get_logger(__name__)


def md5_encrypt(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def generate_mobile_uuid() -> str:
    return str(uuid.uuid4()).upper()


class InspurClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        random_radius_meters: Optional[int] = None,
        client_uuid: Optional[str] = None,
    ):
        self.base_url = base_url
        self.random_radius_meters = random_radius_meters
        self.session = requests.Session()
        self.log = logger
        self.user_info: Dict[str, Any] = {}
        self.attendance_site: Dict[str, Any] = {}
        self.client_uuid = client_uuid

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Html5Plus/1.0",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "X-Requested-With": "XMLHttpRequest",
                "Connection": "keep-alive",
            }
        )

    def _make_request_with_retry(
        self, method: str, endpoint: str, body=None, headers=None, params=None, **kwargs
    ) -> requests.Response:
        url = f"{self.base_url}{endpoint}"

        request_headers = {}
        if headers:
            request_headers.update(headers)

        kwargs.setdefault("timeout", REQUEST_TIMEOUT)

        if body is not None:
            kwargs["data"] = body

        if params is not None:
            kwargs["params"] = params

        params_str = kwargs.get("params", "")
        data_str = kwargs.get("data", "")
        self.log.debug("{} {} {} {}", method, url, params_str, data_str)

        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.request(
                    method, url, headers=request_headers, **kwargs
                )
                response.raise_for_status()

                status_text = "OK" if response.ok else "ERROR"
                self.log.info(
                    "{} {} {}",
                    response.status_code,
                    status_text,
                    response.text,
                )
                return response
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    self.log.error(f"请求失败，已重试{MAX_RETRIES}次: {e}")
                    raise
                self.log.warning(f"请求失败，第{attempt + 1}次重试: {e}")
                time.sleep(2**attempt)
        self.log.error("请求失败")
        raise requests.exceptions.RequestException("请求失败")

    def _load_saved_attendance_site(self) -> bool:
        try:
            config_manager = ConfigManager()
            attendance_sites, checkin_site_address = config_manager.load_checkin_site()
            if attendance_sites and checkin_site_address:
                if checkin_site_address in attendance_sites:
                    site_data = attendance_sites[checkin_site_address]
                    self.attendance_site = {
                        "id": site_data["id"],
                        "latitude": site_data["latitude"],
                        "longitude": site_data["longitude"],
                        "address": checkin_site_address,
                    }
                    self.log.info("✓ 加载已保存的签到考勤点: {}", checkin_site_address)
                    return True
            return False
        except Exception as e:
            self.log.warning("加载考勤点失败: {}", e)
            return False

    def ensure_attendance_site_loaded(self) -> bool:
        if not self.attendance_site:
            return self._load_saved_attendance_site()
        return True

    def _generate_random_coordinates(
        self, base_lng: float, base_lat: float, radius_meters: Optional[int]
    ) -> Tuple[str, str]:
        if radius_meters is None:
            return str(base_lng), str(base_lat)

        random_angle = random.random() * 2 * PI
        random_distance = math.sqrt(random.random()) * radius_meters

        lng_offset = (
            random_distance / (EARTH_RADIUS_METERS * math.cos(base_lat * PI / 180))
        ) * math.sin(random_angle)
        lat_offset = (random_distance / EARTH_RADIUS_METERS) * math.cos(random_angle)

        new_lng = base_lng + lng_offset
        new_lat = base_lat + lat_offset

        return str(new_lng), str(new_lat)

    def _display_attendance_table(self, records: List[Dict[str, Any]]) -> None:
        self.log.info("-" * 50)
        self.log.info("日期        签到时间    签退时间")
        self.log.info("-" * 50)
        for record in records:
            date = record["SIGNTIME"]

            sign_in_time = record.get("SIGNINTIME", "")
            if not sign_in_time or sign_in_time == "-":
                sign_in = "未签到"
            else:
                sign_in = sign_in_time

            sign_out_time = record.get("SIGNOUTTIME", "")
            if not sign_out_time or sign_out_time == "-":
                sign_out = "未签退"
            else:
                sign_out = sign_out_time

            self.log.info(f"{date:<12} {sign_in:<11} {sign_out}")
        self.log.info("-" * 50)

    def _perform_login_request(
        self,
        data: Dict[str, str],
        silent: bool = False,
        return_credentials: bool = False,
    ) -> Dict[str, Any]:
        endpoint = "/urms/plugins/user/usermgr/login.ilf"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = self._make_request_with_retry(
            "POST", endpoint, body=data, headers=headers
        )
        result = response.json()

        if result["status"] == "success":
            user_data = result["result"]
            self.user_info = {
                "phone": user_data["PHONE"],
                "user_id": user_data["USER_ID"],
                "user_name": user_data["USER_NAME"],
            }
            response_data = {"success": True, "data": result}
            if return_credentials:
                response_data.update(
                    {
                        "logged_in_inspur": self,
                        "encrypted_phone": data["userName"],
                        "encrypted_password": data["password"],
                    }
                )
            return response_data

        self.log.error("认证失败: {}", result["erroInfo"])
        raise requests.exceptions.RequestException(result["erroInfo"])

    def login(self, phone: str, password: str, silent: bool = False) -> Dict[str, Any]:
        encrypted_phone = md5_encrypt(phone)
        encrypted_password = md5_encrypt(password)
        data = {"userName": encrypted_phone, "password": encrypted_password}
        return self._perform_login_request(data, silent, False)

    def login_with_encrypted_credentials(
        self, encrypted_phone: str, encrypted_password: str, silent: bool = False
    ) -> Dict[str, Any]:
        data = {"userName": encrypted_phone, "password": encrypted_password}
        return self._perform_login_request(data, silent, True)

    def get_attendance_sites(
        self, longitude: Optional[float] = None, latitude: Optional[float] = None
    ) -> Dict[str, Any]:
        if longitude is None or latitude is None:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            default_lng = config["default_longitude"]
            default_lat = config["default_latitude"]

            if default_lng and default_lat:
                self.log.info("当前坐标：{}, {}", default_lng, default_lat)
                self.log.info("【回车确认】或 【输入新坐标】")
            else:
                self.log.info("未检测到坐标，请输入坐标（可访问 https://lbs.amap.com/tools/picker 获取）:")

            for attempts in range(5):
                try:
                    coord_input = input().strip()

                    if not coord_input:
                        if default_lng and default_lat:
                            longitude = default_lng
                            latitude = default_lat
                            self.log.info("使用坐标: {}, {}", longitude, latitude)
                            break
                        else:
                            self.log.warning("坐标不能为空，请输入有效的坐标")
                            continue

                    if "," in coord_input:
                        parts = coord_input.split(",")
                        if len(parts) == 2:
                            lng_str = parts[0].strip()
                            lat_str = parts[1].strip()

                            if lng_str and lat_str:
                                longitude = float(lng_str)
                                latitude = float(lat_str)
                                self.log.info("使用新坐标: {}, {}", longitude, latitude)
                                config_manager.save_attendance_coordinates(
                                    longitude, latitude
                                )

                                break

                    self.log.warning("坐标格式错误，请使用 经度,纬度 格式")
                except ValueError:
                    self.log.warning("请输入有效的数字格式")
                except KeyboardInterrupt:
                    self.log.warning("用户取消操作")
                    return {"success": False, "error": "用户取消操作"}

            else:
                return {"success": False, "error": "坐标输入失败，请重试"}

        endpoint = "/urms/plugins/check/tcheckattendancesite/findForPhone.ilf"
        params = {"longitude": longitude, "latitude": latitude}
        headers = {}

        response = self._make_request_with_retry(
            "GET", endpoint, params=params, headers=headers
        )
        result = response.json()

        if result["attendanceSites"]:
            self.log.info("找到 {} 个考勤点:", len(result["attendanceSites"]))
            for i, site in enumerate(result["attendanceSites"], 1):
                self.log.info("  {}. {}", i, site["address"])
        else:
            self.log.warning("未找到考勤点")

        return result

    def _select_attendance_site(
        self, sites: List[Dict[str, Any]], action_name: str = "考勤"
    ) -> Optional[Dict[str, Any]]:
        addresses = [site["address"] for site in sites]

        choice_num = get_user_choice_from_list(addresses, f"请选择{action_name}考勤点")

        if choice_num is not None:
            return sites[choice_num - 1]
        return None

    def check_in(self, offset_radius: Optional[int] = None) -> Dict[str, Any]:
        return self._perform_attendance_action(
            "签到", offset_radius, "签到", is_checkout=False
        )

    def check_out(self, offset_radius: Optional[int] = None) -> Dict[str, Any]:
        return self._perform_attendance_action(
            "签退", offset_radius, "签退", is_checkout=True
        )

    def _perform_attendance_action(
        self,
        attendance_type: str,
        offset_radius: Optional[int] = None,
        action_name: str = "",
        is_checkout: bool = False,
    ) -> Dict[str, Any]:
        if not self.user_info:
            self.log.error("请先登录")
            return {"success": False, "error": "缺少必要信息"}

        selected_site = self._handle_site_selection_for_action(action_name, is_checkout)
        if not selected_site:
            self.log.warning("未选择考勤点，操作取消")
            return {"success": False, "error": "未选择考勤点"}

        if offset_radius is None:
            offset_radius = self.random_radius_meters

        endpoint = "/urms/plugins/check/tcheckattendance/create.ilf"
        base_lng = float(selected_site["longitude"])
        base_lat = float(selected_site["latitude"])
        new_lng_str, new_lat_str = self._generate_random_coordinates(
            base_lng, base_lat, offset_radius
        )

        if self.client_uuid is None:
            uuid_input = input("请输入真实设备UUID（回车则模拟生成）: ").strip()
            attendance_uuid = uuid_input if uuid_input else generate_mobile_uuid()
            self.log.info(
                "{}设备UUID: {}",
                "使用真实" if uuid_input else "生成模拟",
                attendance_uuid,
            )
            try:
                config_manager = ConfigManager()
                encrypted_phone = md5_encrypt(self.user_info["phone"])
                config_manager.save_client_uuid(encrypted_phone, attendance_uuid)
                self.client_uuid = attendance_uuid
                self.log.info("已保存设备UUID: {}", attendance_uuid)
            except Exception as e:
                self.log.warning("保存设备UUID失败: {}", e)
                self.client_uuid = attendance_uuid
        else:
            attendance_uuid = self.client_uuid

        data = {
            "userName": self.user_info["user_name"],
            "userId": self.user_info["user_id"],
            "attendanceType": attendance_type,
            "longitude": new_lng_str,
            "address": selected_site["address"],
            "latitude": new_lat_str,
            "resId": selected_site["id"],
            "UUID": attendance_uuid,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = self._make_request_with_retry(
            "POST", endpoint, body=data, headers=headers
        )
        result = response.json()

        if not result["success"]:
            self.log.error("考勤操作失败: {}", result.get("message", "未知错误"))

        return result

    def _handle_site_selection_for_action(
        self, action_name: str, is_checkout: bool = False
    ) -> Optional[Dict[str, Any]]:
        config_manager = ConfigManager()

        if is_checkout:
            load_method = config_manager.load_checkout_site
            save_method = config_manager.save_checkout_site
            site_type = "签退"
        else:
            load_method = config_manager.load_checkin_site
            save_method = config_manager.save_checkin_site
            site_type = "签到"

        return self._select_and_save_site(
            config_manager,
            action_name,
            site_type,
            load_method,
            save_method,
            is_checkout,
        )

    def _select_and_save_site(
        self,
        config_manager,
        action_name: str,
        site_type: str,
        load_method,
        save_method,
        is_checkout: bool = False,
    ) -> Optional[Dict[str, Any]]:
        attendance_sites, saved_address = load_method()

        if saved_address and saved_address in attendance_sites:
            selected_site_data = attendance_sites[saved_address]
            selected_site = {
                "id": selected_site_data["id"],
                "latitude": selected_site_data["latitude"],
                "longitude": selected_site_data["longitude"],
                "address": saved_address,
            }
            self.log.info(
                "使用已保存的{}考勤点: {}",
                action_name,
                saved_address,
            )
            if not is_checkout:
                self.attendance_site = selected_site
            return selected_site

        all_attendance_sites = config_manager.load_attendance_sites()

        if all_attendance_sites:
            selected_site = self._select_from_saved_sites(
                all_attendance_sites, action_name, site_type, save_method, is_checkout
            )
        else:
            selected_site = self._select_from_fresh_sites(
                config_manager, action_name, site_type, save_method, is_checkout
            )

        return selected_site

    def _select_from_saved_sites(
        self,
        attendance_sites: Dict[str, Any],
        action_name: str,
        site_type: str,
        save_method,
        is_checkout: bool = False,
    ) -> Optional[Dict[str, Any]]:
        self.log.info("请选择{}考勤点:", site_type)
        addresses = list(attendance_sites.keys())

        selected_index = get_user_choice_from_list(
            addresses, f"请选择{action_name}考勤点"
        )

        if selected_index is None:
            return None

        selected_address = addresses[selected_index - 1]
        selected_site_data = attendance_sites[selected_address]
        selected_site = {
            "id": selected_site_data["id"],
            "latitude": selected_site_data["latitude"],
            "longitude": selected_site_data["longitude"],
            "address": selected_address,
        }

        save_method(selected_address)
        self.log.info("✓ 已选择并保存{}考勤点: {}", action_name, selected_address)

        if not is_checkout:
            self.attendance_site = selected_site

        return selected_site

    def _select_from_fresh_sites(
        self,
        config_manager,
        action_name: str,
        site_type: str,
        save_method,
        is_checkout: bool = False,
    ) -> Optional[Dict[str, Any]]:
        self.log.info("未找到已保存的考勤点，正在获取考勤点列表...")
        sites_result = self.get_attendance_sites()

        if sites_result["attendanceSites"]:
            sites = sites_result["attendanceSites"]
            self.log.info("请选择{}考勤点（将保存供以后使用）:", site_type)

            selected_site_data = self._select_attendance_site(sites, action_name)
            if selected_site_data:
                selected_site = {
                    "id": str(selected_site_data["id"]),
                    "latitude": selected_site_data["latitude"],
                    "longitude": selected_site_data["longitude"],
                    "address": selected_site_data["address"],
                }

                attendance_sites = {
                    site["address"]: {
                        "id": str(site["id"]),
                        "latitude": site["latitude"],
                        "longitude": site["longitude"],
                    }
                    for site in sites
                }
                config_manager.save_attendance_sites(attendance_sites)

                save_method(selected_site["address"])
                self.log.info(
                    "✓ 已选择并保存{}考勤点: {}",
                    action_name,
                    selected_site["address"],
                )

                if not is_checkout:
                    self.attendance_site = selected_site

                return selected_site
        else:
            self.log.error("未找到考勤点")
        return None

    def get_monthly_attendance(
        self,
        month: Optional[str] = None,
        last_only: bool = False,
        action_type: str = "",
    ) -> Dict[str, Any]:
        if not self.user_info:
            self.log.error("请先登录")
            return {"error": "请先登录"}

        if not month:
            month = datetime.now().strftime("%Y-%m")

        endpoint = "/urms/plugins/check/tcheckattendance/findPageForPhone.ilf"
        params = {"userId": self.user_info["user_id"], "month": month}
        headers = {}

        response = self._make_request_with_retry(
            "GET", endpoint, params=params, headers=headers
        )
        result = response.json()

        records = result["dgpage"]
        if records:
            records_to_show = [records[-1]] if last_only else records
            self._display_attendance_table(records_to_show)

        return result

    def close(self) -> None:
        if hasattr(self, "session"):
            self.session.close()
